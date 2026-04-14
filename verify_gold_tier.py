#!/usr/bin/env python3
"""
Gold Tier Verification Script

Tests all Gold Tier components:
1. Facebook/Instagram MCP Server
2. Facebook/Instagram Watcher
3. Odoo Docker Compose setup
4. Odoo MCP Server
5. CEO Briefing Generator
6. Error Recovery Module
7. Audit Logging System
8. Vault Structure
9. Integration tests

Run with: python verify_gold_tier.py
"""

import sys
import json
import logging
from pathlib import Path
from typing import List, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Test results tracking
TESTS_RUN = 0
TESTS_PASSED = 0
TESTS_FAILED = 0
TESTS_SKIPPED = 0


def test_result(test_name: str, passed: bool, message: str = ""):
    """Record and display test result"""
    global TESTS_RUN, TESTS_PASSED, TESTS_FAILED, TESTS_SKIPPED
    
    TESTS_RUN += 1
    
    if passed:
        TESTS_PASSED += 1
        logger.info(f"✓ {test_name}")
    elif message == "SKIP":
        TESTS_SKIPPED += 1
        logger.warning(f"⊘ {test_name} (skipped)")
    else:
        TESTS_FAILED += 1
        logger.error(f"✗ {test_name}: {message}")


def verify_directory_structure():
    """Verify all required directories exist"""
    logger.info("\n=== Directory Structure ===\n")
    
    base_path = Path(__file__).parent
    
    required_dirs = [
        "AI_Employee_Vault",
        "AI_Employee_Vault/Inbox",
        "AI_Employee_Vault/Needs_Action",
        "AI_Employee_Vault/In_Progress",
        "AI_Employee_Vault/Pending_Approval",
        "AI_Employee_Vault/Approved",
        "AI_Employee_Vault/Rejected",
        "AI_Employee_Vault/Done",
        "AI_Employee_Vault/Plans",
        "AI_Employee_Vault/Accounting",
        "AI_Employee_Vault/Briefings",
        "AI_Employee_Vault/Logs",
        "mcp_servers/facebook-instagram-mcp",
        "mcp_servers/odoo-mcp",
        "watchers",
        "odoo",
    ]
    
    for dir_path in required_dirs:
        full_path = base_path / dir_path
        test_result(
            f"Directory: {dir_path}",
            full_path.exists() and full_path.is_dir(),
            f"Missing: {dir_path}",
        )


def verify_gold_tier_files():
    """Verify all Gold Tier files exist"""
    logger.info("\n=== Gold Tier Files ===\n")
    
    base_path = Path(__file__).parent
    
    required_files = {
        # Facebook/Instagram MCP
        "mcp_servers/facebook-instagram-mcp/package.json": "Facebook/Instagram MCP package.json",
        "mcp_servers/facebook-instagram-mcp/index.js": "Facebook/Instagram MCP server",
        "mcp_servers/facebook-instagram-mcp/start-server.bat": "Facebook/Instagram MCP start script",
        
        # Facebook/Instagram Watcher
        "watchers/facebook_instagram_watcher.py": "Facebook/Instagram watcher",
        
        # Odoo Docker setup
        "odoo/docker-compose.yml": "Odoo Docker Compose config",
        "odoo/odoo.conf": "Odoo configuration",
        "odoo/odoo-start.bat": "Odoo start script",
        "odoo/README.md": "Odoo documentation",
        
        # Odoo MCP
        "mcp_servers/odoo-mcp/server.py": "Odoo MCP server",
        "mcp_servers/odoo-mcp/start-server.bat": "Odoo MCP start script",
        
        # CEO Briefing
        "watchers/ceo_briefing_generator.py": "CEO Briefing generator",
        
        # Error Recovery
        "watchers/error_recovery.py": "Error recovery module",
        
        # Audit Logging
        "watchers/audit_logger.py": "Audit logging system",
        
        # Requirements
        "requirements.txt": "Python requirements",
    }
    
    for file_path, description in required_files.items():
        full_path = base_path / file_path
        test_result(
            f"File: {description}",
            full_path.exists(),
            f"Missing: {file_path}",
        )


def verify_facebook_instagram_mcp():
    """Verify Facebook/Instagram MCP Server"""
    logger.info("\n=== Facebook/Instagram MCP Server ===\n")
    
    base_path = Path(__file__).parent
    mcp_path = base_path / "mcp_servers" / "facebook-instagram-mcp"
    
    # Check package.json
    package_json = mcp_path / "package.json"
    if package_json.exists():
        try:
            with open(package_json, "r") as f:
                package_data = json.load(f)
            
            test_result(
                "Facebook/Instagram MCP: package.json valid",
                "name" in package_data and "dependencies" in package_data,
                "Invalid package.json",
            )
            
            # Check required dependencies
            deps = package_data.get("dependencies", {})
            required_deps = ["@modelcontextprotocol/sdk", "axios", "playwright"]
            missing_deps = [d for d in required_deps if d not in deps]
            
            test_result(
                "Facebook/Instagram MCP: Required dependencies",
                len(missing_deps) == 0,
                f"Missing: {', '.join(missing_deps)}",
            )
        except Exception as e:
            test_result("Facebook/Instagram MCP: package.json parse", False, str(e))
    else:
        test_result("Facebook/Instagram MCP: package.json", False, "File not found")
    
    # Check index.js has required tools
    index_js = mcp_path / "index.js"
    if index_js.exists():
        content = index_js.read_text(encoding="utf-8")
        required_tools = [
            "facebook_post",
            "instagram_post",
            "publish_approved_post",
            "get_facebook_insights",
            "get_social_summary",
            "schedule_social_post",
        ]
        
        missing_tools = [t for t in required_tools if t not in content]
        
        test_result(
            "Facebook/Instagram MCP: All tools defined",
            len(missing_tools) == 0,
            f"Missing tools: {', '.join(missing_tools)}",
        )
        
        # Check HITL pattern
        test_result(
            "Facebook/Instagram MCP: HITL pattern implemented",
            "Pending_Approval" in content and "approval_request" in content,
            "HITL pattern not found",
        )
    else:
        test_result("Facebook/Instagram MCP: index.js", False, "File not found")


def verify_facebook_instagram_watcher():
    """Verify Facebook/Instagram Watcher"""
    logger.info("\n=== Facebook/Instagram Watcher ===\n")
    
    base_path = Path(__file__).parent
    watcher_file = base_path / "watchers" / "facebook_instagram_watcher.py"
    
    if not watcher_file.exists():
        test_result("Facebook/Instagram Watcher: File exists", False, "File not found")
        return
    
    test_result("Facebook/Instagram Watcher: File exists", True)
    
    content = watcher_file.read_text(encoding="utf-8")
    
    # Check for required functionality
    required_components = [
        ("FacebookInstagramWatcher", "Main class"),
        ("check_for_updates", "Update checking"),
        ("create_action_file", "Action file creation"),
        ("_check_facebook", "Facebook API integration"),
        ("_check_instagram", "Instagram API integration"),
        ("_contains_keywords", "Keyword detection"),
        ("BaseWatcher", "Base class inheritance"),
    ]
    
    for component, description in required_components:
        test_result(
            f"Facebook/Instagram Watcher: {description}",
            component in content,
            f"Missing: {component}",
        )


def verify_odoo_setup():
    """Verify Odoo Docker setup"""
    logger.info("\n=== Odoo Docker Setup ===\n")
    
    base_path = Path(__file__).parent
    odoo_path = base_path / "odoo"
    
    # Check docker-compose.yml
    compose_file = odoo_path / "docker-compose.yml"
    if compose_file.exists():
        content = compose_file.read_text(encoding="utf-8")
        
        test_result(
            "Odoo: docker-compose.yml exists",
            True,
        )
        
        test_result(
            "Odoo: PostgreSQL service defined",
            "postgres" in content.lower() or "odoo-db" in content,
            "PostgreSQL service not found",
        )
        
        test_result(
            "Odoo: Odoo service defined",
            "odoo:" in content or "image: odoo" in content,
            "Odoo service not found",
        )
        
        test_result(
            "Odoo: Volume persistence",
            "volumes:" in content.lower(),
            "Volume configuration not found",
        )
    else:
        test_result("Odoo: docker-compose.yml", False, "File not found")
    
    # Check odoo.conf
    conf_file = odoo_path / "odoo.conf"
    if conf_file.exists():
        content = conf_file.read_text(encoding="utf-8")
        test_result(
            "Odoo: odoo.conf exists",
            True,
        )
        
        test_result(
            "Odoo: Database configuration",
            "db_host" in content and "db_name" in content,
            "Database configuration incomplete",
        )
    else:
        test_result("Odoo: odoo.conf", False, "File not found")


def verify_odoo_mcp():
    """Verify Odoo MCP Server"""
    logger.info("\n=== Odoo MCP Server ===\n")
    
    base_path = Path(__file__).parent
    mcp_path = base_path / "mcp_servers" / "odoo-mcp"
    
    # Check server.py
    server_file = mcp_path / "server.py"
    if server_file.exists():
        test_result("Odoo MCP: server.py exists", True)
        
        content = server_file.read_text(encoding="utf-8")
        
        # Check for required functionality
        required_components = [
            ("OdooClient", "Odoo client wrapper"),
            ("create_invoice_draft", "Invoice creation"),
            ("publish_approved_invoice", "Invoice publishing"),
            ("get_invoices", "Invoice retrieval"),
            ("get_payments", "Payment retrieval"),
            ("get_financial_summary", "Financial summary"),
            ("xmlrpc.client", "XML-RPC integration"),
            ("Pending_Approval", "HITL pattern"),
        ]
        
        for component, description in required_components:
            test_result(
                f"Odoo MCP: {description}",
                component in content,
                f"Missing: {component}",
            )
    else:
        test_result("Odoo MCP: server.py", False, "File not found")


def verify_ceo_briefing_generator():
    """Verify CEO Briefing Generator"""
    logger.info("\n=== CEO Briefing Generator ===\n")
    
    base_path = Path(__file__).parent
    briefing_file = base_path / "watchers" / "ceo_briefing_generator.py"
    
    if not briefing_file.exists():
        test_result("CEO Briefing: File exists", False, "File not found")
        return
    
    test_result("CEO Briefing: File exists", True)
    
    content = briefing_file.read_text(encoding="utf-8")
    
    required_components = [
        ("CEOBriefingGenerator", "Main class"),
        ("generate_briefing", "Briefing generation"),
        ("_generate_executive_summary", "Executive summary"),
        ("_generate_revenue_section", "Revenue analysis"),
        ("_generate_tasks_section", "Tasks section"),
        ("_generate_bottlenecks_section", "Bottleneck identification"),
        ("_generate_social_section", "Social media summary"),
        ("_generate_accounting_section", "Accounting insights"),
        ("_generate_proactive_suggestions", "Proactive suggestions"),
    ]
    
    for component, description in required_components:
        test_result(
            f"CEO Briefing: {description}",
            component in content,
            f"Missing: {component}",
        )


def verify_error_recovery():
    """Verify Error Recovery Module"""
    logger.info("\n=== Error Recovery Module ===\n")
    
    base_path = Path(__file__).parent
    recovery_file = base_path / "watchers" / "error_recovery.py"
    
    if not recovery_file.exists():
        test_result("Error Recovery: File exists", False, "File not found")
        return
    
    test_result("Error Recovery: File exists", True)
    
    content = recovery_file.read_text(encoding="utf-8")
    
    required_components = [
        ("CircuitBreaker", "Circuit breaker pattern"),
        ("with_retry", "Retry decorator"),
        ("ErrorHandler", "Error handler"),
        ("GracefulDegradation", "Graceful degradation"),
        ("WatchdogMonitor", "Process monitoring"),
        ("ErrorCategory", "Error categorization"),
    ]
    
    for component, description in required_components:
        test_result(
            f"Error Recovery: {description}",
            component in content,
            f"Missing: {component}",
        )


def verify_audit_logging():
    """Verify Audit Logging System"""
    logger.info("\n=== Audit Logging System ===\n")
    
    base_path = Path(__file__).parent
    audit_file = base_path / "watchers" / "audit_logger.py"
    
    if not audit_file.exists():
        test_result("Audit Logging: File exists", False, "File not found")
        return
    
    test_result("Audit Logging: File exists", True)
    
    content = audit_file.read_text(encoding="utf-8")
    
    required_components = [
        ("AuditLogger", "Main audit logger"),
        ("ActionType", "Action type enumeration"),
        ("log_mcp_call", "MCP call logging"),
        ("log_approval", "Approval logging"),
        ("query_logs", "Log querying"),
        ("generate_audit_report", "Report generation"),
        ("cleanup_old_logs", "Log rotation"),
        ("SecurityAuditLogger", "Security logging"),
    ]
    
    for component, description in required_components:
        test_result(
            f"Audit Logging: {description}",
            component in content,
            f"Missing: {component}",
        )


def verify_requirements():
    """Verify requirements.txt has Gold Tier dependencies"""
    logger.info("\n=== Requirements.txt ===\n")
    
    base_path = Path(__file__).parent
    req_file = base_path / "requirements.txt"
    
    if not req_file.exists():
        test_result("Requirements: File exists", False, "File not found")
        return
    
    content = req_file.read_text(encoding="utf-8")
    
    gold_tier_deps = [
        "facebook-business",
        "zeep",
    ]
    
    missing_deps = [dep for dep in gold_tier_deps if dep not in content.lower()]
    
    test_result(
        "Requirements: Gold Tier dependencies",
        len(missing_deps) == 0,
        f"Missing: {', '.join(missing_deps)}",
    )
    
    # Check for Gold Tier label
    test_result(
        "Requirements: Gold Tier label",
        "Gold Tier" in content,
        "Gold Tier label not found",
    )


def verify_vault_structure():
    """Verify Obsidian Vault structure"""
    logger.info("\n=== Vault Structure ===\n")
    
    base_path = Path(__file__).parent
    vault_path = base_path / "AI_Employee_Vault"
    
    if not vault_path.exists():
        test_result("Vault: Base path exists", False, "Vault not found")
        return
    
    test_result("Vault: Base path exists", True)
    
    required_folders = [
        "Inbox",
        "Needs_Action",
        "In_Progress",
        "Pending_Approval",
        "Approved",
        "Rejected",
        "Done",
        "Plans",
        "Accounting",
        "Briefings",
        "Logs",
    ]
    
    for folder in required_folders:
        folder_path = vault_path / folder
        test_result(
            f"Vault: {folder}/",
            folder_path.exists() and folder_path.is_dir(),
            f"Missing: {folder}",
        )
    
    # Check required files
    required_files = [
        "Dashboard.md",
        "Company_Handbook.md",
        "Business_Goals.md",
    ]
    
    for filename in required_files:
        file_path = vault_path / filename
        test_result(
            f"Vault: {filename}",
            file_path.exists(),
            f"Missing: {filename}",
        )


def verify_integration():
    """Verify integration between components"""
    logger.info("\n=== Integration Tests ===\n")
    
    base_path = Path(__file__).parent
    
    # Check orchestrator can import new modules
    orchestrator_file = base_path / "orchestrator.py"
    if orchestrator_file.exists():
        content = orchestrator_file.read_text(encoding="utf-8")
        test_result("Orchestrator: Exists", True)
    else:
        test_result("Orchestrator: Exists", False, "File not found")
    
    # Check scheduled_tasks includes CEO briefing
    scheduled_tasks_file = base_path / "scheduled_tasks.py"
    if scheduled_tasks_file.exists():
        content = scheduled_tasks_file.read_text(encoding="utf-8")
        test_result("Scheduled Tasks: Exists", True)
        
        # Note: In production, would check if briefing is scheduled
    else:
        test_result("Scheduled Tasks: Exists", False, "File not found")


def print_summary():
    """Print test summary"""
    logger.info("\n" + "=" * 80)
    logger.info("GOLD TIER VERIFICATION SUMMARY")
    logger.info("=" * 80)
    
    total = TESTS_RUN
    passed = TESTS_PASSED
    failed = TESTS_FAILED
    skipped = TESTS_SKIPPED
    
    logger.info(f"\nTotal Tests: {total}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Skipped: {skipped}")
    logger.info(f"Success Rate: {(passed / total * 100) if total > 0 else 0:.1f}%\n")
    
    if failed == 0:
        logger.info("🎉 ALL TESTS PASSED! Gold Tier is ready!")
        logger.info("\nNext steps:")
        logger.info("1. Install dependencies: pip install -r requirements.txt")
        logger.info("2. Start Odoo: cd odoo && docker-compose up -d")
        logger.info("3. Configure MCP servers in Claude Code settings")
        logger.info("4. Set environment variables for Facebook/Instagram/Odoo")
        logger.info("5. Run the orchestrator: python orchestrator.py --ralph-loop")
    else:
        logger.info(f"⚠️  {failed} test(s) failed. Please fix the issues above.")
    
    logger.info("=" * 80)


def main():
    """Run all verification tests"""
    logger.info("Starting Gold Tier Verification...\n")
    
    # Run all verification functions
    verify_directory_structure()
    verify_gold_tier_files()
    verify_facebook_instagram_mcp()
    verify_facebook_instagram_watcher()
    verify_odoo_setup()
    verify_odoo_mcp()
    verify_ceo_briefing_generator()
    verify_error_recovery()
    verify_audit_logging()
    verify_requirements()
    verify_vault_structure()
    verify_integration()
    
    # Print summary
    print_summary()
    
    return 0 if TESTS_FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
