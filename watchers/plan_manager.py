"""
Plan Manager Module

Creates and manages Plan.md files for multi-step tasks.
Plans break down complex tasks into actionable checkboxes.

Usage:
    from plan_manager import PlanManager
    
    manager = PlanManager(vault_path)
    
    # Create a plan
    plan_path = manager.create_plan(
        title="Process Client Invoice",
        task_id="TASK_001",
        steps=[
            "Review invoice details",
            "Create approval request",
            "Wait for approval",
            "Process payment",
            "Archive invoice"
        ]
    )
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging


@dataclass
class PlanStep:
    """Represents a step in a plan."""
    id: str
    description: str
    status: str  # pending, in_progress, completed, skipped
    completed_at: str = None
    notes: str = None


class PlanManager:
    """
    Manages Plan.md files for multi-step tasks.
    
    Features:
    - Create structured plans with checkboxes
    - Track step completion
    - Generate progress reports
    - Archive completed plans
    """

    def __init__(self, vault_path: str):
        """
        Initialize the plan manager.

        Args:
            vault_path: Path to the Obsidian vault root
        """
        self.vault_path = Path(vault_path)
        self.plans_folder = self.vault_path / 'Plans'
        self.done_folder = self.vault_path / 'Done' / 'Plans'
        self.logs = self.vault_path / 'Logs'
        
        # Ensure directories exist
        self.plans_folder.mkdir(parents=True, exist_ok=True)
        self.done_folder.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        
        self.logger.info('PlanManager initialized')

    def _setup_logging(self) -> None:
        """Setup logging to file."""
        log_file = self.logs / f'plan_{datetime.now().strftime("%Y%m%d")}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('PlanManager')

    def create_plan(
        self,
        title: str,
        steps: List[str],
        task_id: str = None,
        source_file: str = None,
        priority: str = 'normal',
        estimated_duration: str = None,
        dependencies: List[str] = None
    ) -> Path:
        """
        Create a new Plan.md file.

        Args:
            title: Plan title
            steps: List of step descriptions
            task_id: Unique task identifier
            source_file: Original file that triggered this plan
            priority: Plan priority (low, normal, high, urgent)
            estimated_duration: Estimated time to complete
            dependencies: List of dependent task IDs

        Returns:
            Path to created plan file
        """
        # Generate task ID if not provided
        if not task_id:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            task_id = f"TASK_{timestamp}"
        
        # Create filename
        safe_title = title.replace(' ', '_').replace('/', '_')[:50]
        filename = f"PLAN_{task_id}_{safe_title}.md"
        
        # Generate step checkboxes
        steps_content = ""
        for i, step in enumerate(steps, 1):
            step_id = f"step_{i}"
            steps_content += f"- [ ] **{i}. {step}** `[{step_id}]`\n"
        
        # Build plan content
        content = f'''---
type: plan
task_id: "{task_id}"
title: "{title}"
created: {datetime.now().isoformat()}
status: active
priority: "{priority}"
source: "{source_file or 'manual'}"
estimated_duration: "{estimated_duration or 'not estimated'}"
progress: 0%
---

# Plan: {title}

## Task Information
- **Task ID:** {task_id}
- **Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Priority:** {priority.upper()}
- **Status:** 🔄 Active
- **Source:** {source_file or 'Manual creation'}
- **Estimated Duration:** {estimated_duration or 'Not estimated'}

## Progress

| Total Steps | Completed | Remaining | Progress |
|-------------|-----------|-----------|----------|
| {len(steps)} | 0 | {len(steps)} | 0% |

## Steps

{steps_content}

## Dependencies

{self._format_dependencies(dependencies) if dependencies else '- None'}

## Notes

*Add any notes or observations below*

---

## Execution Log

| Timestamp | Step | Action | Result |
|-----------|------|--------|--------|
| - | - | - | - |

---

## Completion Summary

*To be filled when plan is complete*

- **Started:** -
- **Completed:** -
- **Total Time:** -
- **Issues Encountered:** -

---
*Created by PlanManager (Silver Tier) | Task ID: {task_id}*
'''
        
        # Write file
        filepath = self.plans_folder / filename
        filepath.write_text(content, encoding='utf-8')
        
        self.logger.info(f'Created plan: {filename} ({len(steps)} steps)')
        self._log_plan('created', task_id, title, len(steps))
        
        return filepath

    def update_step_status(
        self,
        plan_file: Path,
        step_id: str,
        status: str,
        notes: str = None
    ) -> bool:
        """
        Update the status of a step in a plan.

        Args:
            plan_file: Path to the plan file
            step_id: ID of the step to update
            status: New status (pending, in_progress, completed, skipped)
            notes: Optional notes

        Returns:
            True if successful
        """
        try:
            if not plan_file.exists():
                self.logger.error(f'Plan file not found: {plan_file}')
                return False
            
            content = plan_file.read_text(encoding='utf-8')
            
            # Find and update the step
            lines = content.split('\n')
            step_found = False
            
            for i, line in enumerate(lines):
                if f'[{step_id}]' in line:
                    if status == 'completed':
                        lines[i] = line.replace('[ ]', '[x]')
                        # Add completion timestamp
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        if notes:
                            lines[i] += f' ✅ _Completed: {timestamp}_ - {notes}'
                        else:
                            lines[i] += f' ✅ _Completed: {timestamp}_'
                    elif status == 'in_progress':
                        lines[i] = line.replace('[ ]', '[>]')
                        if notes:
                            lines[i] += f' 🔄 _In Progress_ - {notes}'
                    step_found = True
                    break
            
            if not step_found:
                self.logger.warning(f'Step {step_id} not found in plan')
                return False
            
            # Update progress percentage
            content = '\n'.join(lines)
            content = self._update_progress(content)
            
            plan_file.write_text(content, encoding='utf-8')
            
            self.logger.info(f'Updated step {step_id} to {status}')
            return True
            
        except Exception as e:
            self.logger.error(f'Error updating step: {e}')
            return False

    def _update_progress(self, content: str) -> str:
        """Update progress statistics in plan content."""
        lines = content.split('\n')
        
        total_steps = 0
        completed_steps = 0
        
        for line in lines:
            if '[x]' in line or '[X]' in line:
                completed_steps += 1
                total_steps += 1
            elif '[ ]' in line or '[>]' in line:
                total_steps += 1
        
        if total_steps > 0:
            progress = int((completed_steps / total_steps) * 100)
            
            # Update progress in frontmatter
            for i, line in enumerate(lines):
                if line.startswith('progress:'):
                    lines[i] = f'progress: {progress}%'
                    break
            
            # Update progress table
            remaining = total_steps - completed_steps
            for i, line in enumerate(lines):
                if '| Total Steps |' in line:
                    lines[i+1] = f'| {total_steps} | {completed_steps} | {remaining} | {progress}% |'
                    break
            
            # Update status if complete
            if progress == 100:
                content = '\n'.join(lines)
                content = content.replace('status: active', 'status: completed')
                content = content.replace('Status:** 🔄 Active', 'Status:** ✅ Completed')
                return content
        
        return '\n'.join(lines)

    def complete_plan(self, plan_file: Path, summary: str = None) -> bool:
        """
        Mark a plan as complete and move to Done folder.

        Args:
            plan_file: Path to the plan file
            summary: Completion summary

        Returns:
            True if successful
        """
        try:
            if not plan_file.exists():
                self.logger.error(f'Plan file not found: {plan_file}')
                return False
            
            content = plan_file.read_text(encoding='utf-8')
            
            # Update status
            content = content.replace('status: active', 'status: completed')
            content = content.replace('Status:** 🔄 Active', 'Status:** ✅ Completed')
            
            # Add completion timestamp
            completed_at = datetime.now().isoformat()
            content = content.replace(
                '*To be filled when plan is complete*',
                f'**Completed:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n{summary or "Plan completed successfully."}'
            )
            
            # Move to Done folder
            dest = self.done_folder / plan_file.name
            dest.write_text(content, encoding='utf-8')
            plan_file.unlink()
            
            # Extract task ID for logging
            task_id = plan_file.stem
            
            self.logger.info(f'Completed plan: {task_id}')
            self._log_plan('completed', task_id, summary=summary)
            
            return True
            
        except Exception as e:
            self.logger.error(f'Error completing plan: {e}')
            return False

    def get_active_plans(self) -> List[Path]:
        """
        Get all active plans.

        Returns:
            List of active plan file paths
        """
        plans = []
        try:
            for f in self.plans_folder.iterdir():
                if f.is_file() and f.suffix == '.md':
                    content = f.read_text(encoding='utf-8')
                    if 'status: active' in content:
                        plans.append(f)
        except Exception as e:
            self.logger.error(f'Error getting active plans: {e}')
        
        return sorted(plans, key=lambda f: f.stat().st_mtime)

    def get_plan_by_task_id(self, task_id: str) -> Optional[Path]:
        """
        Find a plan by its task ID.

        Args:
            task_id: Task ID to search for

        Returns:
            Path to plan file or None
        """
        try:
            for f in self.plans_folder.iterdir():
                if f.is_file() and f.suffix == '.md':
                    content = f.read_text(encoding='utf-8')
                    if f'task_id: "{task_id}"' in content:
                        return f
        except Exception as e:
            self.logger.error(f'Error searching for plan: {e}')
        
        return None

    def _format_dependencies(self, dependencies: List[str]) -> str:
        """Format dependencies list."""
        if not dependencies:
            return '- None'
        return '\n'.join(f'- {dep}' for dep in dependencies)

    def _log_plan(self, action: str, task_id: str, title: str = None, steps: int = 0, summary: str = None) -> None:
        """Log a plan action."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'task_id': task_id,
            'title': title,
            'steps': steps,
            'summary': summary
        }
        
        log_file = self.logs / f'plan_{datetime.now().strftime("%Y-%m-%d")}.jsonl'
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

    def get_status_summary(self) -> Dict[str, Any]:
        """
        Get summary of plan status.

        Returns:
            Dictionary with status counts
        """
        active = len(self.get_active_plans())
        done = len(list(self.done_folder.glob('*.md')))
        
        return {
            'active': active,
            'completed': done,
            'total': active + done,
        }


def main():
    """Test the plan manager."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python plan_manager.py <vault_path>")
        sys.exit(1)
    
    vault_path = sys.argv[1]
    manager = PlanManager(vault_path)
    
    print("Plan Manager Status:")
    print(json.dumps(manager.get_status_summary(), indent=2))


if __name__ == '__main__':
    main()
