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
import json
import subprocess

class ImportantFileFinder:
    def __init__(self, config_path='config.yaml'):
        self.config = self._load_config(config_path)
        self.important_patterns = self.config.get('important_patterns', {})
        self.quick_destinations = self.config.get('quick_destinations', {})

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

    def _load_processed_files(self, log_path):
        """Load list of processed (kept/moved/deleted) files from log"""
        processed = set()
        if not log_path or not Path(log_path).exists():
            return processed

        try:
            with open(log_path, 'r') as f:
                logs = json.load(f)
                if not isinstance(logs, list):
                    logs = [logs]

                for log_entry in logs:
                    for action in log_entry.get('actions', []):
                        if action['action'] in ['KEEP', 'MOVED', 'DELETED', 'TRASHED']:
                            # For MOVED, use 'from' path
                            path = action.get('from') or action.get('path')
                            if path:
                                processed.add(path)
        except Exception as e:
            print(f"Warning: Could not load processed files log: {e}")

        return processed

    def scan_directory(self, directory, recursive=True, exclude_processed_log=None):
        """Scan directory for important files"""
        important_files = []

        # Load processed files to exclude
        processed_files = self._load_processed_files(exclude_processed_log)
        if processed_files:
            print(f"Excluding {len(processed_files)} previously processed files...")

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
                file_path_str = str(file_path)

                # Skip if already processed
                if file_path_str in processed_files:
                    continue

                matches = self._check_file_importance(file_path_str)
                if matches:
                    stat = file_path.stat()
                    important_files.append({
                        'path': file_path_str,
                        'name': file_path.name,
                        'categories': matches,
                        'size': stat.st_size,
                        'age_days': self._get_file_age_days(file_path_str),
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

    def _preview_file(self, file_path):
        """Preview file contents based on type"""
        ext = Path(file_path).suffix.lower()

        # Text-based files - show first 20 lines
        text_extensions = ['.txt', '.csv', '.log', '.md', '.json', '.xml', '.yaml', '.yml', '.pem', '.key']
        if ext in text_extensions:
            try:
                with open(file_path, 'r') as f:
                    lines = f.readlines()[:20]
                    print("\n" + "─" * 80)
                    print("PREVIEW (first 20 lines):")
                    print("─" * 80)
                    for line in lines:
                        print(line.rstrip())
                    if len(lines) == 20:
                        print("... (file continues)")
                    print("─" * 80)
            except Exception as e:
                print(f"Could not preview: {e}")
        else:
            print(f"Cannot preview {ext} files in terminal. Use 'o' to open.")

    def interactive_review(self, files, save_log=None):
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
                print("  [v] View/preview file contents")
                print("  [o] Open file in default app")

                # Show quick destinations
                if self.quick_destinations:
                    print("\n  Quick move destinations:")
                    for key, dest in self.quick_destinations.items():
                        print(f"    [{key}] {dest['label']} ({dest['path']})")

                print("\n  [m] Move to custom location")
                print("  [d] Delete")
                print("  [k] Keep as is (mark reviewed, won't show again)")
                print("  [s] Skip for now (will show in next scan)")
                print("  [q] Quit")

                choice = input("\nChoice: ").lower().strip()

                if choice == 'v':
                    self._preview_file(file_info['path'])
                elif choice == 'o':
                    os.system(f"open '{file_info['path']}'")
                    print("File opened.")
                elif choice in self.quick_destinations:
                    # Quick destination
                    dest_info = self.quick_destinations[choice]
                    dest_path = Path(dest_info['path']).expanduser()

                    # Check if destination is accessible
                    try:
                        # Try to access the parent directory first
                        if not dest_path.parent.exists():
                            print(f"\n❌ Error: Parent directory does not exist: {dest_path.parent}")
                            print(f"   This might be a network drive that's offline.")
                            retry = input("   Try a different destination? (y/n): ")
                            if retry.lower() == 'y':
                                continue
                            else:
                                break

                        # Create destination directory
                        dest_path.mkdir(parents=True, exist_ok=True)

                        # Verify we can write to it
                        if not os.access(dest_path, os.W_OK):
                            print(f"\n❌ Error: Cannot write to destination: {dest_path}")
                            print(f"   Check permissions or if network drive is mounted.")
                            retry = input("   Try a different destination? (y/n): ")
                            if retry.lower() == 'y':
                                continue
                            else:
                                break

                        import shutil
                        new_path = dest_path / file_info['name']
                        counter = 1
                        while new_path.exists():
                            stem = Path(file_info['name']).stem
                            ext = Path(file_info['name']).suffix
                            new_path = dest_path / f"{stem}_{counter}{ext}"
                            counter += 1

                        shutil.move(file_info['path'], str(new_path))
                        actions_log.append({
                            'action': 'MOVED',
                            'from': file_info['path'],
                            'to': str(new_path),
                            'destination': dest_info['label']
                        })
                        print(f"✓ Moved to {dest_info['label']}: {new_path}")
                        break

                    except PermissionError as e:
                        print(f"\n❌ Permission denied: {e}")
                        print(f"   Check if you have write access to {dest_path}")
                        retry = input("   Try a different destination? (y/n): ")
                        if retry.lower() != 'y':
                            break
                    except OSError as e:
                        print(f"\n❌ Error accessing destination: {e}")
                        print(f"   Network drive might be offline or path is invalid.")
                        retry = input("   Try a different destination? (y/n): ")
                        if retry.lower() != 'y':
                            break
                    except Exception as e:
                        print(f"\n❌ Unexpected error: {e}")
                        retry = input("   Try a different destination? (y/n): ")
                        if retry.lower() != 'y':
                            break
                elif choice == 'm':
                    dest = input("Enter destination path: ").strip()
                    dest_path = Path(dest).expanduser()

                    try:
                        if not dest_path.exists():
                            create = input(f"Directory doesn't exist. Create it? (y/n): ")
                            if create.lower() == 'y':
                                dest_path.mkdir(parents=True, exist_ok=True)
                            else:
                                print("Move cancelled.")
                                continue

                        if not dest_path.is_dir():
                            print(f"Error: {dest} is not a directory")
                            continue

                        if not os.access(dest_path, os.W_OK):
                            print(f"Error: Cannot write to {dest_path}")
                            continue

                        import shutil
                        new_path = dest_path / file_info['name']
                        counter = 1
                        while new_path.exists():
                            stem = Path(file_info['name']).stem
                            ext = Path(file_info['name']).suffix
                            new_path = dest_path / f"{stem}_{counter}{ext}"
                            counter += 1

                        shutil.move(file_info['path'], str(new_path))
                        actions_log.append({
                            'action': 'MOVED',
                            'from': file_info['path'],
                            'to': str(new_path)
                        })
                        print(f"✓ Moved to {new_path}")
                        break

                    except Exception as e:
                        print(f"Error moving file: {e}")
                        continue
                elif choice == 'd':
                    print("\nDelete options:")
                    print("  [t] Move to Trash (safe, can recover)")
                    print("  [p] Permanent delete (cannot recover)")
                    print("  [c] Cancel")
                    delete_choice = input("\nChoice: ").lower().strip()

                    if delete_choice == 't':
                        # Move to trash using macOS command
                        try:
                            result = subprocess.run(
                                ['osascript', '-e', f'tell application "Finder" to delete POSIX file "{file_info["path"]}"'],
                                capture_output=True,
                                text=True,
                                check=True
                            )
                            actions_log.append({
                                'action': 'TRASHED',
                                'path': file_info['path']
                            })
                            print("✓ File moved to Trash.")
                            break
                        except subprocess.CalledProcessError as e:
                            print(f"Error moving to trash: {e}")
                            print("Falling back to asking for permanent delete...")
                            continue
                        except Exception as e:
                            print(f"Error: {e}")
                            continue

                    elif delete_choice == 'p':
                        confirm = input("⚠️  PERMANENT DELETE - Are you absolutely sure? (type 'yes'): ").lower()
                        if confirm == 'yes':
                            try:
                                os.remove(file_info['path'])
                                actions_log.append({
                                    'action': 'DELETED',
                                    'path': file_info['path']
                                })
                                print("✓ File permanently deleted.")
                                break
                            except Exception as e:
                                print(f"Error deleting file: {e}")
                                continue
                        else:
                            print("Delete cancelled.")
                    elif delete_choice == 'c':
                        print("Delete cancelled.")
                    else:
                        print("Invalid choice.")
                elif choice == 'k':
                    actions_log.append({
                        'action': 'KEEP',
                        'path': file_info['path']
                    })
                    print("✓ Marked as reviewed (keeping as is).")
                    break
                elif choice == 's':
                    actions_log.append({
                        'action': 'SKIPPED',
                        'path': file_info['path']
                    })
                    print("Skipping for now...")
                    break
                elif choice == 'q':
                    print("\nQuitting...")
                    self._save_action_log(actions_log, save_log)
                    return
                else:
                    print("Invalid choice. Please try again.")

        # Save log at the end
        self._save_action_log(actions_log, save_log)

    def _save_action_log(self, actions_log, save_log):
        """Save actions log to file"""
        if not actions_log:
            return

        print(f"\n{'='*80}")
        print("Review complete! Actions taken:")
        print(f"{'='*80}")
        for action in actions_log:
            if action['action'] == 'MOVED':
                dest = action.get('destination', 'custom location')
                print(f"  MOVED: {action['from']}")
                print(f"      → {action['to']} ({dest})")
            elif action['action'] == 'DELETED':
                print(f"  DELETED (permanent): {action['path']}")
            elif action['action'] == 'TRASHED':
                print(f"  TRASHED (recoverable): {action['path']}")
            elif action['action'] == 'KEEP':
                print(f"  KEEP: {action['path']}")
            elif action['action'] == 'SKIPPED':
                print(f"  SKIPPED: {action['path']}")

        # Save to file if requested
        if save_log:
            log_data = {
                'timestamp': datetime.now().isoformat(),
                'actions': actions_log
            }

            log_path = Path(save_log).expanduser()

            # Append to existing log or create new
            if log_path.exists():
                with open(log_path, 'r') as f:
                    try:
                        existing = json.load(f)
                        if not isinstance(existing, list):
                            existing = [existing]
                    except:
                        existing = []
                existing.append(log_data)
                with open(log_path, 'w') as f:
                    json.dump(existing, f, indent=2)
            else:
                with open(log_path, 'w') as f:
                    json.dump([log_data], f, indent=2)

            print(f"\n✓ Action log saved to: {log_path}")


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
    parser.add_argument(
        '--save-results',
        help='Save scan results to JSON file (e.g., --save-results scan-results.json)'
    )
    parser.add_argument(
        '--save-log',
        help='Save action log to JSON file (e.g., --save-log actions.json)'
    )
    parser.add_argument(
        '--force-rescan',
        action='store_true',
        help='Ignore processed files log and show all files (even previously reviewed ones)'
    )

    args = parser.parse_args()

    finder = ImportantFileFinder(config_path=args.config)

    # Use save_log path to exclude previously processed files (unless force-rescan is enabled)
    exclude_log = None if args.force_rescan else (args.save_log if args.save_log else None)

    files = finder.scan_directory(
        args.directory,
        recursive=not args.non_recursive,
        exclude_processed_log=exclude_log
    )

    # Save scan results if requested
    if args.save_results:
        results_path = Path(args.save_results).expanduser()
        with open(results_path, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'directory': args.directory,
                'file_count': len(files),
                'files': files
            }, f, indent=2, default=str)
        print(f"\n✓ Scan results saved to: {results_path}")

    if args.no_interactive:
        finder.display_results(files)
    else:
        finder.display_results(files)
        if files:
            print("\n" + "="*80)
            proceed = input("\nWould you like to review these files interactively? (y/n): ")
            if proceed.lower() in ['y', 'yes']:
                finder.interactive_review(files, save_log=args.save_log)


if __name__ == '__main__':
    main()
