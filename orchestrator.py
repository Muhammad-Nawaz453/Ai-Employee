"""
Orchestrator

Main coordination script for the AI Employee system.
Triggers Qwen Code to process items in Needs_Action folder.

Usage:
    python orchestrator.py --vault-path /path/to/vault
    python orchestrator.py --vault-path /path/to/vault --process-all
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import logging


class Orchestrator:
    """
    Orchestrates the AI Employee workflow.

    - Monitors Needs_Action folder for items to process
    - Triggers Qwen Code to analyze and act on items
    - Updates Dashboard.md with status
    """
    
    def __init__(self, vault_path: str, check_interval: int = 60):
        """
        Initialize the orchestrator.
        
        Args:
            vault_path: Path to the Obsidian vault root
            check_interval: Seconds between checks (default: 60)
        """
        self.vault_path = Path(vault_path)
        self.check_interval = check_interval
        
        # Folders
        self.needs_action = self.vault_path / 'Needs_Action'
        self.done = self.vault_path / 'Done'
        self.plans = self.vault_path / 'Plans'
        self.pending_approval = self.vault_path / 'Pending_Approval'
        self.approved = self.vault_path / 'Approved'
        self.logs = self.vault_path / 'Logs'
        self.dashboard = self.vault_path / 'Dashboard.md'
        
        # Ensure directories exist
        for folder in [self.needs_action, self.done, self.plans, 
                       self.pending_approval, self.approved, self.logs]:
            folder.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        
        self.logger.info(f'Orchestrator initialized')
        self.logger.info(f'Vault path: {self.vault_path}')
    
    def _setup_logging(self) -> None:
        """Setup logging to file and console."""
        log_dir = self.logs
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f'orchestrator_{datetime.now().strftime("%Y%m%d")}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('Orchestrator')
    
    def get_pending_items(self) -> List[Path]:
        """
        Get all .md files in Needs_Action folder.
        
        Returns:
            List of pending action files
        """
        try:
            items = [f for f in self.needs_action.iterdir() 
                    if f.is_file() and f.suffix == '.md' 
                    and not f.name.startswith('.')]
            return sorted(items, key=lambda f: f.stat().st_mtime)
        except Exception as e:
            self.logger.error(f'Error scanning Needs_Action: {e}')
            return []
    
    def get_approved_items(self) -> List[Path]:
        """
        Get all items in Approved folder ready for action.
        
        Returns:
            List of approved action files
        """
        try:
            items = [f for f in self.approved.iterdir() 
                    if f.is_file() and f.suffix == '.md']
            return sorted(items, key=lambda f: f.stat().st_mtime)
        except Exception as e:
            self.logger.error(f'Error scanning Approved: {e}')
            return []
    
    def count_folder_items(self, folder: Path) -> int:
        """Count .md files in a folder."""
        try:
            return len([f for f in folder.iterdir() 
                       if f.is_file() and f.suffix == '.md'])
        except:
            return 0
    
    def update_dashboard(self) -> None:
        """Update the Dashboard.md with current status."""
        try:
            pending_count = self.count_folder_items(self.needs_action)
            approval_count = self.count_folder_items(self.pending_approval)
            approved_count = self.count_folder_items(self.approved)
            done_today = self._count_done_today()
            
            # Read current dashboard with UTF-8 encoding
            if self.dashboard.exists():
                content = self.dashboard.read_text(encoding='utf-8')
            else:
                content = self._create_dashboard_template()
            
            # Update stats section
            lines = content.split('\n')
            new_lines = []
            in_stats = False
            
            for line in lines:
                if '| Pending Tasks |' in line:
                    new_lines.append(f'| Pending Tasks | {pending_count} | {"⚠️" if pending_count > 0 else "✅"} |')
                    in_stats = True
                elif '| Awaiting Approval |' in line:
                    new_lines.append(f'| Awaiting Approval | {approval_count + approved_count} | {"⚠️" if approval_count + approved_count > 0 else "✅"} |')
                elif '| Completed Today |' in line:
                    new_lines.append(f'| Completed Today | {done_today} | {"📈" if done_today > 0 else "-"} |')
                else:
                    new_lines.append(line)
            
            # Update inbox status section
            content = '\n'.join(new_lines)
            content = content.replace(
                '- **Needs_Action:** 0 items',
                f'- **Needs_Action:** {pending_count} items'
            )
            content = content.replace(
                '- **Pending_Approval:** 0 items',
                f'- **Pending_Approval:** {approval_count} items'
            )
            
            self.dashboard.write_text(content, encoding='utf-8')
            self.logger.info(f'Dashboard updated: {pending_count} pending, {done_today} done today')
            
        except Exception as e:
            self.logger.error(f'Error updating dashboard: {e}')
    
    def _count_done_today(self) -> int:
        """Count files moved to Done today."""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            count = 0
            for f in self.done.iterdir():
                if f.is_file() and f.suffix == '.md':
                    try:
                        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d')
                        if mtime == today:
                            count += 1
                    except:
                        pass
            return count
        except:
            return 0
    
    def _create_dashboard_template(self) -> str:
        """Create a new dashboard template."""
        return f'''---
last_updated: {datetime.now().isoformat()}
status: active
---

# 📊 AI Employee Dashboard

## 🎯 Quick Stats

| Metric | Value | Status |
|--------|-------|--------|
| Pending Tasks | 0 | ✅ |
| Awaiting Approval | 0 | ✅ |
| Completed Today | 0 | - |
| Revenue MTD | $0 | - |

## 📥 Inbox Status

- **Needs_Action:** 0 items
- **Pending_Approval:** 0 items
- **In_Progress:** 0 items

## 📈 Recent Activity

*No recent activity*

## 🚀 Active Projects

| Project | Status | Next Action |
|---------|--------|-------------|
| - | - | - |

## ⚠️ Alerts & Bottlenecks

*No active alerts*

## 📝 Quick Links

- [[Company_Handbook]] - Rules of Engagement
- [[Business_Goals]] - Q1 2026 Objectives
- [Briefings](Briefings/) - CEO Briefings
- [Logs](Logs/) - Activity Logs

---
*Last generated: {datetime.now().strftime("%Y-%m-%d")} | AI Employee v0.1 (Bronze Tier)*
'''
    
    def trigger_qwen(self, mode: str = 'interactive') -> bool:
        """
        Trigger Qwen Code to process pending items.

        Args:
            mode: 'interactive' for user input, 'auto' for automatic processing

        Returns:
            True if Qwen was triggered successfully
        """
        pending = self.get_pending_items()
        approved = self.get_approved_items()

        if not pending and not approved:
            self.logger.info('No items to process')
            return False

        self.logger.info(f'Triggering Qwen Code: {len(pending)} pending, {len(approved)} approved')

        # Build the prompt
        prompt = self._build_prompt(pending, approved)

        # Log the action
        self._log_action('qwen_triggered', {
            'pending_count': len(pending),
            'approved_count': len(approved),
            'mode': mode
        })

        if mode == 'interactive':
            # Interactive mode - let user see and interact
            print("\n" + "="*60)
            print("🤖 AI Employee - Qwen Code Session")
            print("="*60)
            print(f"📁 Vault: {self.vault_path}")
            print(f"📋 Pending items: {len(pending)}")
            print(f"✅ Approved actions: {len(approved)}")
            print("="*60)
            print("\nStarting Qwen Code...\n")
            print("Prompt for Qwen:\n")
            print(prompt)
            print("\n" + "="*60 + "\n")

            try:
                # Change to vault directory and launch qwen interactively
                # User can manually paste the prompt or type their own
                result = subprocess.run(
                    f'cd /d "{self.vault_path}" && qwen',
                    text=True,
                    capture_output=False,
                    shell=True,
                    encoding='utf-8',
                    env={**os.environ, 'PYTHONUTF8': '1'}
                )
                return result.returncode == 0
            except FileNotFoundError:
                self.logger.error('Qwen Code not found. Install Qwen Code CLI.')
                print("\n❌ Qwen Code not found!")
                print("Install Qwen Code CLI first.")
                return False
            except Exception as e:
                self.logger.error(f'Error running Qwen: {e}')
                return False
        else:
            # Auto mode - just log what needs to be done
            self.logger.info(f'Auto mode: Would process {len(pending)} items')
            for item in pending:
                self.logger.info(f'  - {item.name}')
            return True
    
    def _build_prompt(self, pending: List[Path], approved: List[Path]) -> str:
        """Build the prompt for Claude Code."""
        prompt = """# AI Employee Task Processing

You are the AI Employee assistant. Process the items in this vault according to the Company Handbook.

## Current Status

"""
        if pending:
            prompt += f"\n### 📋 Pending Items ({len(pending)})\n\n"
            for item in pending:
                prompt += f"- `{item.name}`\n"
            prompt += "\n**Action:** Read each pending item, determine required actions, and:\n"
            prompt += "1. Create plans in `/Plans/` for multi-step tasks\n"
            prompt += "2. Request approval in `/Pending_Approval/` for sensitive actions\n"
            prompt += "3. Move completed items to `/Done/`\n"
        
        if approved:
            prompt += f"\n### ✅ Approved Actions ({len(approved)})\n\n"
            for item in approved:
                prompt += f"- `{item.name}`\n"
            prompt += "\n**Action:** Execute the approved actions and log results.\n"
        
        prompt += """
## Rules

1. Always read the Company Handbook before acting
2. Log all actions in the Logs folder
3. Update the Dashboard after processing
4. When in doubt, request approval
5. Move completed items to /Done/

Start by reading the Company Handbook and Business Goals, then process the pending items.
"""
        return prompt
    
    def _log_action(self, action_type: str, details: dict) -> None:
        """Log an action to the logs folder."""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action_type': action_type,
                'actor': 'orchestrator',
                **details
            }
            
            log_file = self.logs / f'{datetime.now().strftime("%Y-%m-%d")}.jsonl'
            
            with open(log_file, 'a') as f:
                import json
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            self.logger.error(f'Error logging action: {e}')
    
    def run(self) -> None:
        """
        Main run loop. Continuously monitors and processes items.
        """
        self.logger.info('Starting Orchestrator')
        self.logger.info('Press Ctrl+C to stop')

        import time

        try:
            while True:
                # Update dashboard
                self.update_dashboard()

                # Check for items to process
                pending = self.get_pending_items()
                approved = self.get_approved_items()

                if pending or approved:
                    self.logger.info(f'Found items to process: {len(pending)} pending, {len(approved)} approved')
                    self.trigger_qwen(mode='auto')

                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            self.logger.info('Orchestrator stopped by user')


def main():
    """Main entry point for the orchestrator."""
    parser = argparse.ArgumentParser(
        description='Orchestrate AI Employee workflow'
    )
    parser.add_argument(
        '--vault-path',
        required=True,
        help='Path to the Obsidian vault root'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Check interval in seconds (default: 60)'
    )
    parser.add_argument(
        '--process-once',
        action='store_true',
        help='Process once and exit (don\'t run continuously)'
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Run in interactive mode (launch Qwen Code)'
    )

    args = parser.parse_args()

    orchestrator = Orchestrator(
        vault_path=args.vault_path,
        check_interval=args.interval
    )

    if args.interactive:
        # Interactive mode - launch Qwen immediately
        orchestrator.trigger_qwen(mode='interactive')
    elif args.process_once:
        # Process once and exit
        orchestrator.update_dashboard()
        orchestrator.trigger_qwen(mode='auto')
    else:
        # Continuous mode
        orchestrator.run()


if __name__ == '__main__':
    main()
