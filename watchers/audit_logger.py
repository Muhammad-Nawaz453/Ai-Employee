"""
Comprehensive Audit Logging System

Provides:
- Structured JSONL logging for all AI actions
- Audit trail for compliance and review
- Log rotation and retention
- Query and analysis tools
- Security event logging
"""

import json
import logging
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import gzip
import shutil

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of actions that can be logged"""
    EMAIL_SEND = "email_send"
    EMAIL_DRAFT = "email_draft"
    EMAIL_READ = "email_read"
    WHATSAPP_SEND = "whatsapp_send"
    WHATSAPP_READ = "whatsapp_read"
    SOCIAL_POST = "social_post"
    SOCIAL_SCHEDULE = "social_schedule"
    SOCIAL_INSIGHTS = "social_insights"
    PAYMENT_CREATE = "payment_create"
    PAYMENT_SEND = "payment_send"
    INVOICE_CREATE = "invoice_create"
    INVOICE_SEND = "invoice_send"
    INVOICE_VIEW = "invoice_view"
    FILE_CREATE = "file_create"
    FILE_READ = "file_read"
    FILE_MOVE = "file_move"
    FILE_DELETE = "file_delete"
    TASK_COMPLETE = "task_complete"
    TASK_PLAN = "task_plan"
    TASK_CLAIM = "task_claim"
    APPROVAL_CREATE = "approval_create"
    APPROVAL_APPROVE = "approval_approve"
    APPROVAL_REJECT = "approval_reject"
    APPROVAL_EXPIRE = "approval_expire"
    BRIEFING_GENERATE = "briefing_generate"
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    SYSTEM_ERROR = "system_error"
    SYSTEM_RESTART = "system_restart"
    WATCHER_EVENT = "watcher_event"
    MCP_CALL = "mcp_call"
    UNKNOWN = "unknown"


class AuditLogger:
    """
    Comprehensive audit logger for all AI Employee actions
    
    Logs to JSONL files with daily rotation and 90-day retention
    """
    
    def __init__(self, vault_path: str, retention_days: int = 90):
        self.vault_path = Path(vault_path)
        self.logs_path = self.vault_path / "Logs"
        self.retention_days = retention_days
        self.current_log_file = None
        self.current_date = None
        
        self._ensure_directories()
        self._rotate_if_needed()
    
    def _ensure_directories(self):
        """Ensure log directories exist"""
        self.logs_path.mkdir(parents=True, exist_ok=True)
    
    def _get_log_file(self, date: datetime) -> Path:
        """Get log file path for a specific date"""
        return self.logs_path / f"audit_{date.strftime('%Y-%m-%d')}.jsonl"
    
    def _rotate_if_needed(self):
        """Rotate log file if date has changed"""
        today = datetime.now().date()
        
        if self.current_date != today:
            self.current_date = today
            self.current_log_file = self._get_log_file(datetime.now())
    
    def log(self, action: ActionType, actor: str = "claude_code",
            target: str = "", parameters: Dict = None,
            approval_status: str = "", approved_by: str = "",
            result: str = "success", metadata: Dict = None):
        """
        Log an action
        
        Args:
            action: Type of action
            actor: Who/what performed the action
            target: Target of the action (email, file, etc.)
            parameters: Action parameters
            approval_status: pending/approved/rejected/auto
            approved_by: Who approved (human/system)
            result: success/failure/error
            metadata: Additional metadata
        """
        self._rotate_if_needed()
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action.value,
            "actor": actor,
            "target": target,
            "parameters": parameters or {},
            "approval_status": approval_status,
            "approved_by": approved_by,
            "result": result,
            "metadata": metadata or {},
        }
        
        # Write to current log file
        try:
            with open(self.current_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            # Fallback: try to write to stderr
            print(f"AUDIT LOG ERROR: {e}", flush=True)
    
    def log_mcp_call(self, server: str, tool: str, arguments: Dict,
                     result: str = "success", error: str = ""):
        """Log an MCP tool call"""
        self.log(
            action=ActionType.MCP_CALL,
            actor=server,
            target=tool,
            parameters=arguments,
            result="failure" if error else result,
            metadata={"error": error} if error else {},
        )
    
    def log_approval(self, action_type: str, approval_id: str,
                     status: str, approved_by: str = ""):
        """Log an approval event"""
        action_map = {
            "create": ActionType.APPROVAL_CREATE,
            "approve": ActionType.APPROVAL_APPROVE,
            "reject": ActionType.APPROVAL_REJECT,
            "expire": ActionType.APPROVAL_EXPIRE,
        }
        
        self.log(
            action=action_map.get(status.lower(), ActionType.APPROVAL_CREATE),
            target=approval_id,
            approval_status=status,
            approved_by=approved_by,
            metadata={"action_type": action_type},
        )
    
    def log_watcher_event(self, watcher: str, event: str, details: Dict = None):
        """Log a watcher event"""
        self.log(
            action=ActionType.WATCHER_EVENT,
            actor=watcher,
            target=event,
            metadata=details or {},
        )
    
    def log_error(self, error: Exception, context: Dict = None):
        """Log an error event"""
        self.log(
            action=ActionType.SYSTEM_ERROR,
            target=str(error),
            result="error",
            metadata=context or {"error_type": type(error).__name__},
        )
    
    def get_logs_for_date(self, date: datetime) -> List[Dict]:
        """Get all logs for a specific date"""
        log_file = self._get_log_file(date)
        
        if not log_file.exists():
            return []
        
        logs = []
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        logs.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Failed to read log file {log_file}: {e}")
        
        return logs
    
    def query_logs(self, start_date: datetime = None, end_date: datetime = None,
                   action_type: str = None, actor: str = None,
                   result: str = None) -> List[Dict]:
        """
        Query logs with filters
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            action_type: Filter by action type
            actor: Filter by actor
            result: Filter by result
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now()
        
        results = []
        current = start_date
        
        while current <= end_date:
            logs = self.get_logs_for_date(current)
            
            for log_entry in logs:
                # Apply filters
                if action_type and log_entry.get("action_type") != action_type:
                    continue
                if actor and log_entry.get("actor") != actor:
                    continue
                if result and log_entry.get("result") != result:
                    continue
                
                results.append(log_entry)
            
            current += timedelta(days=1)
        
        return results
    
    def generate_audit_report(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        Generate audit report for date range
        
        Returns:
            Dict with summary statistics
        """
        logs = self.query_logs(start_date, end_date)
        
        report = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "total_actions": len(logs),
            "actions_by_type": {},
            "actions_by_actor": {},
            "success_rate": 0.0,
            "approval_stats": {
                "approved": 0,
                "rejected": 0,
                "pending": 0,
            },
            "errors": [],
        }
        
        success_count = 0
        error_count = 0
        
        for log_entry in logs:
            # Count by type
            action_type = log_entry.get("action_type", "unknown")
            report["actions_by_type"][action_type] = \
                report["actions_by_type"].get(action_type, 0) + 1
            
            # Count by actor
            actor = log_entry.get("actor", "unknown")
            report["actions_by_actor"][actor] = \
                report["actions_by_actor"].get(actor, 0) + 1
            
            # Count successes
            if log_entry.get("result") == "success":
                success_count += 1
            
            # Count errors
            if log_entry.get("result") == "error":
                error_count += 1
                report["errors"].append({
                    "timestamp": log_entry.get("timestamp"),
                    "target": log_entry.get("target"),
                    "actor": log_entry.get("actor"),
                })
            
            # Count approvals
            approval_status = log_entry.get("approval_status", "")
            if approval_status == "approved":
                report["approval_stats"]["approved"] += 1
            elif approval_status == "rejected":
                report["approval_stats"]["rejected"] += 1
            elif approval_status == "pending":
                report["approval_stats"]["pending"] += 1
        
        # Calculate success rate
        if len(logs) > 0:
            report["success_rate"] = (success_count / len(logs)) * 100
        
        return report
    
    def cleanup_old_logs(self):
        """Remove logs older than retention period"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        removed = []
        
        for log_file in self.logs_path.glob("audit_*.jsonl"):
            # Extract date from filename
            try:
                date_str = log_file.stem.replace("audit_", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                if file_date < cutoff_date:
                    # Compress before deleting
                    compressed_file = log_file.with_suffix(".jsonl.gz")
                    with open(log_file, "rb") as f_in:
                        with gzip.open(compressed_file, "wb") as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    log_file.unlink()
                    removed.append(log_file.name)
                    logger.info(f"Compressed and removed old log: {log_file.name}")
            except Exception as e:
                logger.warning(f"Failed to process log file {log_file}: {e}")
        
        return removed
    
    def export_logs(self, start_date: datetime, end_date: datetime,
                    output_file: str) -> str:
        """
        Export logs to a file for archival or compliance
        
        Returns:
            Path to exported file
        """
        logs = self.query_logs(start_date, end_date)
        
        export_path = Path(output_file)
        
        with open(export_path, "w", encoding="utf-8") as f:
            f.write(f"# Audit Log Export\n")
            f.write(f"# Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n")
            f.write(f"# Total Records: {len(logs)}\n\n")
            
            for log_entry in logs:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        
        logger.info(f"Exported {len(logs)} logs to {export_path}")
        
        return str(export_path)


class SecurityAuditLogger:
    """
    Specialized logger for security events
    
    Tracks authentication, authorization, and sensitive operations
    """
    
    def __init__(self, vault_path: str):
        self.audit_logger = AuditLogger(vault_path)
        self.security_log_path = Path(vault_path) / "Logs" / "security.jsonl"
    
    def log_login(self, user: str, success: bool, ip_address: str = ""):
        """Log login attempt"""
        self.audit_logger.log(
            action=ActionType.SYSTEM_START if success else ActionType.SYSTEM_ERROR,
            actor=user,
            target="login",
            result="success" if success else "failure",
            metadata={"ip_address": ip_address},
        )
    
    def log_sensitive_action(self, action: str, user: str, details: Dict = None):
        """Log sensitive action (payments, deletes, etc.)"""
        self.audit_logger.log(
            action=ActionType.UNKNOWN,
            actor=user,
            target=action,
            approval_status="required",
            metadata=details or {},
        )
    
    def log_permission_change(self, user: str, resource: str, change: str):
        """Log permission changes"""
        self.audit_logger.log(
            action=ActionType.UNKNOWN,
            actor=user,
            target=resource,
            metadata={"permission_change": change},
        )
    
    def log_data_access(self, user: str, resource: str, action: str = "read"):
        """Log sensitive data access"""
        self.audit_logger.log(
            action=ActionType.FILE_READ if action == "read" else ActionType.UNKNOWN,
            actor=user,
            target=resource,
            metadata={"access_type": action},
        )


def create_audit_logger(vault_path: str) -> AuditLogger:
    """Factory function to create audit logger"""
    return AuditLogger(vault_path)


if __name__ == "__main__":
    import sys
    
    vault_path = sys.argv[1] if len(sys.argv) > 1 else "./AI_Employee_Vault"
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Test audit logger
    logger = AuditLogger(vault_path)
    
    # Log some test actions
    logger.log(
        action=ActionType.EMAIL_SEND,
        actor="claude_code",
        target="client@example.com",
        parameters={"subject": "Invoice #123"},
        approval_status="approved",
        approved_by="human",
        result="success",
    )
    
    logger.log_mcp_call(
        server="odoo-mcp",
        tool="create_invoice_draft",
        arguments={"partner_name": "Client A"},
        result="success",
    )
    
    logger.log_approval(
        action_type="invoice",
        approval_id="ODOO_INVOICE_20260101",
        status="approved",
        approved_by="human",
    )
    
    # Generate report
    report = logger.generate_audit_report(
        start_date=datetime.now() - timedelta(days=7),
        end_date=datetime.now(),
    )
    
    print("\nAudit Report:")
    print(json.dumps(report, indent=2))
    
    print("\nAudit logging system test complete")
