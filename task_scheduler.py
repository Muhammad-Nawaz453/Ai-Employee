"""
Task Scheduler Integration

Creates and manages scheduled tasks for the AI Employee system.
Supports Windows Task Scheduler and cron (Linux/Mac).

Features:
- Daily Briefing at 8:00 AM
- Weekly Audit on Sunday at 7:00 PM
- Hourly watcher health check

Usage:
    python task_scheduler.py install --vault-path "D:\Ai-Employee\AI_Employee_Vault"
    python task_scheduler.py list
    python task_scheduler.py remove --task-name "AI Employee Daily Briefing"
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import xml.etree.ElementTree as ET


class TaskSchedulerManager:
    """
    Manages scheduled tasks for AI Employee.
    
    Windows: Uses schtasks.exe
    Linux/Mac: Uses cron
    """

    def __init__(self, vault_path: str, project_path: str = None):
        """
        Initialize the task scheduler manager.

        Args:
            vault_path: Path to the Obsidian vault root
            project_path: Path to the project root (default: current directory)
        """
        self.vault_path = Path(vault_path)
        self.project_path = Path(project_path) if project_path else Path(__file__).parent.parent
        self.python_exe = sys.executable
        self.is_windows = sys.platform == 'win32'
        
        # Task definitions
        self.tasks = {
            'daily_briefing': {
                'name': 'AI Employee Daily Briefing',
                'schedule': '08:00',  # 8:00 AM daily
                'command': self._build_command('daily_briefing'),
                'description': 'Generate daily briefing in Obsidian vault',
            },
            'weekly_audit': {
                'name': 'AI Employee Weekly Audit',
                'schedule': 'SUN 19:00',  # Sunday 7:00 PM
                'command': self._build_command('weekly_audit'),
                'description': 'Weekly business audit and CEO briefing',
            },
            'health_check': {
                'name': 'AI Employee Health Check',
                'schedule': 'HOURLY',  # Every hour
                'command': self._build_command('health_check'),
                'description': 'Check watcher health and log status',
            },
            'dashboard_update': {
                'name': 'AI Employee Dashboard Update',
                'schedule': '*/15 * * * *',  # Every 15 minutes (cron format)
                'command': self._build_command('dashboard_update'),
                'description': 'Update dashboard with current stats',
            },
        }

    def _build_command(self, task_type: str) -> str:
        """Build command for a task type."""
        script = self.project_path / 'scheduled_tasks.py'
        vault = self.vault_path
        
        cmd = f'"{self.python_exe}" "{script}" --vault-path "{vault}" --task {task_type}'
        return cmd

    def install_all(self) -> bool:
        """
        Install all scheduled tasks.

        Returns:
            True if all tasks installed successfully
        """
        success = True
        for task_key, task_def in self.tasks.items():
            print(f"Installing task: {task_def['name']}...")
            if not self.install_task(task_key):
                success = False
        return success

    def install_task(self, task_key: str) -> bool:
        """
        Install a specific scheduled task.

        Args:
            task_key: Key from self.tasks

        Returns:
            True if successful
        """
        if task_key not in self.tasks:
            print(f"Unknown task: {task_key}")
            return False

        task = self.tasks[task_key]
        
        if self.is_windows:
            return self._install_windows(task)
        else:
            return self._install_cron(task)

    def _install_windows(self, task: dict) -> bool:
        """Install task using Windows Task Scheduler."""
        task_name = task['name']
        command = task['command']
        schedule = task['schedule']
        description = task['description']

        try:
            # Build schtasks command
            if schedule == 'HOURLY':
                schedule_cmd = '/SC HOURLY /MO 1'
            elif 'SUN' in schedule:
                # Weekly on Sunday
                time_part = schedule.split()[1] if ' ' in schedule else '19:00'
                schedule_cmd = f'/SC WEEKLY /D SUN /ST {time_part}'
            elif ':' in schedule and 'SUN' not in schedule:
                # Daily at specific time
                schedule_cmd = f'/SC DAILY /ST {schedule}'
            else:
                print(f"Unknown schedule format: {schedule}")
                return False

            # Create task
            schtasks_cmd = (
                f'schtasks /Create /F '
                f'/TN "{task_name}" '
                f'/TR "{command}" '
                f'{schedule_cmd} '
                f'/RL HIGHEST '
                f'/RU SYSTEM '
                f'/SCD "AI Employee System" '
                f'/MOTD '
                f'/Z '
                f'/F'
            )

            result = subprocess.run(
                schtasks_cmd,
                shell=True,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print(f"✅ Task installed: {task_name}")
                print(f"   Schedule: {schedule}")
                print(f"   Command: {command}")
                return True
            else:
                print(f"❌ Failed to install: {task_name}")
                print(f"   Error: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ Error installing task: {e}")
            return False

    def _install_cron(self, task: dict) -> bool:
        """Install task using cron."""
        task_name = task['name']
        command = task['command']
        schedule = task['schedule']

        try:
            # For cron, we use the schedule directly if it's in cron format
            if schedule in ['HOURLY', '08:00', 'SUN 19:00']:
                # Convert to cron format
                if schedule == 'HOURLY':
                    cron_schedule = '0 * * * *'
                elif ':' in schedule and 'SUN' not in schedule:
                    hour, minute = schedule.split(':')
                    cron_schedule = f'{minute} {hour} * * *'
                elif 'SUN' in schedule:
                    time_part = schedule.split()[1] if ' ' in schedule else '19:00'
                    hour, minute = time_part.split(':')
                    cron_schedule = f'{minute} {hour} * * 0'
                else:
                    cron_schedule = schedule

            # Add to crontab
            cron_line = f'# {task_name}\n{cron_schedule} {command}\n'
            
            # Get current crontab
            result = subprocess.run(
                'crontab -l',
                shell=True,
                capture_output=True,
                text=True
            )
            
            current_crontab = result.stdout if result.returncode == 0 else ''
            
            # Check if task already exists
            if task_name in current_crontab:
                print(f"⚠️  Task already exists: {task_name}")
                return True
            
            # Add new task
            new_crontab = current_crontab + '\n' + cron_line
            
            result = subprocess.run(
                'crontab -',
                shell=True,
                input=new_crontab,
                text=True,
                capture_output=True
            )
            
            if result.returncode == 0:
                print(f"✅ Task installed: {task_name}")
                print(f"   Schedule: {cron_schedule}")
                return True
            else:
                print(f"❌ Failed to install: {task_name}")
                print(f"   Error: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ Error installing task: {e}")
            return False

    def remove_task(self, task_name: str) -> bool:
        """
        Remove a scheduled task.

        Args:
            task_name: Name of the task to remove

        Returns:
            True if successful
        """
        if self.is_windows:
            try:
                result = subprocess.run(
                    f'schtasks /Delete /TN "{task_name}" /F',
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    print(f"✅ Task removed: {task_name}")
                    return True
                else:
                    print(f"❌ Failed to remove: {task_name}")
                    print(f"   Error: {result.stderr}")
                    return False
            except Exception as e:
                print(f"❌ Error removing task: {e}")
                return False
        else:
            # For cron, edit crontab
            try:
                result = subprocess.run(
                    'crontab -l',
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    print("No crontab found")
                    return False
                
                lines = result.stdout.split('\n')
                new_lines = []
                skip_next = False
                
                for line in lines:
                    if task_name in line:
                        skip_next = True
                        continue
                    if skip_next and line.strip() and not line.startswith('#'):
                        skip_next = False
                        continue
                    new_lines.append(line)
                
                new_crontab = '\n'.join(new_lines)
                
                result = subprocess.run(
                    'crontab -',
                    shell=True,
                    input=new_crontab,
                    text=True,
                    capture_output=True
                )
                
                if result.returncode == 0:
                    print(f"✅ Task removed: {task_name}")
                    return True
                else:
                    print(f"❌ Failed to remove: {task_name}")
                    return False
            except Exception as e:
                print(f"❌ Error removing task: {e}")
                return False

    def list_tasks(self) -> List[dict]:
        """
        List all installed tasks.

        Returns:
            List of task info dictionaries
        """
        installed = []
        
        if self.is_windows:
            try:
                result = subprocess.run(
                    'schtasks /Query /FO TABLE /NH',
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        for task_name, task_def in self.tasks.items():
                            if task_def['name'] in line:
                                installed.append({
                                    'name': task_def['name'],
                                    'schedule': task_def['schedule'],
                                    'status': 'Installed'
                                })
            except Exception as e:
                print(f"Error listing tasks: {e}")
        else:
            try:
                result = subprocess.run(
                    'crontab -l',
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    for task_name, task_def in self.tasks.items():
                        if task_def['name'] in result.stdout:
                            installed.append({
                                'name': task_def['name'],
                                'schedule': task_def['schedule'],
                                'status': 'Installed'
                            })
            except:
                pass
        
        return installed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Manage AI Employee scheduled tasks'
    )
    parser.add_argument(
        'action',
        choices=['install', 'install-all', 'remove', 'list', 'status'],
        help='Action to perform'
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
        '--task-name',
        default=None,
        help='Specific task name for install/remove'
    )

    args = parser.parse_args()

    manager = TaskSchedulerManager(
        vault_path=args.vault_path,
        project_path=args.project_path
    )

    if args.action == 'install-all':
        print("="*60)
        print("Installing all AI Employee scheduled tasks")
        print("="*60)
        success = manager.install_all()
        print("="*60)
        if success:
            print("✅ All tasks installed successfully")
        else:
            print("⚠️  Some tasks failed to install")
    
    elif args.action == 'install':
        if not args.task_name:
            print("Error: --task-name required for install")
            sys.exit(1)
        print(f"Installing task: {args.task_name}")
        if manager.install_task(args.task_name):
            print("✅ Task installed successfully")
        else:
            print("❌ Failed to install task")
            sys.exit(1)
    
    elif args.action == 'remove':
        if not args.task_name:
            print("Error: --task-name required for remove")
            sys.exit(1)
        print(f"Removing task: {args.task_name}")
        if manager.remove_task(args.task_name):
            print("✅ Task removed successfully")
        else:
            print("❌ Failed to remove task")
    
    elif args.action == 'list':
        print("="*60)
        print("AI Employee Scheduled Tasks")
        print("="*60)
        tasks = manager.list_tasks()
        if tasks:
            for task in tasks:
                print(f"  ✅ {task['name']}")
                print(f"     Schedule: {task['schedule']}")
                print()
        else:
            print("  No tasks found")
        print("="*60)
    
    elif args.action == 'status':
        print("="*60)
        print("AI Employee Task Scheduler Status")
        print("="*60)
        print(f"Platform: {'Windows' if manager.is_windows else 'Linux/Mac'}")
        print(f"Vault: {manager.vault_path}")
        print(f"Python: {manager.python_exe}")
        print()
        print("Available tasks:")
        for key, task in manager.tasks.items():
            print(f"  - {task['name']} ({key})")
            print(f"    Schedule: {task['schedule']}")
        print("="*60)


if __name__ == '__main__':
    main()
