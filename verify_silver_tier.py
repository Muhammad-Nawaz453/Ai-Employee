r"""
Silver Tier Verification Script

Comprehensive test suite for AI Employee Silver Tier features.

Tests:
1. Python dependencies
2. Watcher scripts (Gmail, WhatsApp, Filesystem)
3. MCP Servers (LinkedIn)
4. Orchestrator with Ralph Wiggum Loop
5. HITL Approval Workflow
6. Plan Manager
7. Task Scheduler
8. Scheduled Tasks

Usage:
    python verify_silver_tier.py --vault-path "D:\Ai-Employee\AI_Employee_Vault"
"""

import argparse
import subprocess
import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple


class SilverTierVerifier:
    """Verifies Silver Tier installation and functionality."""

    def __init__(self, vault_path: str, project_path: str = None):
        """
        Initialize the verifier.

        Args:
            vault_path: Path to the Obsidian vault root
            project_path: Path to the project root
        """
        self.vault_path = Path(vault_path)
        self.project_path = Path(project_path) if project_path else Path(__file__).parent
        self.results: List[Dict[str, Any]] = []
        
        # Required files
        self.required_files = [
            'watchers/base_watcher.py',
            'watchers/filesystem_watcher.py',
            'watchers/gmail_watcher.py',
            'watchers/whatsapp_watcher.py',
            'watchers/hitl_approval.py',
            'watchers/plan_manager.py',
            'orchestrator.py',
            'task_scheduler.py',
            'scheduled_tasks.py',
            'mcp_servers/linkedin-mcp/package.json',
            'mcp_servers/linkedin-mcp/index.js',
        ]
        
        # Required vault folders
        self.required_folders = [
            'Inbox',
            'Needs_Action',
            'Done',
            'Plans',
            'Pending_Approval',
            'Approved',
            'Rejected',
            'Accounting',
            'Briefings',
            'Logs',
        ]
        
        # Required vault files
        self.required_vault_files = [
            'Dashboard.md',
            'Company_Handbook.md',
            'Business_Goals.md',
        ]

    def log_result(self, category: str, test: str, passed: bool, message: str = ""):
        """Log a test result."""
        result = {
            'category': category,
            'test': test,
            'passed': passed,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        self.results.append(result)
        
        # Use ASCII-safe characters for Windows compatibility
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status}: {test}")
        if message:
            print(f"         {message}")

    def verify_python_dependencies(self) -> bool:
        """Verify all Python dependencies are installed."""
        print("\n" + "="*60)
        print("Checking Python Dependencies")
        print("="*60)
        
        required_packages = [
            ('watchdog', 'File system watching'),
            ('googleapiclient', 'Gmail API'),
            ('google.oauth2', 'Google OAuth'),
            ('playwright', 'WhatsApp automation'),
            ('requests', 'HTTP requests'),
            ('dotenv', 'Environment variables'),
            ('jsonschema', 'JSON validation'),
            ('schedule', 'Task scheduling'),
            ('rich', 'Terminal output'),
        ]
        
        all_passed = True
        
        for package, description in required_packages:
            try:
                __import__(package)
                self.log_result('Dependencies', f'{package} ({description})', True)
            except ImportError:
                self.log_result('Dependencies', f'{package} ({description})', False, 
                               f'Run: pip install {package.replace("googleapiclient", "google-api-python-client").replace("dotenv", "python-dotenv")}')
                all_passed = False
        
        return all_passed

    def verify_nodejs(self) -> bool:
        """Verify Node.js and npm are installed."""
        print("\n" + "="*60)
        print("Checking Node.js Installation")
        print("="*60)
        
        all_passed = True
        
        # Check Node.js
        try:
            result = subprocess.run(['node', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                self.log_result('Node.js', 'Node.js installed', True, result.stdout.strip())
            else:
                self.log_result('Node.js', 'Node.js installed', False, 'Node.js not found')
                all_passed = False
        except FileNotFoundError:
            self.log_result('Node.js', 'Node.js installed', False, 'Node.js not found')
            all_passed = False
        
        # Check npm
        try:
            result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                self.log_result('npm', 'npm installed', True, result.stdout.strip())
            else:
                self.log_result('npm', 'npm installed', False, 'npm not found')
                all_passed = False
        except FileNotFoundError:
            self.log_result('npm', 'npm installed', False, 'npm not found')
            all_passed = False
        
        return all_passed

    def verify_project_structure(self) -> bool:
        """Verify project file structure."""
        print("\n" + "="*60)
        print("Checking Project Structure")
        print("="*60)
        
        all_passed = True
        
        # Check required files
        for file_path in self.required_files:
            full_path = self.project_path / file_path
            if full_path.exists():
                self.log_result('Files', file_path, True)
            else:
                self.log_result('Files', file_path, False, 'File not found')
                all_passed = False
        
        return all_passed

    def verify_vault_structure(self) -> bool:
        """Verify Obsidian vault structure."""
        print("\n" + "="*60)
        print("Checking Vault Structure")
        print("="*60)
        
        all_passed = True
        
        # Check folders
        for folder in self.required_folders:
            folder_path = self.vault_path / folder
            if folder_path.exists() and folder_path.is_dir():
                self.log_result('Folders', folder, True)
            else:
                self.log_result('Folders', folder, False, 'Folder not found')
                all_passed = False
        
        # Check vault files
        for file_path in self.required_vault_files:
            full_path = self.vault_path / file_path
            if full_path.exists():
                self.log_result('Vault Files', file_path, True)
            else:
                self.log_result('Vault Files', file_path, False, 'File not found')
                all_passed = False
        
        return all_passed

    def verify_watchers_syntax(self) -> bool:
        """Verify watcher scripts have valid Python syntax."""
        print("\n" + "="*60)
        print("Checking Watcher Scripts Syntax")
        print("="*60)
        
        watchers = [
            'watchers/base_watcher.py',
            'watchers/filesystem_watcher.py',
            'watchers/gmail_watcher.py',
            'watchers/whatsapp_watcher.py',
            'watchers/hitl_approval.py',
            'watchers/plan_manager.py',
        ]
        
        all_passed = True
        
        for watcher in watchers:
            watcher_path = self.project_path / watcher
            if not watcher_path.exists():
                self.log_result('Syntax', watcher, False, 'File not found')
                all_passed = False
                continue
            
            try:
                result = subprocess.run(
                    [sys.executable, '-m', 'py_compile', str(watcher_path)],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    self.log_result('Syntax', watcher, True)
                else:
                    self.log_result('Syntax', watcher, False, result.stderr)
                    all_passed = False
            except Exception as e:
                self.log_result('Syntax', watcher, False, str(e))
                all_passed = False
        
        return all_passed

    def verify_orchestrator_syntax(self) -> bool:
        """Verify orchestrator has valid Python syntax."""
        print("\n" + "="*60)
        print("Checking Orchestrator Syntax")
        print("="*60)
        
        orchestrator_path = self.project_path / 'orchestrator.py'
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'py_compile', str(orchestrator_path)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.log_result('Syntax', 'orchestrator.py', True)
                
                # Check for Silver tier features
                content = orchestrator_path.read_text()
                has_ralph = 'RalphWiggumLoop' in content
                has_approval = 'ApprovalManager' in content
                has_plan = 'PlanManager' in content
                
                self.log_result('Features', 'Ralph Wiggum Loop', has_ralph)
                self.log_result('Features', 'HITL Approval', has_approval)
                self.log_result('Features', 'Plan Manager', has_plan)
                
                return has_ralph and has_approval and has_plan
            else:
                self.log_result('Syntax', 'orchestrator.py', False, result.stderr)
                return False
        except Exception as e:
            self.log_result('Syntax', 'orchestrator.py', False, str(e))
            return False

    def verify_mcp_server(self) -> bool:
        """Verify LinkedIn MCP server structure."""
        print("\n" + "="*60)
        print("Checking LinkedIn MCP Server")
        print("="*60)
        
        mcp_path = self.project_path / 'mcp_servers' / 'linkedin-mcp'
        all_passed = True
        
        # Check package.json
        package_json = mcp_path / 'package.json'
        if package_json.exists():
            self.log_result('MCP', 'package.json exists', True)
            try:
                content = json.loads(package_json.read_text())
                if '@modelcontextprotocol/sdk' in content.get('dependencies', {}):
                    self.log_result('MCP', 'MCP SDK dependency', True)
                else:
                    self.log_result('MCP', 'MCP SDK dependency', False, 'Not in package.json')
                    all_passed = False
            except:
                self.log_result('MCP', 'package.json valid', False)
                all_passed = False
        else:
            self.log_result('MCP', 'package.json exists', False)
            all_passed = False
        
        # Check index.js
        index_js = mcp_path / 'index.js'
        if index_js.exists():
            self.log_result('MCP', 'index.js exists', True)
            content = index_js.read_text()
            has_tools = 'TOOLS' in content
            has_linkedin_post = 'linkedin_post' in content
            has_hitle = 'HITL' in content or 'approval' in content.lower()
            
            self.log_result('MCP', 'Has tool definitions', has_tools)
            self.log_result('MCP', 'Has linkedin_post tool', has_linkedin_post)
            self.log_result('MCP', 'Has HITL pattern', has_hitle)
        else:
            self.log_result('MCP', 'index.js exists', False)
            all_passed = False
        
        return all_passed

    def verify_claude_code(self) -> bool:
        """Verify Claude Code is installed."""
        print("\n" + "="*60)
        print("Checking Claude Code Installation")
        print("="*60)
        
        try:
            result = subprocess.run(['claude', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                self.log_result('Claude Code', 'Claude Code installed', True, result.stdout.strip())
                return True
            else:
                self.log_result('Claude Code', 'Claude Code installed', False, 'Not found')
                return False
        except FileNotFoundError:
            self.log_result('Claude Code', 'Claude Code installed', False, 'Not found')
            return False

    def run_quick_test(self) -> bool:
        """Run a quick functional test."""
        print("\n" + "="*60)
        print("Running Quick Functional Test")
        print("="*60)
        
        # Test: Create a test action file
        test_file = self.vault_path / 'Needs_Action' / 'TEST_SilverTier.md'
        test_content = f'''---
type: test
created: {datetime.now().isoformat()}
status: pending
---

# Silver Tier Verification Test

This is a test file created by the verification script.

## Expected Actions

- [ ] AI Employee should detect this file
- [ ] Process according to Company Handbook
- [ ] Move to /Done/ when complete

---
*Test file - safe to delete*
'''
        
        try:
            test_file.write_text(test_content, encoding='utf-8')
            self.log_result('Functional', 'Create test file', True)
            
            # Verify file was created
            if test_file.exists():
                self.log_result('Functional', 'Test file exists', True)
                
                # Clean up
                test_file.unlink()
                self.log_result('Functional', 'Test file cleaned up', True)
                return True
            else:
                self.log_result('Functional', 'Test file exists', False)
                return False
        except Exception as e:
            self.log_result('Functional', 'Create test file', False, str(e))
            return False

    def generate_report(self) -> str:
        """Generate verification report."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r['passed'])
        failed = total - passed
        
        report = f"""
{'='*60}
Silver Tier Verification Report
{'='*60}

Total Tests: {total}
Passed: {passed} ({passed/total*100:.1f}%)
Failed: {failed} ({failed/total*100:.1f}%)

Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
        
        # Group by category
        categories = {}
        for result in self.results:
            cat = result['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(result)
        
        for category, results in categories.items():
            report += f"\n{category}:\n"
            report += "-" * 40 + "\n"
            for result in results:
                status = "[OK]" if result['passed'] else "[FAIL]"
                report += f"  {status} {result['test']}\n"
                if result['message']:
                    report += f"     {result['message']}\n"
        
        report += f"\n{'='*60}\n"
        
        if failed == 0:
            report += "SUCCESS: All tests passed! Silver Tier is ready.\n"
        else:
            report += f"WARNING: {failed} test(s) failed. Please review and fix.\n"
        
        report += "="*60 + "\n"
        
        return report

    def run_full_verification(self) -> bool:
        """Run all verification checks."""
        print("\n" + "="*60)
        print("AI Employee - Silver Tier Verification")
        print("="*60)
        print(f"Vault Path: {self.vault_path}")
        print(f"Project Path: {self.project_path}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # Run all checks
        checks = [
            ('Python Dependencies', self.verify_python_dependencies),
            ('Node.js', self.verify_nodejs),
            ('Project Structure', self.verify_project_structure),
            ('Vault Structure', self.verify_vault_structure),
            ('Watcher Syntax', self.verify_watchers_syntax),
            ('Orchestrator', self.verify_orchestrator_syntax),
            ('MCP Server', self.verify_mcp_server),
            ('Claude Code', self.verify_claude_code),
            ('Functional Test', self.run_quick_test),
        ]
        
        results = []
        for name, check in checks:
            try:
                result = check()
                results.append((name, result))
            except Exception as e:
                print(f"Error in {name}: {e}")
                results.append((name, False))
        
        # Generate report
        report = self.generate_report()
        print(report)
        
        # Save report
        report_file = self.vault_path / 'Logs' / f'verification_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(report, encoding='utf-8')
        print(f"\nReport saved to: {report_file}")
        
        # Return overall success
        all_passed = all(r[1] for r in results)
        return all_passed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Verify AI Employee Silver Tier installation'
    )
    parser.add_argument(
        '--vault-path',
        required=True,
        help='Path to the Obsidian vault root'
    )
    parser.add_argument(
        '--project-path',
        default=None,
        help='Path to the project root'
    )
    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Only generate report (skip tests)'
    )

    args = parser.parse_args()

    verifier = SilverTierVerifier(
        vault_path=args.vault_path,
        project_path=args.project_path
    )

    if args.report_only:
        print(verifier.generate_report())
    else:
        success = verifier.run_full_verification()
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
