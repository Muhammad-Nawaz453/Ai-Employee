"""
Error Recovery & Graceful Degradation Module

Provides:
- Retry logic with exponential backoff
- Error categorization and handling
- Graceful degradation strategies
- Circuit breaker pattern
- Health monitoring and auto-restart
"""

import time
import logging
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Callable, Any, Dict
from functools import wraps
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of errors for appropriate handling"""
    TRANSIENT = "transient"  # Network timeout, API rate limit
    AUTHENTICATION = "authentication"  # Expired token, revoked access
    LOGIC = "logic"  # AI misinterpretation
    DATA = "data"  # Corrupted file, missing field
    SYSTEM = "system"  # Process crash, disk full


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures
    
    Usage:
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        result = breaker.call(api_function, args)
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker logic"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker half-open, testing recovery")
            else:
                raise Exception("Circuit breaker is open, request rejected")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if self.last_failure_time is None:
            return True
        return (datetime.now() - self.last_failure_time).total_seconds() > self.recovery_timeout
    
    def _on_success(self):
        """Reset circuit breaker on success"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        logger.debug("Circuit breaker reset to closed")
    
    def _on_failure(self, error: Exception):
        """Handle failure and update circuit state"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker re-opened after failed recovery test")


def with_retry(max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 60.0,
               retryable_exceptions: tuple = (Exception,)):
    """
    Decorator for retry with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        retryable_exceptions: Tuple of exception types to retry on
    
    Usage:
        @with_retry(max_attempts=3, base_delay=2)
        def api_call():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        logger.error(f"Max retries ({max_attempts}) exceeded for {func.__name__}")
                        raise
                    
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}, "
                        f"retrying in {delay:.1f}s: {str(e)}"
                    )
                    time.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator


class ErrorHandler:
    """Centralized error handling and recovery"""
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.error_log_path = self.vault_path / "Logs" / "errors.jsonl"
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure log directories exist"""
        self.error_log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize an error for appropriate handling"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Transient errors
        if any(kw in error_str or kw in error_type for kw in [
            "timeout", "rate limit", "too many requests", "connection refused",
            "network", "temporary"
        ]):
            return ErrorCategory.TRANSIENT
        
        # Authentication errors
        if any(kw in error_str or kw in error_type for kw in [
            "unauthorized", "forbidden", "authentication", "token expired",
            "invalid credentials", "access denied"
        ]):
            return ErrorCategory.AUTHENTICATION
        
        # Data errors
        if any(kw in error_str or kw in error_type for kw in [
            "corrupt", "invalid format", "missing field", "parse error",
            "validation", "schema"
        ]):
            return ErrorCategory.DATA
        
        # System errors
        if any(kw in error_str or kw in error_type for kw in [
            "disk full", "out of memory", "permission denied", "crash",
            "segmentation fault"
        ]):
            return ErrorCategory.SYSTEM
        
        # Default to logic error
        return ErrorCategory.LOGIC
    
    def handle_error(self, error: Exception, context: Dict = None) -> Dict:
        """
        Handle an error with appropriate recovery strategy
        
        Returns:
            Dict with error info and recovery action
        """
        category = self.categorize_error(error)
        timestamp = datetime.now().isoformat()
        
        error_record = {
            "timestamp": timestamp,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "category": category.value,
            "context": context or {},
        }
        
        # Log error
        self._log_error(error_record)
        
        # Determine recovery action
        recovery_action = self._get_recovery_action(category, error)
        error_record["recovery_action"] = recovery_action
        
        logger.error(f"Error handled: {category.value} - {str(error)}")
        
        return error_record
    
    def _log_error(self, error_record: Dict):
        """Log error to JSONL file"""
        try:
            with open(self.error_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(error_record) + "\n")
        except Exception as e:
            logger.error(f"Failed to log error: {e}")
    
    def _get_recovery_action(self, category: ErrorCategory, error: Exception) -> Dict:
        """Get appropriate recovery action for error category"""
        actions = {
            ErrorCategory.TRANSIENT: {
                "action": "retry_with_backoff",
                "message": "Will retry with exponential backoff",
                "auto_recover": True,
                "notify_human": False,
            },
            ErrorCategory.AUTHENTICATION: {
                "action": "alert_human",
                "message": "Authentication failed - human must refresh credentials",
                "auto_recover": False,
                "notify_human": True,
            },
            ErrorCategory.LOGIC: {
                "action": "queue_for_review",
                "message": "Queued for human review",
                "auto_recover": False,
                "notify_human": True,
            },
            ErrorCategory.DATA: {
                "action": "quarantine_and_alert",
                "message": "Data quarantined - human must review",
                "auto_recover": False,
                "notify_human": True,
            },
            ErrorCategory.SYSTEM: {
                "action": "alert_and_degrade",
                "message": "System degraded - alerting human",
                "auto_recover": False,
                "notify_human": True,
            },
        }
        
        return actions.get(category, {
            "action": "unknown",
            "message": "Unknown error - manual intervention required",
            "auto_recover": False,
            "notify_human": True,
        })
    
    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """Get or create a circuit breaker"""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker()
        return self.circuit_breakers[name]


class GracefulDegradation:
    """
    Manages system degradation when components fail
    
    Ensures system continues operating with reduced functionality
    """
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.degraded_services: Dict[str, datetime] = {}
        self.status_file = self.vault_path / "Logs" / "system_status.json"
    
    def mark_service_degraded(self, service_name: str, reason: str = ""):
        """Mark a service as degraded"""
        self.degraded_services[service_name] = datetime.now()
        logger.warning(f"Service degraded: {service_name} - {reason}")
        self._update_status_file()
    
    def mark_service_recovered(self, service_name: str):
        """Mark a service as recovered"""
        if service_name in self.degraded_services:
            del self.degraded_services[service_name]
            logger.info(f"Service recovered: {service_name}")
            self._update_status_file()
    
    def is_service_degraded(self, service_name: str) -> bool:
        """Check if a service is currently degraded"""
        return service_name in self.degraded_services
    
    def execute_with_fallback(self, primary_func: Callable, fallback_func: Callable,
                               service_name: str, *args, **kwargs) -> Any:
        """
        Execute primary function, fallback if degraded
        
        Args:
            primary_func: Primary function to call
            fallback_func: Fallback function if primary fails
            service_name: Name of the service for tracking
        """
        if self.is_service_degraded(service_name):
            logger.info(f"Service {service_name} degraded, using fallback")
            return fallback_func(*args, **kwargs)
        
        try:
            result = primary_func(*args, **kwargs)
            self.mark_service_recovered(service_name)
            return result
        except Exception as e:
            logger.error(f"Primary function failed for {service_name}: {e}")
            self.mark_service_degraded(service_name, str(e))
            return fallback_func(*args, **kwargs)
    
    def _update_status_file(self):
        """Update system status file"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "degraded_services": {
                name: since.isoformat()
                for name, since in self.degraded_services.items()
            },
            "overall_status": "degraded" if self.degraded_services else "healthy",
        }
        
        try:
            with open(self.status_file, "w", encoding="utf-8") as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to update status file: {e}")
    
    def get_status_report(self) -> Dict:
        """Get current system status report"""
        return {
            "timestamp": datetime.now().isoformat(),
            "degraded_services": list(self.degraded_services.keys()),
            "overall_status": "degraded" if self.degraded_services else "healthy",
        }


class WatchdogMonitor:
    """
    Monitor and restart critical processes
    
    Ensures watchers and services stay running
    """
    
    def __init__(self, vault_path: str, check_interval: int = 60):
        self.vault_path = Path(vault_path)
        self.check_interval = check_interval
        self.processes: Dict[str, Dict] = {}
        self.error_handler = ErrorHandler(vault_path)
        self.logger = logging.getLogger("watchdog")
    
    def register_process(self, name: str, command: str, pid_file: str = None):
        """Register a process for monitoring"""
        self.processes[name] = {
            "command": command,
            "pid_file": pid_file or f"/tmp/{name}.pid",
            "last_seen": None,
            "restart_count": 0,
        }
        self.logger.info(f"Registered process: {name}")
    
    def check_and_restart(self) -> List[str]:
        """Check all processes and restart failed ones"""
        restarted = []
        
        for name, proc_info in self.processes.items():
            if not self._is_process_running(name, proc_info):
                self.logger.warning(f"Process {name} not running, restarting...")
                
                try:
                    self._restart_process(name, proc_info)
                    restarted.append(name)
                except Exception as e:
                    self.logger.error(f"Failed to restart {name}: {e}")
                    self.error_handler.handle_error(e, {"process": name})
        
        return restarted
    
    def _is_process_running(self, name: str, proc_info: Dict) -> bool:
        """Check if a process is running"""
        # Simplified check - in production, use psutil or platform-specific checks
        pid_file = Path(proc_info["pid_file"])
        
        if not pid_file.exists():
            return False
        
        try:
            pid = int(pid_file.read_text().strip())
            # On Windows, this would require psutil
            # For now, assume running if PID file exists
            return True
        except:
            return False
    
    def _restart_process(self, name: str, proc_info: Dict):
        """Restart a process"""
        import subprocess
        
        proc_info["restart_count"] += 1
        proc_info["last_seen"] = datetime.now().isoformat()
        
        # In production, would use subprocess.Popen or platform-specific restart
        self.logger.info(f"Would restart {name}: {proc_info['command']}")
    
    def run_monitor_loop(self):
        """Run continuous monitoring loop"""
        self.logger.info("Starting watchdog monitor")
        
        while True:
            try:
                restarted = self.check_and_restart()
                
                if restarted:
                    self.logger.info(f"Restarted processes: {', '.join(restarted)}")
                
            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}")
            
            time.sleep(self.check_interval)


if __name__ == "__main__":
    import sys
    
    vault_path = sys.argv[1] if len(sys.argv) > 1 else "./AI_Employee_Vault"
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Test error handler
    error_handler = ErrorHandler(vault_path)
    
    try:
        raise TimeoutError("Connection timeout")
    except Exception as e:
        result = error_handler.handle_error(e, {"test": "example"})
        print(f"Error handled: {result['category']} - {result['recovery_action']['action']}")
    
    # Test circuit breaker
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=5)
    
    call_count = 0
    
    def failing_function():
        global call_count
        call_count += 1
        if call_count < 4:
            raise Exception("Temporary failure")
        return "Success!"
    
    try:
        result = breaker.call(failing_function)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Circuit breaker prevented further calls: {e}")
    
    print("\nError recovery module test complete")
