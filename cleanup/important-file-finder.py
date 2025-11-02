#!/usr/bin/env python3
"""
Important File Finder
Scans directories for files that may contain important information
and helps you decide what to do with them.
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
import yaml
import re

class ImportantFileFinder:
    def __init__(self, config_path='config.yaml'):
        self.config = self._load_config(config_path)
        self.important_patterns = self.config.get('important_patterns', {})

    def _load_config(self, config_path):
        """Load configuration from YAML file"""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}

    def _matches_pattern(self, filename, pattern):
        """Check if filename matches a pattern (supports wildcards and regex)"""
        # Convert wildcards to regex
        pattern = pattern.replace('.', r'\.')
        pattern = pattern.replace('*', '.*')
        pattern = pattern.replace('?', '.')
        return re.search(pattern, filename, re.IGNORECASE) is not None

    def _check_file_importance(self, file_path):
        """Check if a file matches any important patterns"""
        filename = os.path.basename(file_path)
        matches = []

        for category, patterns in self.important_patterns.items():
            for pattern in patterns:
                if self._matches_pattern(filename, pattern):
                    matches.append(category)
                    break

        return matches

    def _format_file_size(self, size_bytes):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def _get_file_age_days(self, file_path):
        """Get file age in days"""
        mtime = os.path.getmtime(file_path)
        age_seconds = datetime.now().timestamp() - mtime
        return int(age_seconds / 86400)

    def scan_directory(self, directory, recursive=True):
        """Scan directory for important files"""
        important_files = []

        path = Path(directory).expanduser()
        if not path.exists():
            print(f"Error: Directory '{directory}' does not exist")
            return []

        # Get all files
        if recursive:
            files = path.rglob('*')
        else:
            files = path.glob('*')

        for file_path in files:
            if file_path.is_file():
                matches = self._check_file_importance(str(file_path))
                if matches:
                    stat = file_path.stat()
                    important_files.append({
                        'path': str(file_path),
                        'name': file_path.name,
                        'categories': matches,
                        'size': stat.st_size,
                        'age_days': self._get_file_age_days(str(file_path)),
                        'modified': datetime.fromtimestamp(stat.st_mtime)
                    })

        return important_files

    def display_results(self, files):
        """Display found files and prompt for action"""
        if not files:
            print("No important files found.")
            return

        print(f"\n{'='*80}")
        print(f"Found {len(files)} potentially important file(s)")
        print(f"{'='*80}\n")

        for idx, file_info in enumerate(files, 1):
            print(f"\n[{idx}] {file_info['name']}")
            print(f"    Path: {file_info['path']}")
            print(f"    Categories: {', '.join(file_info['categories'])}")
            print(f"    Size: {self._format_file_size(file_info['size'])}")
            print(f"    Age: {file_info['age_days']} days")
            print(f"    Modified: {file_info['modified'].strftime('%Y-%m-%d %H:%M:%S')}")

    def interactive_review(self, files):
        """Interactive review of important files"""
        if not files:
            return

        actions_log = []

        for idx, file_info in enumerate(files, 1):
            print(f"\n{'='*80}")
            print(f"File {idx}/{len(files)}")
            print(f"{'='*80}")
            print(f"Name: {file_info['name']}")
            print(f"Path: {file_info['path']}")
            print(f"Categories: {', '.join(file_info['categories'])}")
            print(f"Size: {self._format_file_size(file_info['size'])}")
            print(f"Age: {file_info['age_days']} days")

            while True:
                print("\nWhat would you like to do?")
                print("  [k] Keep as is")
                print("  [m] Move to a specific location")
                print("  [d] Delete")
                print("  [o] Open file")
                print("  [s] Skip for now")
                print("  [q] Quit")

                choice = input("\nChoice: ").lower().strip()

                if choice == 'k':
                    actions_log.append(f"KEEP: {file_info['path']}")
                    print("Keeping file as is.")
                    break
                elif choice == 'm':
                    dest = input("Enter destination path: ").strip()
                    dest_path = Path(dest).expanduser()
                    if dest_path.exists() and dest_path.is_dir():
                        import shutil
                        new_path = dest_path / file_info['name']
                        shutil.move(file_info['path'], str(new_path))
                        actions_log.append(f"MOVED: {file_info['path']} -> {new_path}")
                        print(f"Moved to {new_path}")
                        break
                    else:
                        print(f"Invalid destination: {dest}")
                elif choice == 'd':
                    confirm = input("Are you sure you want to delete? (yes/no): ").lower()
                    if confirm == 'yes':
                        os.remove(file_info['path'])
                        actions_log.append(f"DELETED: {file_info['path']}")
                        print("File deleted.")
                        break
                    else:
                        print("Delete cancelled.")
                elif choice == 'o':
                    os.system(f"open '{file_info['path']}'")
                    print("File opened.")
                elif choice == 's':
                    actions_log.append(f"SKIPPED: {file_info['path']}")
                    print("Skipping...")
                    break
                elif choice == 'q':
                    print("\nQuitting...")
                    if actions_log:
                        print("\nActions taken:")
                        for action in actions_log:
                            print(f"  {action}")
                    return
                else:
                    print("Invalid choice. Please try again.")

        if actions_log:
            print(f"\n{'='*80}")
            print("Review complete! Actions taken:")
            print(f"{'='*80}")
            for action in actions_log:
                print(f"  {action}")


def main():
    parser = argparse.ArgumentParser(
        description='Find important files in a directory that may need your attention'
    )
    parser.add_argument(
        'directory',
        nargs='?',
        default='~/Downloads',
        help='Directory to scan (default: ~/Downloads)'
    )
    parser.add_argument(
        '--non-recursive',
        action='store_true',
        help='Do not scan subdirectories'
    )
    parser.add_argument(
        '--no-interactive',
        action='store_true',
        help='Just display results without interactive review'
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to config file (default: config.yaml)'
    )

    args = parser.parse_args()

    finder = ImportantFileFinder(config_path=args.config)
    files = finder.scan_directory(args.directory, recursive=not args.non_recursive)

    if args.no_interactive:
        finder.display_results(files)
    else:
        finder.display_results(files)
        if files:
            print("\n" + "="*80)
            proceed = input("\nWould you like to review these files interactively? (y/n): ")
            if proceed.lower() in ['y', 'yes']:
                finder.interactive_review(files)


if __name__ == '__main__':
    main()
