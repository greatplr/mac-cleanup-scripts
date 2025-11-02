# Mac Cleanup Scripts

A set of Python scripts to help keep your Mac clean and organized by identifying important files and automatically organizing/cleaning up common folders like Downloads and Desktop.

## Installation

1. Clone this repository:
```bash
git clone https://github.com/YOUR_USERNAME/scripts.git
cd scripts
```

2. Install dependencies:
```bash
pip3 install -r requirements.txt
# or
python3 -m pip install -r requirements.txt
```

3. Copy the example config:
```bash
cp config.yaml.example config.yaml
```

4. Customize `config.yaml` to your needs

## Project Structure

```
scripts/
├── cleanup/              # Folder cleanup and organization scripts
│   ├── important-file-finder.py
│   └── cleanup-folders.py
├── utilities/            # General Mac utilities (future)
├── automation/           # Automation helpers (future)
├── docs/                 # Extended documentation
├── config.yaml.example   # Configuration template
└── requirements.txt      # Python dependencies
```

## Scripts

### 1. cleanup/important-file-finder.py

Scans directories for files that may contain important information (credentials, 2FA codes, financial documents, etc.) and helps you decide what to do with them.

**Usage:**

```bash
# Scan Downloads folder (default)
./cleanup/important-file-finder.py

# Scan a specific folder
./cleanup/important-file-finder.py ~/Desktop

# Non-recursive scan (current directory only)
./cleanup/important-file-finder.py ~/Documents --non-recursive

# Just show results without interactive review
./cleanup/important-file-finder.py ~/Downloads --no-interactive
```

**Features:**
- Identifies files matching important patterns (credentials, 2FA backup codes, financial docs, etc.)
- Interactive review mode to decide what to do with each file
- Actions: Keep, Move, Delete, Open, or Skip
- Shows file age, size, and categories

### 2. cleanup/cleanup-folders.py

Automatically organizes and cleans up folders based on file age, type, and importance. **Safe by default** - important files are never auto-deleted.

**Usage:**

```bash
# Dry run (see what would happen without making changes)
./cleanup/cleanup-folders.py --dry-run

# Clean Downloads and Desktop (default)
./cleanup/cleanup-folders.py

# Clean specific folders
./cleanup/cleanup-folders.py ~/Downloads ~/Documents

# Always test with --dry-run first!
./cleanup/cleanup-folders.py ~/Downloads --dry-run
```

**Features:**
- Automatically categorizes files by type (documents, images, videos, etc.)
- Age-based cleanup rules
- Protects important files from auto-deletion
- Organizes files into appropriate folders
- Archives old files instead of deleting them
- Dry-run mode for safety

### 3. config.yaml

Configuration file that defines:
- **Important file patterns** - Files to protect and flag for review
- **File categories** - File types by extension
- **Cleanup rules** - Age-based and category-based cleanup behavior
- **Organization targets** - Where to move files when organizing

## Configuration

Edit `config.yaml` to customize:

### Important Patterns

Add patterns to identify important files:

```yaml
important_patterns:
  credentials:
    - "*credentials*.csv"
    - "*password*.txt"
  custom_category:
    - "*your*pattern*.ext"
```

### Cleanup Rules

Configure how files are handled:

```yaml
cleanup_rules:
  by_category:
    temporary:
      delete_after_days: 7

    images:
      organize_to: ~/Pictures/Downloaded

  by_age:
    - days: 180
      action: archive
```

**Available actions:**
- `delete_after_days` - Delete files older than X days
- `archive_after_days` - Move to _archive subfolder after X days
- `organize_to` - Move to specified directory

## Recommended Workflow

### Step 1: Find Important Files

Run the important file finder on your Downloads and Desktop to identify files that need your attention:

```bash
./important-file-finder.py ~/Downloads
./important-file-finder.py ~/Desktop
```

Review each file and move important items to appropriate locations.

### Step 2: Test Cleanup

Run cleanup in dry-run mode to see what would happen:

```bash
./cleanup-folders.py --dry-run
```

Review the output to ensure nothing important would be deleted.

### Step 3: Run Cleanup

Once you're comfortable with the rules:

```bash
./cleanup-folders.py
```

### Step 4: Automate (Optional)

Create a cron job or use launchd to run these scripts regularly:

```bash
# Example: Run cleanup weekly
# Add to crontab (crontab -e):
0 10 * * 0 cd /Users/ryan/Code/scripts && ./cleanup/cleanup-folders.py
```

## Safety Features

- **Important files are never auto-deleted** - Files matching important patterns are flagged and skipped
- **Dry-run mode** - Test before making changes
- **Archives instead of deletes** - Old files are moved to `_archive` folder by default
- **Non-recursive by default** - Only processes files in the target directory, not subdirectories
- **Conflict handling** - Automatically renames files if name conflicts occur when moving

## Examples

### Example 1: Weekly Cleanup Routine

```bash
# Monday morning: Find important files
./cleanup/important-file-finder.py ~/Downloads
./cleanup/important-file-finder.py ~/Desktop

# Review and organize important files manually

# Then cleanup the rest
./cleanup/cleanup-folders.py
```

### Example 2: Before Backup

```bash
# Find any credentials or important docs before backup
./cleanup/important-file-finder.py ~ --no-interactive

# Review the list and ensure everything is properly organized
```

### Example 3: Aggressive Cleanup

Modify `config.yaml` to be more aggressive:

```yaml
cleanup_rules:
  by_age:
    - days: 90
      action: delete
```

Then run with dry-run first:

```bash
./cleanup/cleanup-folders.py --dry-run
```

## Customization

Add your own important patterns in `config.yaml`:

```yaml
important_patterns:
  work_docs:
    - "*NDA*.pdf"
    - "*contract*.pdf"

  personal:
    - "*medical*.pdf"
    - "*prescription*.pdf"
```

Add custom file categories:

```yaml
file_categories:
  ebooks:
    - .epub
    - .mobi
    - .azw
```

## Tips

1. **Start conservative** - Begin with dry-run mode and short retention periods
2. **Review regularly** - Run important-file-finder weekly to catch important files
3. **Customize patterns** - Add patterns specific to your workflow
4. **Check archives** - Periodically review `_archive` folders before permanent deletion
5. **Backup first** - Always have backups before running cleanup scripts

## License

Free to use and modify as needed.
