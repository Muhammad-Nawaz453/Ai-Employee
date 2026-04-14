"""
Facebook & Instagram Watcher

Monitors Facebook and Instagram for:
- New messages and comments
- Page mentions and tags
- Important notifications
- Keyword-based triggers

Creates action files in Needs_Action/ folder for Claude Code to process.
"""

import time
import logging
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from base_watcher import BaseWatcher


class FacebookInstagramWatcher(BaseWatcher):
    """
    Watcher for Facebook and Instagram business accounts.
    Monitors for messages, comments, mentions, and keyword triggers.
    """
    
    def __init__(
        self,
        vault_path: str,
        facebook_access_token: str = "",
        facebook_page_id: str = "",
        instagram_account_id: str = "",
        check_interval: int = 300,  # 5 minutes
        keywords: Optional[List[str]] = None,
    ):
        super().__init__(vault_path, check_interval)
        self.facebook_access_token = facebook_access_token
        self.facebook_page_id = facebook_page_id
        self.instagram_account_id = instagram_account_id
        self.keywords = keywords or ["urgent", "help", "question", "invoice", "payment", "pricing"]
        self.processed_ids: set = set()
        self.last_check_time = datetime.now()
        
        # Load processed IDs from cache if exists
        self._load_processed_cache()
    
    def _load_processed_cache(self):
        """Load previously processed IDs to avoid duplicates"""
        cache_file = Path(self.vault_path) / "Logs" / "fb_ig_processed.json"
        if cache_file.exists():
            try:
                import json
                with open(cache_file, "r") as f:
                    data = json.load(f)
                    self.processed_ids = set(data.get("processed_ids", []))
            except Exception as e:
                self.logger.warning(f"Could not load processed cache: {e}")
    
    def _save_processed_cache(self):
        """Save processed IDs to prevent re-processing on restart"""
        cache_file = Path(self.vault_path) / "Logs" / "fb_ig_processed.json"
        try:
            import json
            # Keep only last 1000 IDs to prevent file bloat
            processed_list = list(self.processed_ids)[-1000:]
            with open(cache_file, "w") as f:
                json.dump({"processed_ids": processed_list}, f)
        except Exception as e:
            self.logger.warning(f"Could not save processed cache: {e}")
    
    def check_for_updates(self) -> List[Dict]:
        """
        Check Facebook and Instagram for new items.
        Returns list of items to process.
        """
        items = []
        
        # Check Facebook messages and comments
        if self.facebook_page_id and self.facebook_access_token:
            try:
                fb_items = self._check_facebook()
                items.extend(fb_items)
            except Exception as e:
                self.logger.error(f"Error checking Facebook: {e}")
        
        # Check Instagram messages and comments
        if self.instagram_account_id and self.facebook_access_token:
            try:
                ig_items = self._check_instagram()
                items.extend(ig_items)
            except Exception as e:
                self.logger.error(f"Error checking Instagram: {e}")
        
        return items
    
    def _check_facebook(self) -> List[Dict]:
        """Check Facebook page for new conversations and mentions"""
        items = []
        
        try:
            # Get recent page posts and comments
            posts_url = f"https://graph.facebook.com/v18.0/{self.facebook_page_id}/feed"
            params = {
                "fields": "id,message,created_time,comments.summary(false),from",
                "access_token": self.facebook_access_token,
                "since": self.last_check_time.isoformat(),
                "limit": 25,
            }
            
            response = requests.get(posts_url, params=params, timeout=30)
            response.raise_for_status()
            
            posts = response.json().get("data", [])
            
            for post in posts:
                post_id = post.get("id", "")
                
                if post_id in self.processed_ids:
                    continue
                
                # Check if post contains keywords
                message = post.get("message", "") or ""
                if self._contains_keywords(message):
                    items.append({
                        "platform": "facebook",
                        "type": "post",
                        "id": post_id,
                        "message": message,
                        "from": post.get("from", {}).get("name", "Unknown"),
                        "created_time": post.get("created_time", ""),
                        "priority": "high" if self._is_urgent(message) else "normal",
                    })
                    self.processed_ids.add(post_id)
                
                # Check for new comments on posts
                comments = post.get("comments", {}).get("data", [])
                for comment in comments:
                    comment_id = comment.get("id", "")
                    if comment_id in self.processed_ids:
                        continue
                    
                    comment_message = comment.get("message", "")
                    if self._contains_keywords(comment_message):
                        items.append({
                            "platform": "facebook",
                            "type": "comment",
                            "id": comment_id,
                            "post_id": post_id,
                            "message": comment_message,
                            "from": comment.get("from", {}).get("name", "Unknown"),
                            "created_time": comment.get("created_time", ""),
                            "priority": "high" if self._is_urgent(comment_message) else "normal",
                        })
                        self.processed_ids.add(comment_id)
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Facebook API error: {e}")
        
        return items
    
    def _check_instagram(self) -> List[Dict]:
        """Check Instagram business account for new interactions"""
        items = []
        
        try:
            # Get recent media and comments
            media_url = f"https://graph.facebook.com/v18.0/{self.instagram_account_id}/media"
            params = {
                "fields": "id,caption,media_type,timestamp,comments.summary(false)",
                "access_token": self.facebook_access_token,
                "since": self.last_check_time.isoformat(),
                "limit": 25,
            }
            
            response = requests.get(media_url, params=params, timeout=30)
            response.raise_for_status()
            
            media_items = response.json().get("data", [])
            
            for media in media_items:
                media_id = media.get("id", "")
                
                if media_id in self.processed_ids:
                    continue
                
                # Check caption for keywords
                caption = media.get("caption", "") or ""
                if self._contains_keywords(caption):
                    items.append({
                        "platform": "instagram",
                        "type": "media",
                        "id": media_id,
                        "caption": caption,
                        "media_type": media.get("media_type", ""),
                        "created_time": media.get("timestamp", ""),
                        "priority": "normal",
                    })
                    self.processed_ids.add(media_id)
            
            # Get Instagram messages (if available)
            messages_url = f"https://graph.facebook.com/v18.0/{self.instagram_account_id}/conversations"
            params = {
                "fields": "id,updated_time,messages.limit(5){message,from,created_time}",
                "access_token": self.facebook_access_token,
                "updated_time": f">={int(self.last_check_time.timestamp())}",
            }
            
            try:
                response = requests.get(messages_url, params=params, timeout=30)
                if response.status_code == 200:
                    conversations = response.json().get("data", [])
                    
                    for conv in conversations:
                        messages = conv.get("messages", {}).get("data", [])
                        for msg in messages:
                            msg_id = msg.get("id", "")
                            if msg_id in self.processed_ids:
                                continue
                            
                            message_text = msg.get("message", "")
                            if self._contains_keywords(message_text):
                                items.append({
                                    "platform": "instagram",
                                    "type": "message",
                                    "id": msg_id,
                                    "message": message_text,
                                    "from": msg.get("from", {}).get("name", "Unknown"),
                                    "created_time": msg.get("created_time", ""),
                                    "priority": "high" if self._is_urgent(message_text) else "normal",
                                })
                                self.processed_ids.add(msg_id)
            except Exception as e:
                self.logger.warning(f"Instagram messages check failed: {e}")
        
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Instagram API error: {e}")
        
        return items
    
    def _contains_keywords(self, text: str) -> bool:
        """Check if text contains any monitored keywords"""
        if not text:
            return False
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in self.keywords)
    
    def _is_urgent(self, text: str) -> bool:
        """Check if text indicates urgency"""
        urgent_keywords = ["urgent", "asap", "emergency", "immediately", "critical"]
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in urgent_keywords)
    
    def create_action_file(self, item: Dict) -> Path:
        """Create action file in Needs_Action folder"""
        platform = item.get("platform", "unknown")
        item_type = item.get("type", "unknown")
        item_id = item.get("id", "unknown")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Sanitize filename
        safe_id = item_id.replace("/", "_").replace("\\", "_")[:50]
        filename = f"{platform.upper()}_{item_type.upper()}_{safe_id}_{timestamp}.md"
        
        filepath = self.needs_action / filename
        
        # Build content based on item type
        content = f"""---
type: social_media
platform: {platform}
item_type: {item_type}
item_id: {item_id}
received: {datetime.now().isoformat()}
priority: {item.get('priority', 'normal')}
status: pending
---

# {platform.title()} {item_type.replace('_', ' ').title()}

## Details
- **Platform:** {platform.title()}
- **Type:** {item_type.replace('_', ' ').title()}
- **Item ID:** {item_id}
- **Received:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Content
"""
        
        if item_type == "post":
            content += f"""
{item.get('message', '')}

**From:** {item.get('from', 'Unknown')}
"""
        elif item_type == "comment":
            content += f"""
{item.get('message', '')}

**From:** {item.get('from', 'Unknown')}
**Post ID:** {item.get('post_id', 'N/A')}
"""
        elif item_type == "message":
            content += f"""
{item.get('message', '')}

**From:** {item.get('from', 'Unknown')}
"""
        elif item_type == "media":
            content += f"""
{item.get('caption', '')}

**Media Type:** {item.get('media_type', 'Unknown')}
"""
        
        content += f"""
## Suggested Actions
- [ ] Review content
- [ ] Respond if needed
- [ ] Archive after processing
"""
        
        filepath.write_text(content, encoding="utf-8")
        self.logger.info(f"Created action file: {filepath.name}")
        
        # Save cache periodically
        if len(self.processed_ids) % 50 == 0:
            self._save_processed_cache()
        
        return filepath
    
    def run(self):
        """Run the watcher loop"""
        self.logger.info(f"Starting {self.__class__.__name__}")
        self.logger.info(f"Monitoring keywords: {self.keywords}")
        
        while True:
            try:
                items = self.check_for_updates()
                
                if items:
                    self.logger.info(f"Found {len(items)} new items to process")
                    for item in items:
                        self.create_action_file(item)
                else:
                    self.logger.debug("No new items found")
                
                self.last_check_time = datetime.now()
                
            except Exception as e:
                self.logger.error(f"Error in watcher loop: {e}")
            
            time.sleep(self.check_interval)


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    vault_path = os.getenv("VAULT_PATH", "./AI_Employee_Vault")
    facebook_token = os.getenv("FACEBOOK_ACCESS_TOKEN", "")
    facebook_page_id = os.getenv("FACEBOOK_PAGE_ID", "")
    instagram_account_id = os.getenv("INSTAGRAM_ACCOUNT_ID", "")
    
    if not facebook_token:
        print("Warning: FACEBOOK_ACCESS_TOKEN not set. Watcher will run but won't connect to APIs.")
        print("Set the environment variable or create a .env file with your credentials.")
    
    watcher = FacebookInstagramWatcher(
        vault_path=vault_path,
        facebook_access_token=facebook_token,
        facebook_page_id=facebook_page_id,
        instagram_account_id=instagram_account_id,
        check_interval=60,  # Check every minute for testing
    )
    
    try:
        watcher.run()
    except KeyboardInterrupt:
        print("\nWatcher stopped by user")
