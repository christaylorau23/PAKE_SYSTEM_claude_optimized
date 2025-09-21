#!/usr/bin/env python3
"""
Install Git hooks for PAKE+ system
"""

import os
import shutil
import stat
from pathlib import Path


def install_git_hooks():
    """Install Git hooks for PAKE+ validation"""

    project_root = Path(__file__).parent.parent
    git_hooks_dir = project_root / ".git" / "hooks"
    scripts_dir = project_root / "scripts"

    if not git_hooks_dir.exists():
        print(
            "❌ Error: .git/hooks directory not found. Make sure you're in a Git repository.",
        )
        return False

    # Install pre-commit hook
    pre_commit_source = scripts_dir / "pre-commit"
    pre_commit_target = git_hooks_dir / "pre-commit"

    if not pre_commit_source.exists():
        print("❌ Error: pre-commit script not found")
        return False

    try:
        # Copy the hook
        shutil.copy2(pre_commit_source, pre_commit_target)

        # Make it executable
        current_permissions = stat.S_IMODE(os.lstat(pre_commit_target).st_mode)
        os.chmod(pre_commit_target, current_permissions | stat.S_IEXEC)

        print("✅ Pre-commit hook installed successfully")

        # Create commit-msg hook for enhanced validation
        commit_msg_content = '''#!/usr/bin/env python3
"""
PAKE+ commit message validation
"""

import sys
import re

def validate_commit_message(message):
    """Validate commit message format"""
    lines = message.strip().split('\\n')

    if not lines:
        return False, "Commit message cannot be empty"

    # Check first line length
    if len(lines[0]) > 72:
        return False, "Commit message first line too long (max 72 characters)"

    # Check for conventional commit format (optional)
    conventional_pattern = r'^(feat|fix|docs|style|refactor|test|chore|pake)(\\(.+\\))?: .+'
    if not re.match(conventional_pattern, lines[0]):
        return False, "Consider using conventional commit format: type(scope): description"

    return True, "Valid commit message"

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(1)

    with open(sys.argv[1], 'r') as f:
        commit_message = f.read()

    valid, message = validate_commit_message(commit_message)

    if not valid:
        print(f"❌ Commit message validation failed: {message}")
        sys.exit(1)

    print("✅ Commit message validated")
    sys.exit(0)
'''

        commit_msg_target = git_hooks_dir / "commit-msg"
        with open(commit_msg_target, "w") as f:
            f.write(commit_msg_content)

        # Make commit-msg hook executable
        current_permissions = stat.S_IMODE(os.lstat(commit_msg_target).st_mode)
        os.chmod(commit_msg_target, current_permissions | stat.S_IEXEC)

        print("✅ Commit-msg hook installed successfully")

        # Create post-commit hook for logging
        post_commit_content = '''#!/usr/bin/env python3
"""
PAKE+ post-commit logging
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path

def log_commit():
    """Log commit information for PAKE+ system"""
    try:
        # Get commit info
        commit_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
        commit_msg = subprocess.check_output(['git', 'log', '-1', '--pretty=%s']).decode().strip()
        author = subprocess.check_output(['git', 'log', '-1', '--pretty=%an']).decode().strip()

        # Get changed files
        changed_files = subprocess.check_output([
            'git', 'diff-tree', '--no-commit-id', '--name-only', '-r', commit_hash
        ]).decode().strip().split('\\n')

        # Filter markdown files in vault
        vault_files = [f for f in changed_files if f.startswith('vault/') and f.endswith('.md')]

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'commit_hash': commit_hash,
            'commit_message': commit_msg,
            'author': author,
            'vault_files_changed': vault_files,
            'total_files_changed': len(changed_files)
        }

        # Write to log file
        log_file = Path('logs/git-commits.jsonl')
        log_file.parent.mkdir(exist_ok=True)

        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\\n')

    except Exception as e:
        print(f"Warning: Could not log commit: {e}")

if __name__ == "__main__":
    log_commit()
'''

        post_commit_target = git_hooks_dir / "post-commit"
        with open(post_commit_target, "w") as f:
            f.write(post_commit_content)

        # Make post-commit hook executable
        current_permissions = stat.S_IMODE(os.lstat(post_commit_target).st_mode)
        os.chmod(post_commit_target, current_permissions | stat.S_IEXEC)

        print("✅ Post-commit hook installed successfully")

        return True

    except Exception as e:
        print(f"❌ Error installing hooks: {str(e)}")
        return False


def test_hooks():
    """Test that hooks are working correctly"""
    print("\\n🧪 Testing Git hooks...")

    # Create a test file with invalid frontmatter
    test_file = Path("vault/00-Inbox/test-validation.md")
    test_file.parent.mkdir(parents=True, exist_ok=True)

    invalid_content = """---
invalid: frontmatter
missing: required fields
---

# Test File

This is a test file for validation.
"""

    with open(test_file, "w") as f:
        f.write(invalid_content)

    print("✅ Created test file with invalid frontmatter")
    print("💡 Try committing this file to test the validation hook:")
    print(f"   git add {test_file}")
    print("   git commit -m 'test: validate git hooks'")
    print("\\n⚠️  The commit should fail with validation errors.")
    print("\\n🔧 Run the pre-commit script directly to see validation in action:")
    print("   python scripts/pre-commit")


if __name__ == "__main__":
    print("🔧 Installing PAKE+ Git hooks...")

    if install_git_hooks():
        print("\\n✅ All hooks installed successfully!")
        test_hooks()
    else:
        print("\\n❌ Hook installation failed")
        exit(1)
