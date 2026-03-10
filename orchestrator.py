"""
Orchestrator

Main coordination script for the AI Employee system.
Triggers Qwen Code to process items in Needs_Action folder.
Includes Ralph Wiggum Loop for autonomous task completion.

Usage:
    python orchestrator.py --vault-path /path/to/vault
    python orchestrator.py --vault-path /path/to/vault --process-all
    python orchestrator.py --vault-path /path/to/vault --ralph-loop "Process all pending items"
"""

import argparse
import subprocess
import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

# Import Silver tier modules
from watchers.hitl_approval import ApprovalManager
from watchers.plan_manager import PlanManager


class RalphWiggumLoop:
    """
    Ralph Wiggum Loop - Keeps Claude Code working until tasks are complete.
    
    This implements the Stop hook pattern where:
    1. Orchestrator creates state file with prompt
    2. Claude works on task
    3. Claude tries to exit
    4. Stop hook checks: Is task file in /Done?
    5. If NO → Block exit, re-inject prompt (loop continues)
    6. Repeat until complete or max iterations
    
    Reference: https://github.com/anthropics/claude-code/tree/main/.claude/plugins/ralph-wiggum
    """

    def __init__(self, vault_path: str, max_iterations: int = 10):
        """
        Initialize the Ralph Wiggum Loop.

        Args:
            vault_path: Path to the Obsidian vault root
            max_iterations: Maximum loop iterations before forcing exit
        """
        self.vault_path = Path(vault_path)
        self.max_iterations = max_iterations
        self.current_iteration = 0
        
        # Folders
        self.needs_action = self.vault_path / 'Needs_Action'
        self.done = self.vault_path / 'Done'
        self.plans = self.vault_path / 'Plans'
        self.state_file = self.vault_path / 'Logs' / 'ralph_state.json'
        
        # Ensure directories exist
        (self.vault_path / 'Logs').mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = logging.getLogger('RalphWiggumLoop')
        
        # Load state
        self._load_state()

    def _load_state(self) -> None:
        """Load loop state from file."""
        if self.state_file.exists():
            try:
                state = json.loads(self.state_file.read_text())
                self.current_iteration = state.get('iteration', 0)
                self.task_prompt = state.get('prompt', '')
                self.start_time = state.get('start_time')
            except:
                self.current_iteration = 0
                self.task_prompt = ''
                self.start_time = None

    def _save_state(self) -> None:
        """Save loop state to file."""
        state = {
            'iteration': self.current_iteration,
            'prompt': self.task_prompt,
            'start_time': self.start_time,
            'last_check': datetime.now().isoformat()
        }
        self.state_file.write_text(json.dumps(state, indent=2))

    def start(self, prompt: str) -> bool:
        """
        Start a new Ralph loop.

        Args:
            prompt: Task prompt for Claude

        Returns:
            True if started successfully
        """
        self.current_iteration = 0
        self.task_prompt = prompt
        self.start_time = datetime.now().isoformat()
        self._save_state()
        
        self.logger.info(f'Ralph loop started: "{prompt[:50]}..."')
        return True

    def should_continue(self) -> bool:
        """
        Check if the loop should continue.

        Returns:
            True if Claude should keep working
        """
        # Check max iterations
        if self.current_iteration >= self.max_iterations:
            self.logger.warning(f'Max iterations ({self.max_iterations}) reached')
            return False
        
        # Check if there are still pending items
        pending_count = len([f for f in self.needs_action.iterdir() 
                            if f.is_file() and f.suffix == '.md'])
        
        if pending_count > 0:
            self.logger.info(f'Continuing: {pending_count} items still pending')
            return True
        
        # Check for active plans
        plans_folder = self.vault_path / 'Plans'
        if plans_folder.exists():
            active_plans = len([f for f in plans_folder.iterdir() 
                               if f.is_file() and f.suffix == '.md'
                               and 'status: active' in f.read_text()])
            if active_plans > 0:
                self.logger.info(f'Continuing: {active_plans} active plans')
                return True
        
        # All done
        self.logger.info('All tasks complete - loop ending')
        return False

    def increment(self) -> int:
        """Increment iteration counter and return new value."""
        self.current_iteration += 1
        self._save_state()
        return self.current_iteration

    def get_status(self) -> Dict[str, Any]:
        """Get current loop status."""
        return {
            'iteration': self.current_iteration,
            'max_iterations': self.max_iterations,
            'prompt': self.task_prompt,
            'start_time': self.start_time,
            'should_continue': self.should_continue()
        }

    def end(self) -> None:
        """End the loop and clean up state."""
        self.state_file.unlink(missing_ok=True)
        self.logger.info('Ralph loop ended')


class Orchestrator:
    """
    Orchestrates the AI Employee workflow.

    - Monitors Needs_Action folder for items to process
    - Triggers Qwen Code to analyze and act on items
    - Updates Dashboard.md with status
    - Manages HITL approvals and Plans (Silver Tier)
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

        # Initialize Silver tier managers
        self.approval_manager = ApprovalManager(vault_path)
        self.plan_manager = PlanManager(vault_path)
        self.ralph_loop = RalphWiggumLoop(vault_path)

        # Setup logging
        self._setup_logging()

        self.logger.info(f'Orchestrator initialized (Silver Tier)')
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

    def ralph_loop_run(self, prompt: str = None) -> None:
        """
        Run the Ralph Wiggum Loop for autonomous task completion.
        
        This keeps Claude Code working until all tasks are complete or
        max iterations is reached.
        
        Args:
            prompt: Optional custom prompt (uses default if not provided)
        """
        self.logger.info('Starting Ralph Wiggum Loop')
        self.logger.info('This will keep Claude working until tasks are complete')
        
        # Default prompt if not provided
        if not prompt:
            prompt = """# Autonomous Task Processing

Process all pending items in the vault:

1. Read all files in /Needs_Action/
2. Create plans in /Plans/ for multi-step tasks
3. Create approval requests in /Pending_Approval/ for sensitive actions
4. Execute approved actions from /Approved/
5. Move completed items to /Done/
6. Update the Dashboard

Follow the Company Handbook rules. Log all actions.
"""
        
        # Start the Ralph loop
        self.ralph_loop.start(prompt)
        
        try:
            while self.ralph_loop.should_continue():
                iteration = self.ralph_loop.increment()
                self.logger.info(f'=== Ralph Loop Iteration {iteration}/{self.ralph_loop.max_iterations} ===')
                
                # Update dashboard
                self.update_dashboard()
                
                # Build and display prompt
                pending = self.get_pending_items()
                approved = self.get_approved_items()
                active_plans = self.plan_manager.get_active_plans()
                
                print("\n" + "="*60)
                print(f"🔄 Ralph Loop - Iteration {iteration}/{self.ralph_loop.max_iterations}")
                print("="*60)
                print(f"📋 Pending items: {len(pending)}")
                print(f"✅ Approved actions: {len(approved)}")
                print(f"📝 Active plans: {len(active_plans)}")
                print("="*60)
                
                # Launch Claude Code
                try:
                    # Change to vault directory and launch qwen
                    result = subprocess.run(
                        f'cd /d "{self.vault_path}" && qwen --prompt "{prompt.replace(chr(10), " ").replace(chr(34), chr(39))}"',
                        text=True,
                        capture_output=False,
                        shell=True,
                        encoding='utf-8',
                        env={**os.environ, 'PYTHONUTF8': '1'}
                    )
                    
                    if result.returncode != 0:
                        self.logger.warning(f'Qwen exited with code {result.returncode}')
                    
                except Exception as e:
                    self.logger.error(f'Error running Qwen: {e}')
                
                # Small delay before next iteration
                time.sleep(2)
                
        except KeyboardInterrupt:
            self.logger.info('Ralph loop stopped by user')
        
        # Cleanup
        self.ralph_loop.end()
        self.update_dashboard()
        self.logger.info('Ralph loop finished')
    
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
        description='Orchestrate AI Employee workflow (Silver Tier)'
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
    parser.add_argument(
        '--ralph-loop',
        nargs='?',
        const=True,
        metavar='PROMPT',
        help='Run Ralph Wiggum Loop for autonomous completion (optional custom prompt)'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show current status and exit'
    )

    args = parser.parse_args()

    orchestrator = Orchestrator(
        vault_path=args.vault_path,
        check_interval=args.interval
    )

    if args.status:
        # Show status
        print("\n" + "="*60)
        print("AI Employee Status (Silver Tier)")
        print("="*60)
        print(f"Vault: {args.vault_path}")
        print(f"Pending items: {len(orchestrator.get_pending_items())}")
        print(f"Approved items: {len(orchestrator.get_approved_items())}")
        print(f"Active plans: {len(orchestrator.plan_manager.get_active_plans())}")
        print(f"Pending approvals: {len(orchestrator.approval_manager.get_pending_requests())}")
        print("="*60 + "\n")
        return

    if args.ralph_loop:
        # Ralph Wiggum Loop mode
        prompt = args.ralph_loop if args.ralph_loop is not True else None
        orchestrator.ralph_loop_run(prompt=prompt)
    elif args.interactive:
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
