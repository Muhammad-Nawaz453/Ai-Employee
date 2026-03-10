"""
WhatsApp Watcher

Monitors WhatsApp Web for messages containing keywords using Playwright.
Creates action files in the vault for messages that require attention.

Note: This uses WhatsApp Web automation. Be aware of WhatsApp's terms of service.
For production use, consider the official WhatsApp Business API.

Setup Requirements:
1. Install playwright: pip install playwright
2. Install browsers: playwright install
3. First run will require QR code scan to authenticate

Usage:
    python whatsapp_watcher.py --vault-path /path/to/vault --session /path/to/session
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeout

from base_watcher import BaseWatcher


class WhatsAppWatcher(BaseWatcher):
    """
    Watches WhatsApp Web for new messages containing keywords.
    
    Monitors for:
    - Messages containing urgent keywords
    - Messages from specific contacts
    - Unread messages in starred chats
    """

    def __init__(
        self, 
        vault_path: str, 
        session_path: str,
        check_interval: int = 60,
        headless: bool = True
    ):
        """
        Initialize the WhatsApp watcher.

        Args:
            vault_path: Path to the Obsidian vault root
            session_path: Path to store browser session data
            check_interval: Seconds between checks (default: 60)
            headless: Run browser in headless mode (default: True)
        """
        super().__init__(vault_path, check_interval)
        
        self.session_path = Path(session_path)
        self.session_path.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        
        # Keywords that indicate urgency or importance
        self.keywords = [
            'urgent', 'asap', 'emergency', 'help', 'invoice', 'payment', 
            'deadline', 'important', 'call me', 'meeting', 'tomorrow'
        ]
        
        # Track last message timestamps per chat
        self.last_message_times: Dict[str, datetime] = {}
        
        self.logger.info(f'WhatsApp Watcher initialized')
        self.logger.info(f'Session path: {self.session_path}')
        self.logger.info(f'Keywords: {self.keywords}')

    def check_for_updates(self) -> List[Dict[str, Any]]:
        """
        Check WhatsApp Web for new important messages.

        Returns:
            List of message data dictionaries
        """
        messages = []
        
        try:
            with sync_playwright() as p:
                # Launch browser with persistent context
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(self.session_path),
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-dev-shm-usage'
                    ]
                )
                
                page = browser.pages[0] if browser.pages else browser.new_page()
                
                # Navigate to WhatsApp Web
                try:
                    page.goto('https://web.whatsapp.com', timeout=60000)
                    
                    # Wait for chat list to load
                    try:
                        page.wait_for_selector('[data-testid="chat-list"]', timeout=30000)
                        self.logger.info('WhatsApp Web loaded successfully')
                    except PlaywrightTimeout:
                        self.logger.warning('WhatsApp Web not loaded - QR scan may be required')
                        # Save screenshot for debugging
                        screenshot_path = self.vault_path / 'Logs' / 'whatsapp_qr.png'
                        page.screenshot(path=str(screenshot_path))
                        self.logger.info(f'QR code screenshot saved to: {screenshot_path}')
                        browser.close()
                        return messages
                    
                    # Small delay for content to load
                    time.sleep(3)
                    
                    # Find all chat items with unread messages
                    messages = self._extract_messages(page)
                    
                except Exception as e:
                    self.logger.error(f'Error loading WhatsApp Web: {e}')
                
                browser.close()
                
        except Exception as e:
            self.logger.error(f'Error in WhatsApp watcher: {e}', exc_info=True)
        
        return messages

    def _extract_messages(self, page: Page) -> List[Dict[str, Any]]:
        """Extract messages from WhatsApp Web page."""
        messages = []
        
        try:
            # JavaScript to extract chat data
            extract_script = """
            () => {
                const chats = [];
                const chatList = document.querySelector('[data-testid="chat-list"]');
                if (!chatList) return chats;
                
                const chatItems = chatList.querySelectorAll('[role="row"]');
                chatItems.forEach(item => {
                    try {
                        const nameElement = item.querySelector('[dir="auto"]');
                        const messageElement = item.querySelector('[dir="auto"]:last-child');
                        const unreadElement = item.querySelector('[data-testid="unread-msg-count"]');
                        
                        if (nameElement && messageElement) {
                            chats.push({
                                name: nameElement.textContent.trim(),
                                lastMessage: messageElement.textContent.trim(),
                                isUnread: !!unreadElement,
                                unreadCount: unreadElement ? parseInt(unreadElement.textContent) : 0
                            });
                        }
                    } catch (e) {
                        console.error('Error extracting chat:', e);
                    }
                });
                
                return chats;
            }
            """
            
            chats = page.evaluate(extract_script)
            self.logger.info(f'Found {len(chats)} chats')
            
            # Process each chat
            for chat in chats:
                if self._is_important(chat):
                    message_data = {
                        'chat_name': chat['name'],
                        'last_message': chat['last_message'],
                        'is_unread': chat['isUnread'],
                        'unread_count': chat['unreadCount'],
                        'timestamp': datetime.now(),
                        'matched_keywords': self._get_matched_keywords(chat['last_message'])
                    }
                    
                    # Check if we've seen this message before
                    chat_key = f"{chat['name']}:{chat['last_message']}"
                    if chat_key not in self.processed_ids:
                        messages.append(message_data)
                        self.processed_ids.add(chat_key)
                        self.logger.info(f'Important message from {chat["name"]}: {chat["last_message"][:50]}')
            
        except Exception as e:
            self.logger.error(f'Error extracting messages: {e}')
        
        return messages

    def _is_important(self, chat: Dict) -> bool:
        """Determine if a chat contains important messages."""
        # Unread messages are always important
        if chat.get('isUnread', False):
            return True
        
        # Check for keywords in last message
        message_lower = chat.get('lastMessage', '').lower()
        for keyword in self.keywords:
            if keyword in message_lower:
                return True
        
        return False

    def _get_matched_keywords(self, message: str) -> List[str]:
        """Get list of keywords that matched in the message."""
        message_lower = message.lower()
        return [kw for kw in self.keywords if kw in message_lower]

    def create_action_file(self, message: Dict[str, Any]) -> Optional[Path]:
        """
        Create a Markdown action file for the WhatsApp message.

        Args:
            message: Message data dictionary

        Returns:
            Path to created file
        """
        try:
            # Sanitize chat name for filename
            safe_name = self.sanitize_filename(message['chat_name'])
            timestamp = message['timestamp'].strftime('%Y%m%d_%H%M%S')
            filename = f"WHATSAPP_{timestamp}_{safe_name[:30]}.md"
            
            # Determine priority
            priority = 'high' if message['is_unread'] else 'normal'
            if message['matched_keywords']:
                priority = 'high'
            
            # Generate suggested actions
            suggested_actions = self._generate_suggested_actions(message)
            
            content = f'''{self.generate_frontmatter(
                item_type='whatsapp_message',
                chat_name=f'"{message["chat_name"]}"',
                received=message['timestamp'].isoformat(),
                priority=f'"{priority}"',
                is_unread=str(message['is_unread']),
                unread_count=str(message['unread_count']),
                keywords=f'{message["matched_keywords"]}'
            )}

# WhatsApp Message from {message['chat_name']}

## Message Details
- **Contact:** {message['chat_name']}
- **Received:** {message['timestamp'].isoformat()}
- **Priority:** {priority.upper()}
- **Unread:** {'Yes' if message['is_unread'] else 'No'} ({message['unread_count']} messages)
- **Matched Keywords:** {', '.join(message['matched_keywords']) if message['matched_keywords'] else 'None'}

## Last Message

> {message['last_message']}

## Suggested Actions

{suggested_actions}

## Response Draft

*Draft your WhatsApp response below*

---

## Processing Notes

- [ ] Message reviewed
- [ ] Response drafted (if needed)
- [ ] Follow-up required: Yes / No
- [ ] Moved to Done

---
*Created by WhatsAppWatcher | Chat: {message['chat_name']}*
'''
            
            filepath = self.needs_action / filename
            filepath.write_text(content, encoding='utf-8')
            
            self.logger.info(f'Created action file for WhatsApp message from {message["chat_name"]}')
            return filepath
            
        except Exception as e:
            self.logger.error(f'Error creating action file: {e}')
            return None

    def _generate_suggested_actions(self, message: Dict) -> str:
        """Generate suggested actions based on message content."""
        actions = []
        message_lower = (message.get('last_message', '') or '').lower()
        keywords = message.get('matched_keywords', [])
        
        # Urgent keywords
        if 'urgent' in keywords or 'asap' in keywords or 'emergency' in keywords:
            actions.append('- [ ] **Respond immediately** - High priority message')
            actions.append('- [ ] Consider calling if time-sensitive')
        
        # Payment/invoice related
        if 'invoice' in keywords or 'payment' in keywords:
            actions.append('- [ ] Review payment/invoice request')
            actions.append('- [ ] Create approval request if amount > $500')
            actions.append('- [ ] Forward to accounting if needed')
        
        # Meeting related
        if 'meeting' in keywords or 'call me' in keywords:
            actions.append('- [ ] Check calendar availability')
            actions.append('- [ ] Respond with available times')
        
        # Help request
        if 'help' in keywords:
            actions.append('- [ ] Assess what help is needed')
            actions.append('- [ ] Provide assistance or delegate')
        
        # Default actions
        if not actions:
            actions.append('- [ ] Review message')
            actions.append('- [ ] Draft response if needed')
        
        actions.append('- [ ] Mark as processed')
        
        return '\n'.join(actions)


def main():
    """Main entry point for the WhatsApp watcher."""
    parser = argparse.ArgumentParser(
        description='Watch WhatsApp Web for important messages and create action files'
    )
    parser.add_argument(
        '--vault-path',
        required=True,
        help='Path to the Obsidian vault root'
    )
    parser.add_argument(
        '--session',
        required=True,
        help='Path to store browser session data'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Check interval in seconds (default: 60)'
    )
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Run browser with visible UI (useful for QR code scanning)'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("WhatsApp Watcher - Silver Tier")
    print("=" * 60)
    print(f"Vault: {args.vault_path}")
    print(f"Session: {args.session}")
    print(f"Check interval: {args.interval}s")
    print("=" * 60)
    print()
    print("First run will require QR code scan:")
    print("1. Open WhatsApp on your phone")
    print("2. Go to Settings > Linked Devices")
    print("3. Scan the QR code that appears")
    print()
    print("Tip: Run with --no-headless first to see QR code, then use headless mode")
    print("Press Ctrl+C to stop")
    print()

    watcher = WhatsAppWatcher(
        vault_path=args.vault_path,
        session_path=args.session,
        check_interval=args.interval,
        headless=not args.no_headless
    )

    watcher.run()


if __name__ == '__main__':
    main()
