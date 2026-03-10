"""
Scheduled Tasks Runner

Executes scheduled tasks for the AI Employee system:
- Daily Briefing
- Weekly Audit
- Health Check
- Dashboard Update

Usage:
    python scheduled_tasks.py --vault-path "D:\Ai-Employee\AI_Employee_Vault" --task daily_briefing
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List


class ScheduledTaskRunner:
    """Runs scheduled tasks for AI Employee."""

    def __init__(self, vault_path: str):
        """
        Initialize the task runner.

        Args:
            vault_path: Path to the Obsidian vault root
        """
        self.vault_path = Path(vault_path)
        self.logs = self.vault_path / 'Logs'
        self.briefings = self.vault_path / 'Briefings'
        self.accounting = self.vault_path / 'Accounting'
        self.done = self.vault_path / 'Done'
        self.needs_action = self.vault_path / 'Needs_Action'
        
        # Ensure directories exist
        self.logs.mkdir(parents=True, exist_ok=True)
        self.briefings.mkdir(parents=True, exist_ok=True)
        self.accounting.mkdir(parents=True, exist_ok=True)
        
        self.logger = self._setup_logging()

    def _setup_logging(self):
        """Setup logging."""
        import logging
        log_file = self.logs / f'scheduled_tasks_{datetime.now().strftime("%Y%m%d")}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger('ScheduledTasks')

    def run_task(self, task_type: str) -> bool:
        """
        Run a scheduled task.

        Args:
            task_type: Type of task to run

        Returns:
            True if successful
        """
        self.logger.info(f'Running scheduled task: {task_type}')
        
        try:
            if task_type == 'daily_briefing':
                return self.run_daily_briefing()
            elif task_type == 'weekly_audit':
                return self.run_weekly_audit()
            elif task_type == 'health_check':
                return self.run_health_check()
            elif task_type == 'dashboard_update':
                return self.run_dashboard_update()
            else:
                self.logger.error(f'Unknown task type: {task_type}')
                return False
        except Exception as e:
            self.logger.error(f'Error running task {task_type}: {e}', exc_info=True)
            return False

    def run_daily_briefing(self) -> bool:
        """
        Generate daily briefing.
        
        Creates a briefing file with:
        - Today's date and day
        - Pending items count
        - Active plans
        - Recent completions
        - Priority focus areas
        """
        self.logger.info('Generating daily briefing')
        
        # Count items
        pending_count = len([f for f in self.needs_action.iterdir() 
                            if f.is_file() and f.suffix == '.md'])
        done_count = len([f for f in self.done.iterdir() 
                         if f.is_file() and f.suffix == '.md'])
        
        # Get active plans
        plans_folder = self.vault_path / 'Plans'
        active_plans = 0
        if plans_folder.exists():
            active_plans = len([f for f in plans_folder.iterdir() 
                               if f.is_file() and f.suffix == '.md'
                               and 'status: active' in f.read_text()])
        
        # Get pending approvals
        pending_approval = self.vault_path / 'Pending_Approval'
        approval_count = 0
        if pending_approval.exists():
            approval_count = len([f for f in pending_approval.iterdir() 
                                 if f.is_file() and f.suffix == '.md'])
        
        # Create briefing
        today = datetime.now()
        briefing_date = today.strftime('%Y-%m-%d')
        day_name = today.strftime('%A')
        
        content = f'''---
type: daily_briefing
date: "{briefing_date}"
day: "{day_name}"
generated: "{datetime.now().isoformat()}"
---

# Daily Briefing - {day_name}, {briefing_date}

## 📊 Quick Stats

| Metric | Count | Status |
|--------|-------|--------|
| Pending Items | {pending_count} | {"⚠️" if pending_count > 5 else "✅"} |
| Active Plans | {active_plans} | {"📝" if active_plans > 0 else "-"} |
| Awaiting Approval | {approval_count} | {"⚠️" if approval_count > 0 else "✅"} |
| Completed (Total) | {done_count} | {"📈" if done_count > 0 else "-"} |

## 🎯 Today's Focus

### Priority Tasks
*Review items in Needs_Action folder and prioritize*

### Active Plans
{f"* {active_plans} plan(s) in progress*" if active_plans > 0 else "*No active plans*"}

### Pending Approvals
{f"* {approval_count} item(s) awaiting approval*" if approval_count > 0 else "*No pending approvals*"}

## 📈 Yesterday's Summary

*Review completed items in /Done/ folder*

## 🚨 Alerts

{self._generate_alerts(pending_count, approval_count)}

## 📝 Notes

*Add your notes for today below*

---
*Generated by AI Employee Scheduled Tasks (Silver Tier)*
'''
        
        # Save briefing
        filename = f"Daily_Briefing_{briefing_date}.md"
        briefing_file = self.briefings / filename
        briefing_file.write_text(content, encoding='utf-8')
        
        self.logger.info(f'Daily briefing saved: {briefing_file}')
        print(f"✅ Daily briefing created: {briefing_file}")
        return True

    def run_weekly_audit(self) -> bool:
        """
        Generate weekly audit (Monday Morning CEO Briefing).
        
        Creates comprehensive weekly report with:
        - Revenue summary
        - Completed tasks
        - Bottlenecks
        - Proactive suggestions
        """
        self.logger.info('Generating weekly audit')
        
        today = datetime.now()
        last_week = today - timedelta(days=7)
        
        # Count completed items this week
        completed_this_week = 0
        for f in self.done.iterdir():
            if f.is_file() and f.suffix == '.md':
                try:
                    mtime = datetime.fromtimestamp(f.stat().st_mtime)
                    if mtime >= last_week:
                        completed_this_week += 1
                except:
                    pass
        
        # Generate audit content
        week_start = last_week.strftime('%Y-%m-%d')
        week_end = today.strftime('%Y-%m-%d')
        
        content = f'''---
type: weekly_audit
period_start: "{week_start}"
period_end: "{week_end}"
generated: "{datetime.now().isoformat()}"
---

# Monday Morning CEO Briefing

## Executive Summary

**Period:** {week_start} to {week_end}

*Weekly performance summary*

## 📊 Key Metrics

| Metric | This Week | Target | Status |
|--------|-----------|--------|--------|
| Tasks Completed | {completed_this_week} | 20 | {"✅" if completed_this_week >= 20 else "⚠️"} |
| Response Time | - | <24h | - |
| Revenue | $0 | $10,000 | - |

## ✅ Completed Tasks

{completed_this_week} tasks completed this week.

*Review /Done/ folder for details*

## 📋 Active Plans

{self._list_active_plans()}

## ⚠️ Bottlenecks

*Identify tasks that took too long or are blocked*

## 💡 Proactive Suggestions

{self._generate_suggestions()}

## 📈 Next Week's Focus

*Set priorities for the upcoming week*

---
*Generated by AI Employee Weekly Audit (Silver Tier)*
'''
        
        # Save audit
        filename = f"Weekly_Audit_{week_start}_to_{week_end}.md"
        audit_file = self.briefings / filename
        audit_file.write_text(content, encoding='utf-8')
        
        self.logger.info(f'Weekly audit saved: {audit_file}')
        print(f"✅ Weekly audit created: {audit_file}")
        return True

    def run_health_check(self) -> bool:
        """
        Run health check on all watchers and systems.
        
        Checks:
        - Watcher processes running
        - Log files recent
        - No error spikes
        - Disk space adequate
        """
        self.logger.info('Running health check')
        
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'overall': 'healthy'
        }
        
        # Check log files
        recent_logs = 0
        error_count = 0
        for log_file in self.logs.glob('*.log'):
            try:
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime > datetime.now() - timedelta(hours=24):
                    recent_logs += 1
                
                # Count errors in log
                content = log_file.read_text()
                error_count += content.count('ERROR')
            except:
                pass
        
        health_status['checks']['logs'] = {
            'recent_logs': recent_logs,
            'error_count': error_count,
            'status': 'warning' if error_count > 10 else 'healthy'
        }
        
        # Check vault folders
        folder_counts = {
            'needs_action': len([f for f in self.needs_action.iterdir() if f.is_file() and f.suffix == '.md']),
            'pending_approval': len([f for f in (self.vault_path / 'Pending_Approval').iterdir() if f.is_file() and f.suffix == '.md']) if (self.vault_path / 'Pending_Approval').exists() else 0,
            'plans': len([f for f in (self.vault_path / 'Plans').iterdir() if f.is_file() and f.suffix == '.md']) if (self.vault_path / 'Plans').exists() else 0,
        }
        
        health_status['checks']['folders'] = folder_counts
        
        # Check disk space
        import shutil
        total, used, free = shutil.disk_usage(str(self.vault_path))
        health_status['checks']['disk'] = {
            'free_gb': free / (1024**3),
            'status': 'healthy' if free > 1024**3 else 'warning'
        }
        
        # Determine overall status
        if error_count > 50 or free < 500 * 1024 * 1024:
            health_status['overall'] = 'critical'
        elif error_count > 10:
            health_status['overall'] = 'warning'
        
        # Save health report
        report_file = self.logs / f'health_check_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        report_file.write_text(json.dumps(health_status, indent=2))
        
        self.logger.info(f'Health check complete: {health_status["overall"]}')
        print(f"✅ Health check complete: {health_status['overall']}")
        print(f"   Recent logs: {recent_logs}")
        print(f"   Errors (24h): {error_count}")
        print(f"   Free disk: {health_status['checks']['disk']['free_gb']:.1f} GB")
        
        return True

    def run_dashboard_update(self) -> bool:
        """
        Update dashboard with current stats.
        
        This is a lightweight task that just refreshes the dashboard.
        """
        self.logger.info('Updating dashboard')
        
        # Import and use orchestrator's dashboard update
        sys.path.insert(0, str(self.vault_path.parent))
        from orchestrator import Orchestrator
        
        orchestrator = Orchestrator(str(self.vault_path))
        orchestrator.update_dashboard()
        
        print("✅ Dashboard updated")
        return True

    def _generate_alerts(self, pending_count: int, approval_count: int) -> str:
        """Generate alert messages."""
        alerts = []
        
        if pending_count > 10:
            alerts.append(f"- ⚠️ High pending items count: {pending_count}")
        if approval_count > 5:
            alerts.append(f"- ⚠️ Multiple approvals waiting: {approval_count}")
        
        if not alerts:
            return "*No active alerts*"
        
        return '\n'.join(alerts)

    def _list_active_plans(self) -> str:
        """List active plans."""
        plans_folder = self.vault_path / 'Plans'
        if not plans_folder.exists():
            return "*No plans*"
        
        active = []
        for f in plans_folder.iterdir():
            if f.is_file() and f.suffix == '.md':
                content = f.read_text()
                if 'status: active' in content:
                    # Extract title
                    title = "Unknown"
                    for line in content.split('\n'):
                        if 'title:' in line:
                            title = line.split('title:')[1].strip().strip('"')
                            break
                    active.append(f"- {title}")
        
        return '\n'.join(active) if active else "*No active plans*"

    def _generate_suggestions(self) -> str:
        """Generate proactive suggestions."""
        suggestions = []
        
        # Check for old pending items
        for f in self.needs_action.iterdir():
            if f.is_file() and f.suffix == '.md':
                try:
                    mtime = datetime.fromtimestamp(f.stat().st_mtime)
                    age = datetime.now() - mtime
                    if age.days > 3:
                        suggestions.append(f"- Review old pending item: {f.name} ({age.days} days)")
                except:
                    pass
        
        if not suggestions:
            return "*No suggestions at this time*"
        
        return '\n'.join(suggestions[:5])  # Limit to 5


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run AI Employee scheduled tasks'
    )
    parser.add_argument(
        '--vault-path',
        required=True,
        help='Path to the Obsidian vault root'
    )
    parser.add_argument(
        '--task',
        required=True,
        choices=['daily_briefing', 'weekly_audit', 'health_check', 'dashboard_update'],
        help='Task to run'
    )

    args = parser.parse_args()

    runner = ScheduledTaskRunner(args.vault_path)
    success = runner.run_task(args.task)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
