"""
Human-in-the-Loop (HITL) Approval Workflow Module

Manages approval requests for sensitive actions like payments, posts, and communications.
Provides utilities for creating, checking, and processing approval requests.

Usage:
    from hitl_approval import ApprovalManager
    
    manager = ApprovalManager(vault_path)
    
    # Create approval request
    manager.create_approval_request(
        action_type='payment',
        details={'amount': 500, 'recipient': 'Client A'},
        reason='Invoice #1234 payment'
    )
    
    # Check for approved items
    approved = manager.get_approved_items()
"""

import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import logging


@dataclass
class ApprovalRequest:
    """Represents an approval request."""
    request_id: str
    action_type: str
    created: str
    status: str  # pending, approved, rejected, expired
    reason: str
    details: Dict[str, Any]
    expires: str = None
    approved_by: str = None
    approved_at: str = None
    rejection_reason: str = None


class ApprovalManager:
    """
    Manages Human-in-the-Loop approval workflow.
    
    Handles:
    - Creating approval requests
    - Tracking approval status
    - Processing approved items
    - Expiring old requests
    """

    # Action types that require approval
    SENSITIVE_ACTIONS = [
        'payment',
        'email_send',
        'whatsapp_send',
        'linkedin_post',
        'subscription_new',
        'refund',
        'file_delete',
        'contract_sign',
    ]

    # Default approval timeout (24 hours)
    DEFAULT_EXPIRY_HOURS = 24

    def __init__(self, vault_path: str):
        """
        Initialize the approval manager.

        Args:
            vault_path: Path to the Obsidian vault root
        """
        self.vault_path = Path(vault_path)
        
        # Folders
        self.pending_approval = self.vault_path / 'Pending_Approval'
        self.approved = self.vault_path / 'Approved'
        self.rejected = self.vault_path / 'Rejected'
        self.done = self.vault_path / 'Done'
        self.logs = self.vault_path / 'Logs'
        
        # Ensure directories exist
        for folder in [self.pending_approval, self.approved, self.rejected, 
                       self.done, self.logs]:
            folder.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        
        # Track processed requests
        self.processed_requests: set = set()
        
        self.logger.info('ApprovalManager initialized')

    def _setup_logging(self) -> None:
        """Setup logging to file."""
        log_file = self.logs / f'hitl_{datetime.now().strftime("%Y%m%d")}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('ApprovalManager')

    def requires_approval(self, action_type: str) -> bool:
        """
        Check if an action type requires human approval.

        Args:
            action_type: Type of action to check

        Returns:
            True if approval required
        """
        return action_type in self.SENSITIVE_ACTIONS

    def create_approval_request(
        self,
        action_type: str,
        details: Dict[str, Any],
        reason: str,
        title: str = None,
        expiry_hours: int = None
    ) -> Path:
        """
        Create a new approval request file.

        Args:
            action_type: Type of action (payment, email_send, etc.)
            details: Action-specific details
            reason: Reason for the action
            title: Optional title for the request
            expiry_hours: Hours until request expires

        Returns:
            Path to created approval request file
        """
        if not self.requires_approval(action_type):
            self.logger.warning(f'Action {action_type} does not require approval')
            return None

        # Generate request ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        request_id = f"REQ_{action_type.upper()}_{timestamp}"
        
        # Calculate expiry
        expiry_hours = expiry_hours or self.DEFAULT_EXPIRY_HOURS
        expires = (datetime.now() + timedelta(hours=expiry_hours)).isoformat()
        
        # Create filename
        safe_title = (title or reason)[:50].replace(' ', '_').replace('/', '_')
        filename = f"{request_id}_{safe_title}.md"
        
        # Format details for display
        details_text = self._format_details(details, action_type)
        
        # Create approval request content
        content = f'''---
type: approval_request
request_id: "{request_id}"
action_type: {action_type}
created: {datetime.now().isoformat()}
expires: {expires}
status: pending
reason: "{reason}"
---

# Approval Request: {title or action_type.title()}

## Request Details
- **Request ID:** {request_id}
- **Action Type:** {action_type}
- **Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Expires:** {datetime.fromisoformat(expires).strftime('%Y-%m-%d %H:%M:%S')}
- **Status:** ⏳ Pending

## Reason

{reason}

## Details

{details_text}

## Instructions

### To Approve
1. Review the details above carefully
2. Move this file to the `/Approved/` folder
3. The AI Employee will execute the approved action

### To Reject
1. Move this file to the `/Rejected/` folder
2. Add a rejection reason below (optional)

### To Request Changes
1. Edit this file with your feedback
2. Move it back to `/Pending_Approval/` (if not already there)

---
## Processing Log

*AI Employee will log actions here*

---
*Created by ApprovalManager (HITL Workflow) | Request ID: {request_id}*
'''
        
        # Write file
        filepath = self.pending_approval / filename
        filepath.write_text(content, encoding='utf-8')
        
        self.logger.info(f'Created approval request: {filename}')
        self._log_request('created', request_id, action_type)
        
        return filepath

    def _format_details(self, details: Dict[str, Any], action_type: str) -> str:
        """Format details dictionary as readable text."""
        lines = []
        
        if action_type == 'payment':
            lines.append(f"- **Amount:** ${details.get('amount', 'N/A')}")
            lines.append(f"- **Recipient:** {details.get('recipient', 'N/A')}")
            lines.append(f"- **Reference:** {details.get('reference', 'N/A')}")
            if 'invoice_number' in details:
                lines.append(f"- **Invoice:** {details['invoice_number']}")
                
        elif action_type == 'email_send':
            lines.append(f"- **To:** {details.get('to', 'N/A')}")
            lines.append(f"- **Subject:** {details.get('subject', 'N/A')}")
            lines.append(f"- **CC:** {details.get('cc', 'None')}")
            
        elif action_type == 'linkedin_post':
            lines.append(f"- **Content Length:** {details.get('content_length', 'N/A')} characters")
            lines.append(f"- **Hashtags:** {', '.join(details.get('hashtags', []))}")
            if 'schedule' in details:
                lines.append(f"- **Schedule:** {details['schedule']}")
                
        elif action_type == 'whatsapp_send':
            lines.append(f"- **Contact:** {details.get('contact', 'N/A')}")
            lines.append(f"- **Message Preview:** {details.get('message_preview', 'N/A')[:100]}")
            
        elif action_type == 'subscription_new':
            lines.append(f"- **Service:** {details.get('service', 'N/A')}")
            lines.append(f"- **Cost:** ${details.get('cost', 'N/A')}/month")
            lines.append(f"- **Reason:** {details.get('justification', 'N/A')}")
            
        else:
            # Generic formatting
            for key, value in details.items():
                lines.append(f"- **{key.replace('_', ' ').title()}:** {value}")
        
        return '\n'.join(lines) if lines else '- *No additional details*'

    def get_pending_requests(self) -> List[Path]:
        """
        Get all pending approval requests.

        Returns:
            List of pending request file paths
        """
        try:
            requests = [
                f for f in self.pending_approval.iterdir()
                if f.is_file() and f.suffix == '.md'
                and f.name not in self.processed_requests
            ]
            return sorted(requests, key=lambda f: f.stat().st_mtime)
        except Exception as e:
            self.logger.error(f'Error getting pending requests: {e}')
            return []

    def get_approved_items(self) -> List[Path]:
        """
        Get all approved items ready for execution.

        Returns:
            List of approved file paths
        """
        try:
            items = [
                f for f in self.approved.iterdir()
                if f.is_file() and f.suffix == '.md'
            ]
            return sorted(items, key=lambda f: f.stat().st_mtime)
        except Exception as e:
            self.logger.error(f'Error getting approved items: {e}')
            return []

    def approve_request(self, request_file: Path, approved_by: str = "Human") -> bool:
        """
        Move a request from Pending to Approved.

        Args:
            request_file: Path to the request file
            approved_by: Name of approver

        Returns:
            True if successful
        """
        try:
            if not request_file.exists():
                self.logger.error(f'Request file not found: {request_file}')
                return False
            
            if request_file.parent != self.pending_approval:
                self.logger.error(f'File not in Pending_Approval: {request_file}')
                return False
            
            # Read and update frontmatter
            content = request_file.read_text(encoding='utf-8')
            content = content.replace(
                'status: pending',
                f'status: approved\napproved_by: "{approved_by}"\napproved_at: "{datetime.now().isoformat()}"'
            )
            content = content.replace(
                'Status:** ⏳ Pending',
                'Status:** ✅ Approved'
            )
            
            # Move to approved folder
            dest = self.approved / request_file.name
            shutil.move(str(request_file), str(dest))
            dest.write_text(content, encoding='utf-8')
            
            # Extract request ID for logging
            request_id = request_file.stem
            
            self.logger.info(f'Approved request: {request_id}')
            self._log_request('approved', request_id, approved_by=approved_by)
            
            return True
            
        except Exception as e:
            self.logger.error(f'Error approving request: {e}')
            return False

    def reject_request(self, request_file: Path, reason: str = "") -> bool:
        """
        Move a request from Pending to Rejected.

        Args:
            request_file: Path to the request file
            reason: Reason for rejection

        Returns:
            True if successful
        """
        try:
            if not request_file.exists():
                self.logger.error(f'Request file not found: {request_file}')
                return False
            
            # Read and update content
            content = request_file.read_text(encoding='utf-8')
            content = content.replace(
                'status: pending',
                f'status: rejected\nrejection_reason: "{reason}"\nrejected_at: "{datetime.now().isoformat()}"'
            )
            content = content.replace(
                'Status:** ⏳ Pending',
                'Status:** ❌ Rejected'
            )
            
            # Add rejection reason to file
            if '## Processing Log' in content:
                content = content.replace(
                    '## Processing Log',
                    f'## Rejection\n\n**Reason:** {reason}\n\n## Processing Log'
                )
            
            # Move to rejected folder
            dest = self.rejected / request_file.name
            shutil.move(str(request_file), str(dest))
            dest.write_text(content, encoding='utf-8')
            
            self.logger.info(f'Rejected request: {request_file.stem}')
            self._log_request('rejected', request_file.stem, reason=reason)
            
            return True
            
        except Exception as e:
            self.logger.error(f'Error rejecting request: {e}')
            return False

    def execute_approved_action(self, approved_file: Path) -> bool:
        """
        Execute an approved action and move to Done.

        Args:
            approved_file: Path to approved file

        Returns:
            True if successful
        """
        try:
            # Read the file to determine action type
            content = approved_file.read_text(encoding='utf-8')
            
            # Extract action type from frontmatter
            action_type = self._extract_frontmatter_value(content, 'action_type')
            request_id = self._extract_frontmatter_value(content, 'request_id')
            
            if not action_type:
                self.logger.error(f'Could not determine action type from {approved_file}')
                return False
            
            self.logger.info(f'Executing approved action: {action_type} ({request_id})')
            
            # Execute based on action type
            success = self._execute_action(action_type, approved_file, content)
            
            if success:
                # Move to Done
                dest = self.done / approved_file.name
                shutil.move(str(approved_file), str(dest))
                
                # Update status in file
                dest_content = dest.read_text(encoding='utf-8')
                dest_content = dest_content.replace(
                    'status: approved',
                    'status: completed\ncompleted_at: "' + datetime.now().isoformat() + '"'
                )
                dest.write_text(dest_content, encoding='utf-8')
                
                self.logger.info(f'Completed action: {request_id}')
                self._log_request('completed', request_id)
                
                return True
            else:
                self.logger.error(f'Failed to execute action: {action_type}')
                return False
                
        except Exception as e:
            self.logger.error(f'Error executing approved action: {e}')
            return False

    def _execute_action(self, action_type: str, file_path: Path, content: str) -> bool:
        """
        Execute the actual action based on type.
        
        This is a placeholder - actual execution would use MCP servers.
        """
        # In a full implementation, this would call the appropriate MCP server
        # For now, we just log what would happen
        
        self.logger.info(f'Would execute {action_type} via MCP server')
        
        # Add execution log to file
        return True

    def _extract_frontmatter_value(self, content: str, key: str) -> Optional[str]:
        """Extract a value from YAML frontmatter."""
        import re
        match = re.search(rf'{key}:\s*"?([^"\n]+)"?', content)
        return match.group(1) if match else None

    def _log_request(self, action: str, request_id: str, **kwargs) -> None:
        """Log a request action."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'request_id': request_id,
            **kwargs
        }
        
        log_file = self.logs / f'hitl_{datetime.now().strftime("%Y-%m-%d")}.jsonl'
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

    def cleanup_expired_requests(self) -> int:
        """
        Move expired requests to Rejected.

        Returns:
            Number of requests expired
        """
        expired_count = 0
        now = datetime.now()
        
        for request_file in self.get_pending_requests():
            try:
                content = request_file.read_text(encoding='utf-8')
                expires_str = self._extract_frontmatter_value(content, 'expires')
                
                if expires_str:
                    expires = datetime.fromisoformat(expires_str)
                    if now > expires:
                        self.reject_request(
                            request_file, 
                            reason='Request expired (no response within timeout)'
                        )
                        expired_count += 1
                        
            except Exception as e:
                self.logger.error(f'Error checking expiry for {request_file}: {e}')
        
        return expired_count

    def get_status_summary(self) -> Dict[str, Any]:
        """
        Get summary of approval status.

        Returns:
            Dictionary with status counts
        """
        return {
            'pending': len(self.get_pending_requests()),
            'approved': len(self.get_approved_items()),
            'rejected': len(list(self.rejected.glob('*.md'))),
            'done': len(list(self.done.glob('*.md'))),
        }


def main():
    """Test the approval manager."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python hitl_approval.py <vault_path>")
        sys.exit(1)
    
    vault_path = sys.argv[1]
    manager = ApprovalManager(vault_path)
    
    print("Approval Manager Status:")
    print(json.dumps(manager.get_status_summary(), indent=2))


if __name__ == '__main__':
    main()
