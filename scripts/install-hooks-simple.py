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
            "Error: .git/hooks directory not found. Make sure you're in a Git repository.",
        )
        return False

    # Install pre-commit hook
    pre_commit_source = scripts_dir / "pre-commit"
    pre_commit_target = git_hooks_dir / "pre-commit"

    if not pre_commit_source.exists():
        print("Error: pre-commit script not found")
        return False

    try:
        # Copy the hook
        shutil.copy2(pre_commit_source, pre_commit_target)

        # Make it executable (Windows compatible)
        if os.name != "nt":  # Not Windows
            current_permissions = stat.S_IMODE(os.lstat(pre_commit_target).st_mode)
            os.chmod(pre_commit_target, current_permissions | stat.S_IEXEC)

        print("Pre-commit hook installed successfully")
        return True

    except Exception as e:
        print(f"Error installing hooks: {str(e)}")
        return False


if __name__ == "__main__":
    print("Installing PAKE+ Git hooks...")

    if install_git_hooks():
        print("Hooks installed successfully!")
    else:
        print("Hook installation failed")
        exit(1)
