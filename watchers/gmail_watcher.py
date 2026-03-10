"""
Gmail Watcher

Monitors Gmail for unread and important emails, creating action files in the vault.
Uses Gmail API to fetch emails and creates Markdown files for Claude Code to process.

Setup Requirements:
1. Enable Gmail API in Google Cloud Console
2. Create OAuth 2.0 credentials
3. Download credentials.json
4. First run will open browser for authentication

Usage:
    python gmail_watcher.py --vault-path /path/to/vault --credentials /path/to/credentials.json
"""

import argparse
import base64
import os
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from base_watcher import BaseWatcher


# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 
          'https://www.googleapis.com/auth/gmail.labels']


class GmailWatcher(BaseWatcher):
    """
    Watches Gmail for new important emails and creates action files.
    
    Monitors for:
    - Unread emails
    - Starred emails
    - Emails with important labels
    - Emails from VIP contacts
    """

    def __init__(
        self, 
        vault_path: str, 
        credentials_path: str,
        token_path: str = None,
        check_interval: int = 120
    ):
        """
        Initialize the Gmail watcher.

        Args:
            vault_path: Path to the Obsidian vault root
            credentials_path: Path to Gmail API credentials.json
            token_path: Path to store token.json (default: ~/.gmail_token.json)
            check_interval: Seconds between checks (default: 120)
        """
        super().__init__(vault_path, check_interval)
        
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path) if token_path else Path.home() / '.gmail_token.json'
        
        # Keywords that indicate urgency
        self.urgent_keywords = ['urgent', 'asap', 'emergency', 'important', 'deadline', 'invoice', 'payment']
        
        # VIP senders (can be configured)
        self.vip_senders = []
        
        # Gmail service
        self.service = None
        
        # Load configuration
        self._load_config()
        
        # Authenticate
        self._authenticate()
        
        self.logger.info(f'Gmail Watcher initialized')
        self.logger.info(f'Credentials: {self.credentials_path}')
        self.logger.info(f'Token: {self.token_path}')

    def _load_config(self) -> None:
        """Load configuration from environment or config file."""
        # Load VIP senders from environment
        vip_env = os.environ.get('GMAIL_VIP_SENDERS', '')
        if vip_env:
            self.vip_senders = [s.strip() for s in vip_env.split(',')]
        
        self.logger.info(f'VIP senders: {self.vip_senders}')

    def _authenticate(self) -> None:
        """Authenticate with Gmail API."""
        creds = None
        
        # Load existing token
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f'Gmail credentials not found at {self.credentials_path}\n'
                        'Please download credentials.json from Google Cloud Console.'
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save token
            self.token_path.write_text(creds.to_json())
            self.logger.info('Gmail credentials saved')
        
        # Build service
        self.service = build('gmail', 'v1', credentials=creds)
        self.logger.info('Authenticated with Gmail API')

    def _get_label_id(self, label_name: str) -> Optional[str]:
        """Get Gmail label ID by name."""
        try:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            for label in labels:
                if label['name'] == label_name:
                    return label['id']
        except Exception as e:
            self.logger.error(f'Error getting label {label_name}: {e}')
        return None

    def check_for_updates(self) -> List[Dict[str, Any]]:
        """
        Check for new important emails.

        Returns:
            List of email data dictionaries
        """
        emails = []
        
        try:
            # Search for unread emails
            query = 'is:unread'
            
            # Also search for starred emails (even if read)
            starred_query = 'is:starred'
            
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=20
            ).execute()
            
            messages = results.get('messages', [])
            
            # Also get starred
            starred_results = self.service.users().messages().list(
                userId='me',
                q=starred_query,
                maxResults=10
            ).execute()
            
            starred_messages = starred_results.get('messages', [])
            
            # Combine and deduplicate
            all_message_ids = set()
            for msg in messages + starred_messages:
                all_message_ids.add(msg['id'])
            
            for msg_id in all_message_ids:
                if msg_id not in self.processed_ids:
                    email_data = self._fetch_email(msg_id)
                    if email_data:
                        emails.append(email_data)
                        self.processed_ids.add(msg_id)
            
        except Exception as e:
            self.logger.error(f'Error checking Gmail: {e}', exc_info=True)
        
        return emails

    def _fetch_email(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full email data by ID."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = message['payload']['headers']
            header_dict = {}
            for h in headers:
                header_dict[h['name']] = h['value']
            
            # Extract body
            body = self._extract_body(message['payload'])
            
            # Determine priority
            priority = self._determine_priority(header_dict, body)
            
            # Get labels
            label_ids = message.get('labelIds', [])
            labels = self._get_label_names(label_ids)
            
            return {
                'id': message_id,
                'thread_id': message['threadId'],
                'from': header_dict.get('From', 'Unknown'),
                'to': header_dict.get('To', ''),
                'subject': header_dict.get('Subject', 'No Subject'),
                'date': header_dict.get('Date', ''),
                'body': body,
                'labels': labels,
                'priority': priority,
                'snippet': message['payload'].get('snippet', '')
            }
            
        except Exception as e:
            self.logger.error(f'Error fetching email {message_id}: {e}')
            return None

    def _extract_body(self, payload: Dict) -> str:
        """Extract plain text body from email payload."""
        body = ""
        
        if 'parts' in payload:
            # Multipart email - find plain text or HTML
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                        break
                    elif part['parts']:
                        body = self._extract_body(part)
                        if body:
                            break
                elif part['mimeType'] == 'text/html' and not body:
                    data = part['body'].get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
        elif 'body' in payload:
            data = payload['body'].get('data', '')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
        
        # Truncate long bodies
        if len(body) > 5000:
            body = body[:5000] + '... [truncated]'
        
        return body

    def _determine_priority(self, headers: Dict, body: str) -> str:
        """Determine email priority based on content."""
        body_lower = (body or '').lower()
        subject_lower = (headers.get('Subject', '')).lower()
        from_email = (headers.get('From', '')).lower()
        
        # Check for urgent keywords
        for keyword in self.urgent_keywords:
            if keyword in subject_lower or keyword in body_lower:
                return 'high'
        
        # Check VIP senders
        for vip in self.vip_senders:
            if vip.lower() in from_email:
                return 'high'
        
        # Check if starred
        if 'STARRED' in headers.get('X-Gmail-Labels', ''):
            return 'high'
        
        return 'normal'

    def _get_label_names(self, label_ids: List[str]) -> List[str]:
        """Convert label IDs to names."""
        # Common label mappings
        label_map = {
            'INBOX': 'Inbox',
            'STARRED': 'Starred',
            'IMPORTANT': 'Important',
            'UNREAD': 'Unread',
            'SENT': 'Sent',
            'DRAFT': 'Draft',
            'SPAM': 'Spam',
            'TRASH': 'Trash',
        }
        
        names = []
        for label_id in label_ids:
            names.append(label_map.get(label_id, label_id))
        
        return names

    def create_action_file(self, email: Dict[str, Any]) -> Optional[Path]:
        """
        Create a Markdown action file for the email.

        Args:
            email: Email data dictionary

        Returns:
            Path to created file
        """
        try:
            # Sanitize subject for filename
            safe_subject = self.sanitize_filename(email['subject'])
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"EMAIL_{timestamp}_{safe_subject[:50]}.md"
            
            # Parse date
            try:
                parsed_date = parsedate_to_datetime(email['date'])
                date_str = parsed_date.isoformat()
            except:
                date_str = datetime.now().isoformat()
            
            # Generate suggested actions based on content
            suggested_actions = self._generate_suggested_actions(email)
            
            content = f'''{self.generate_frontmatter(
                item_type='email',
                email_id=f'"{email["id"]}"',
                thread_id=f'"{email["thread_id"]}"',
                from_email=f'"{email["from"]}"',
                subject=f'"{email["subject"]}"',
                received=date_str,
                priority=f'"{email["priority"]}"',
                labels=f'{email["labels"]}'
            )}

# Email: {email['subject']}

## Email Details
- **From:** {email['from']}
- **To:** {email['to']}
- **Date:** {date_str}
- **Priority:** {email['priority'].upper()}
- **Labels:** {', '.join(email['labels'])}

## Email Content

{email['body'] if email['body'] else email['snippet']}

## Suggested Actions

{suggested_actions}

## Response Draft

*Draft your response below*

---

## Processing Notes

- [ ] Email read and understood
- [ ] Response drafted (if needed)
- [ ] Follow-up required: Yes / No
- [ ] Moved to Done

---
*Created by GmailWatcher | Email ID: {email['id']}*
'''
            
            filepath = self.needs_action / filename
            filepath.write_text(content, encoding='utf-8')
            
            self.logger.info(f'Created action file for email: {email["subject"][:50]}')
            return filepath
            
        except Exception as e:
            self.logger.error(f'Error creating action file: {e}')
            return None

    def _generate_suggested_actions(self, email: Dict) -> str:
        """Generate suggested actions based on email content."""
        actions = []
        body_lower = (email.get('body', '') or '').lower()
        subject_lower = (email.get('subject', '') or '').lower()
        
        # Check for questions
        if '?' in (email.get('subject', '') + email.get('body', '')):
            actions.append('- [ ] Reply to sender with answer')
        
        # Check for invoice/payment mentions
        if 'invoice' in body_lower or 'payment' in body_lower:
            actions.append('- [ ] Review invoice/payment request')
            actions.append('- [ ] Create approval request if amount > $500')
        
        # Check for meeting requests
        if 'meeting' in body_lower or 'call' in body_lower or 'schedule' in body_lower:
            actions.append('- [ ] Check calendar availability')
            actions.append('- [ ] Respond with available times')
        
        # Check for attachments (would need to check separately)
        actions.append('- [ ] Check for attachments')
        
        # Default actions
        actions.append('- [ ] Archive after processing')
        
        return '\n'.join(actions) if actions else '- [ ] Review and respond as needed'


def main():
    """Main entry point for the Gmail watcher."""
    parser = argparse.ArgumentParser(
        description='Watch Gmail for important emails and create action files'
    )
    parser.add_argument(
        '--vault-path',
        required=True,
        help='Path to the Obsidian vault root'
    )
    parser.add_argument(
        '--credentials',
        required=True,
        help='Path to Gmail API credentials.json'
    )
    parser.add_argument(
        '--token',
        default=None,
        help='Path to store token.json (default: ~/.gmail_token.json)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=120,
        help='Check interval in seconds (default: 120)'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Gmail Watcher - Silver Tier")
    print("=" * 60)
    print(f"Vault: {args.vault_path}")
    print(f"Credentials: {args.credentials}")
    print(f"Check interval: {args.interval}s")
    print("=" * 60)
    print()
    print("First run will open browser for Gmail authentication.")
    print("Press Ctrl+C to stop")
    print()

    watcher = GmailWatcher(
        vault_path=args.vault_path,
        credentials_path=args.credentials,
        token_path=args.token,
        check_interval=args.interval
    )

    watcher.run()


if __name__ == '__main__':
    main()
