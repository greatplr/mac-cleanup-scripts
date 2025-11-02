#!/usr/bin/env python3
"""
Folder Cleanup Script
Automatically organizes files in common folders like Downloads and Desktop
based on age, type, and importance.
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import yaml
import shutil
import re

class FolderCleanup:
    def __init__(self, config_path='config.yaml'):
        self.config = self._load_config(config_path)
        self.cleanup_rules = self.config.get('cleanup_rules', {})
        self.file_categories = self.config.get('file_categories', {})
        self.important_patterns = self.config.get('important_patterns', {})
        self.safe_directories = self.config.get('safe_cleanup_directories', [])
        self.dry_run = False

    def _load_config(self, config_path):
        """Load configuration from YAML file"""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}

    def _matches_pattern(self, filename, pattern):
        """Check if filename matches a pattern"""
        pattern = pattern.replace('.', r'\.')
        pattern = pattern.replace('*', '.*')
        pattern = pattern.replace('?', '.')
        return re.search(pattern, filename, re.IGNORECASE) is not None

    def _is_important_file(self, file_path):
        """Check if file is marked as important"""
        filename = os.path.basename(file_path)
        for category, patterns in self.important_patterns.items():
            for pattern in patterns:
                if self._matches_pattern(filename, pattern):
                    return True, category
        return False, None

    def _get_file_category(self, file_path):
        """Determine file category based on extension"""
        ext = Path(file_path).suffix.lower()

        for category, extensions in self.file_categories.items():
            if ext in extensions:
                return category

        return 'other'

    def _get_file_age_days(self, file_path):
        """Get file age in days"""
        mtime = os.path.getmtime(file_path)
        age_seconds = datetime.now().timestamp() - mtime
        return int(age_seconds / 86400)

    def _execute_action(self, action, file_path, target_dir=None):
        """Execute cleanup action"""
        if self.dry_run:
            if action == 'delete':
                print(f"  [DRY RUN] Would delete: {file_path}")
            elif action == 'move' and target_dir:
                print(f"  [DRY RUN] Would move: {file_path} -> {target_dir}")
            elif action == 'archive':
                print(f"  [DRY RUN] Would archive: {file_path}")
            return True

        try:
            if action == 'delete':
                os.remove(file_path)
                print(f"  Deleted: {file_path}")
                return True
            elif action == 'move' and target_dir:
                Path(target_dir).mkdir(parents=True, exist_ok=True)
                dest = Path(target_dir) / Path(file_path).name
                # Handle name conflicts
                counter = 1
                while dest.exists():
                    stem = Path(file_path).stem
                    ext = Path(file_path).suffix
                    dest = Path(target_dir) / f"{stem}_{counter}{ext}"
                    counter += 1
                shutil.move(file_path, str(dest))
                print(f"  Moved: {file_path} -> {dest}")
                return True
            elif action == 'archive':
                archive_dir = Path(file_path).parent / '_archive'
                return self._execute_action('move', file_path, str(archive_dir))
        except Exception as e:
            print(f"  Error: {e}")
            return False

    def _is_safe_directory(self, directory, allow_any=False):
        """Check if directory is in the safe list"""
        if allow_any:
            return True

        path = Path(directory).expanduser().resolve()

        # Check against safe directories list
        for safe_dir in self.safe_directories:
            safe_path = Path(safe_dir).expanduser().resolve()
            if path == safe_path:
                return True

        return False

    def cleanup_directory(self, directory, dry_run=False, allow_any_directory=False):
        """Clean up a directory based on rules"""
        self.dry_run = dry_run
        path = Path(directory).expanduser()

        if not path.exists():
            print(f"Error: Directory '{directory}' does not exist")
            return

        # Safety check - only allow whitelisted directories
        if not self._is_safe_directory(directory, allow_any=allow_any_directory):
            print(f"\n{'='*80}")
            print(f"🛑 SAFETY ERROR: Directory not in safe cleanup list")
            print(f"{'='*80}")
            print(f"Directory: {path}")
            print(f"\nFor safety, cleanup is only allowed in these directories:")
            for safe_dir in self.safe_directories:
                print(f"  - {safe_dir}")
            print(f"\nTo add this directory to the safe list, edit config.yaml")
            print(f"Or use --allow-any-directory flag to override (use with caution!)")
            print(f"{'='*80}\n")
            return

        print(f"\n{'='*80}")
        print(f"Cleaning up: {path}")
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        print(f"{'='*80}\n")

        stats = {
            'scanned': 0,
            'deleted': 0,
            'moved': 0,
            'archived': 0,
            'skipped': 0,
            'important_flagged': 0
        }

        # Get all files in directory (non-recursive for safety)
        for item in path.iterdir():
            if not item.is_file():
                continue

            stats['scanned'] += 1
            file_path = str(item)

            # Check if file is important - skip if it is
            is_important, importance_category = self._is_important_file(file_path)
            if is_important:
                print(f"⚠️  IMPORTANT ({importance_category}): {item.name}")
                stats['important_flagged'] += 1
                stats['skipped'] += 1
                continue

            # Get file properties
            age_days = self._get_file_age_days(file_path)
            category = self._get_file_category(file_path)

            # Apply cleanup rules
            rule_applied = False

            # Check category-specific rules
            if category in self.cleanup_rules.get('by_category', {}):
                cat_rules = self.cleanup_rules['by_category'][category]

                # Skip if category has no rules (None/null in YAML)
                if cat_rules is None:
                    continue

                if 'delete_after_days' in cat_rules:
                    if age_days > cat_rules['delete_after_days']:
                        print(f"🗑️  {item.name} (age: {age_days} days, category: {category})")
                        if self._execute_action('delete', file_path):
                            stats['deleted'] += 1
                        rule_applied = True
                        continue

                if 'archive_after_days' in cat_rules:
                    if age_days > cat_rules['archive_after_days']:
                        print(f"📦 {item.name} (age: {age_days} days, category: {category})")
                        if self._execute_action('archive', file_path):
                            stats['archived'] += 1
                        rule_applied = True
                        continue

                if 'organize_to' in cat_rules:
                    organize_dir = Path(cat_rules['organize_to']).expanduser()
                    print(f"📁 {item.name} (category: {category})")
                    if self._execute_action('move', file_path, str(organize_dir)):
                        stats['moved'] += 1
                    rule_applied = True
                    continue

            # Check general age-based rules
            age_rules = self.cleanup_rules.get('by_age', [])
            for rule in age_rules:
                if age_days > rule.get('days', 0):
                    action = rule.get('action')
                    if action == 'delete':
                        print(f"🗑️  {item.name} (age: {age_days} days)")
                        if self._execute_action('delete', file_path):
                            stats['deleted'] += 1
                        rule_applied = True
                        break
                    elif action == 'archive':
                        print(f"📦 {item.name} (age: {age_days} days)")
                        if self._execute_action('archive', file_path):
                            stats['archived'] += 1
                        rule_applied = True
                        break

            if not rule_applied:
                stats['skipped'] += 1

        # Print summary
        print(f"\n{'='*80}")
        print("Cleanup Summary")
        print(f"{'='*80}")
        print(f"Files scanned:    {stats['scanned']}")
        print(f"Files deleted:    {stats['deleted']}")
        print(f"Files moved:      {stats['moved']}")
        print(f"Files archived:   {stats['archived']}")
        print(f"Important files:  {stats['important_flagged']}")
        print(f"Files skipped:    {stats['skipped']}")
        print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Clean up and organize folders automatically'
    )
    parser.add_argument(
        'directories',
        nargs='*',
        default=['~/Downloads', '~/Desktop'],
        help='Directories to clean (default: ~/Downloads ~/Desktop)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to config file (default: config.yaml)'
    )
    parser.add_argument(
        '--allow-any-directory',
        action='store_true',
        help='⚠️  DANGER: Allow cleanup in any directory (bypasses safety whitelist)'
    )

    args = parser.parse_args()

    cleaner = FolderCleanup(config_path=args.config)

    for directory in args.directories:
        cleaner.cleanup_directory(
            directory,
            dry_run=args.dry_run,
            allow_any_directory=args.allow_any_directory
        )


if __name__ == '__main__':
    main()
