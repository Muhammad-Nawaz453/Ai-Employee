"""
File System Watcher

Monitors a drop folder for new files and creates action files in the vault.
This is the simplest watcher to set up - just drop files into the monitored folder.

Usage:
    python filesystem_watcher.py --vault-path /path/to/vault --watch-folder /path/to/drops
"""

import argparse
import shutil
from pathlib import Path
from typing import List, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

from base_watcher import BaseWatcher


class DropFolderHandler(FileSystemEventHandler):
    """Handles file system events for the drop folder."""
    
    def __init__(self, watcher: 'FileSystemWatcher'):
        self.watcher = watcher
        self.logger = watcher.logger
    
    def on_created(self, event):
        """Called when a file or directory is created."""
        if event.is_directory:
            return
        
        self.logger.info(f'New file detected: {event.src_path}')
        self.watcher.process_new_file(Path(event.src_path))


class FileSystemWatcher(BaseWatcher):
    """
    Watches a folder for new files and creates action files in the vault.
    
    Files dropped into the watch folder are copied to Needs_Action/
    with accompanying metadata .md files.
    """
    
    def __init__(self, vault_path: str, watch_folder: str, check_interval: int = 5):
        """
        Initialize the file system watcher.
        
        Args:
            vault_path: Path to the Obsidian vault root
            watch_folder: Path to the folder to monitor for new files
            check_interval: Seconds between checks (default: 5 for file watcher)
        """
        super().__init__(vault_path, check_interval)
        
        self.watch_folder = Path(watch_folder)
        self.watch_folder.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f'Watch folder: {self.watch_folder}')
        
        # Track processed files
        self.processed_files: set = set()
    
    def check_for_updates(self) -> List[Path]:
        """
        Check for new files in the watch folder.
        
        Returns:
            List of new file paths to process
        """
        new_files = []
        
        try:
            for file_path in self.watch_folder.iterdir():
                if file_path.is_file() and file_path not in self.processed_files:
                    # Skip hidden files and temp files
                    if file_path.name.startswith('.') or file_path.suffix == '.tmp':
                        continue
                    
                    new_files.append(file_path)
                    self.processed_files.add(file_path)
        except Exception as e:
            self.logger.error(f'Error scanning watch folder: {e}')
        
        return new_files
    
    def process_new_file(self, source: Path) -> None:
        """
        Process a newly detected file.
        
        Args:
            source: Path to the new file
        """
        try:
            # Copy file to Needs_Action
            dest = self.needs_action / f'FILE_{source.name}'
            shutil.copy2(source, dest)
            
            # Create metadata file
            self.create_action_file(source)
            
            self.logger.info(f'Processed file: {source.name}')
            
        except Exception as e:
            self.logger.error(f'Error processing file {source}: {e}')
    
    def create_action_file(self, source: Path) -> Optional[Path]:
        """
        Create a metadata .md file for the dropped file.
        
        Args:
            source: Path to the original file
            
        Returns:
            Path to created metadata file
        """
        try:
            file_size = source.stat().st_size
            file_modified = source.stat().st_mtime
            
            content = f'''{self.generate_frontmatter(
                item_type='file_drop',
                original_name=f'"{source.name}"',
                file_size=file_size,
                source_folder=f'"{self.watch_folder}"'
            )}

# File Drop for Processing

## File Details
- **Original Name:** {source.name}
- **Size:** {self._format_size(file_size)}
- **Dropped:** {self._format_timestamp(file_modified)}
- **Source:** {self.watch_folder}

## Content Preview

*File copied to: `Needs_Action/FILE_{source.name}`*

## Suggested Actions

- [ ] Review file content
- [ ] Process according to type
- [ ] Move to appropriate folder
- [ ] Archive or delete after processing

## Notes

*Add any notes about this file below*

---
*Created by FileSystemWatcher*
'''
            
            # Create metadata file
            meta_path = self.needs_action / f'FILE_{source.stem}.meta.md'
            meta_path.write_text(content)
            
            self.logger.info(f'Created metadata file: {meta_path.name}')
            return meta_path
            
        except Exception as e:
            self.logger.error(f'Error creating action file: {e}')
            return None
    
    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.1f} {unit}'
            size /= 1024
        return f'{size:.1f} TB'
    
    def _format_timestamp(self, timestamp: float) -> str:
        """Format Unix timestamp as ISO datetime."""
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).isoformat()
    
    def run(self) -> None:
        """
        Run the file system watcher using watchdog observer.
        
        This overrides the base class to use event-driven watching
        instead of polling.
        """
        self.logger.info(f'Starting {self.__class__.__name__}')
        self.logger.info(f'Watching: {self.watch_folder}')
        self.logger.info('Press Ctrl+C to stop')
        
        event_handler = DropFolderHandler(self)
        observer = Observer()
        observer.schedule(event_handler, str(self.watch_folder), recursive=False)
        observer.start()
        
        try:
            while True:
                # Check for any files that might have been missed
                items = self.check_for_updates()
                for item in items:
                    self.create_action_file(item)
                    self.logger.info(f'Created action file: {item.name}')
                
                import time
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            self.logger.info(f'{self.__class__.__name__} stopped by user')
            observer.stop()
        
        observer.join()


def main():
    """Main entry point for the filesystem watcher."""
    parser = argparse.ArgumentParser(
        description='Watch a folder for new files and create action files in the vault'
    )
    parser.add_argument(
        '--vault-path',
        required=True,
        help='Path to the Obsidian vault root'
    )
    parser.add_argument(
        '--watch-folder',
        required=True,
        help='Path to the folder to monitor for new files'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=5,
        help='Check interval in seconds (default: 5)'
    )
    
    args = parser.parse_args()
    
    watcher = FileSystemWatcher(
        vault_path=args.vault_path,
        watch_folder=args.watch_folder,
        check_interval=args.interval
    )
    
    watcher.run()


if __name__ == '__main__':
    main()
