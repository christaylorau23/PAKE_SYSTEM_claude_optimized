#!/usr/bin/env python3
"""
PAKE System - Filesystem Issue Fixes
===================================

This script fixes the critical filesystem issues identified in the PAKE System
that could cause CI failures on case-sensitive filesystems.

Key Fixes:
1. Remove hardcoded Windows paths from ai-security-monitor.py
2. Create CI-compatible diagnostic script
3. Document directory naming conventions
"""

import os
import sys
from pathlib import Path


def fix_ai_security_monitor(self) -> None:
    """Fix hardcoded path in ai-security-monitor.py"""
    print("🔧 Fixing ai-security-monitor.py...")

    file_path = Path("src/ai-security-monitor.py")
    if not file_path.exists():
        print("❌ ai-security-monitor.py not found")
        return False

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Replace hardcoded Windows path with relative path
        old_line = 'sys.path.append("/d/Projects/PAKE_SYSTEM/mcp-servers")'
        new_line = '# sys.path.append("/d/Projects/PAKE_SYSTEM/mcp-servers")  # Removed hardcoded path for CI compatibility'

        if old_line in content:
            content = content.replace(old_line, new_line)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            print("✅ Fixed hardcoded path in ai-security-monitor.py")
            return True
        print("ℹ️  No hardcoded path found in ai-security-monitor.py")
        return True

    except Exception as e:
        print(f"❌ Error fixing ai-security-monitor.py: {e}")
        return False


def create_ci_diagnostic_script(self) -> None:
    """Create a CI-compatible diagnostic script"""
    print("📝 Creating CI-compatible diagnostic script...")

    script_content = '''#!/usr/bin/env python3
"""
PAKE System - CI Filesystem Diagnostics
=======================================

Lightweight diagnostic script for CI environments to detect filesystem issues.
"""

import os
import sys
from pathlib import Path

def check_critical_issues(self) -> None:
    """Check for critical filesystem issues that cause CI failures"""
    issues = []

    # Check for problematic directory names with hyphens
    problematic_dirs = [
        'src/services/secrets-manager',
        'src/services/agent-runtime',
        'src/services/enterprise-integrations',
        'src/services/social-media-automation',
        'src/services/video-generation',
        'src/services/voice-agents'
    ]

    for dir_path in problematic_dirs:
        if Path(dir_path).exists():
            issues.append(f"Directory with hyphens: {dir_path}")

    # Check for hardcoded Windows paths in source files only
    source_files = list(Path("src").rglob("*.py")) if Path("src").exists() else []

    for py_file in source_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\\n')
            for i, line in enumerate(lines, 1):
                # Check for hardcoded Windows paths
                if '/d/Projects/' in line or '/c/' in line.lower():
                    issues.append(f"Hardcoded Windows path in {py_file}:{i}")
                    break

        except Exception:
            continue  # Skip files that can't be read

    return issues

def main(self) -> None:
    """Main function"""
    print("🔍 PAKE System - CI Filesystem Diagnostics")
    print("=" * 50)

    issues = check_critical_issues()

    if issues:
        print(f"❌ Found {len(issues)} critical issues:")
        for issue in issues:
            print(f"  • {issue}")

        print("\\n💡 Recommendations:")
        print("  1. Replace hyphens with underscores in directory names")
        print("  2. Remove hardcoded Windows paths")
        print("  3. Use relative imports instead of sys.path manipulation")

        return 1
    else:
        print("✅ No critical filesystem issues found!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
'''

    try:
        with open("scripts/ci_filesystem_check.py", "w", encoding="utf-8") as f:
            f.write(script_content)

        # Make it executable
        os.chmod("scripts/ci_filesystem_check.py", 0o755)

        print("✅ Created CI-compatible diagnostic script")
        return True

    except Exception as e:
        print(f"❌ Error creating CI diagnostic script: {e}")
        return False


def create_directory_naming_guide(self) -> None:
    """Create a guide for directory naming conventions"""
    print("📚 Creating directory naming guide...")

    guide_content = """# PAKE System - Directory Naming Conventions

## CI-Compatible Directory Naming

To ensure compatibility with case-sensitive filesystems (Linux CI environments), follow these conventions:

### ✅ Recommended Patterns
- Use underscores: `src/services/secrets_manager`
- Use lowercase: `src/services/analytics`
- Use hyphens only for non-Python directories: `docs/api-reference`

### ❌ Avoid These Patterns
- Hyphens in Python package directories: `src/services/secrets-manager`
- Mixed case without clear pattern: `src/services/AgentRuntime`
- Spaces in directory names: `src/services/social media`

### Current Problematic Directories
The following directories use hyphens and may cause import issues on case-sensitive filesystems:

1. `src/services/secrets-manager` → `src/services/secrets_manager`
2. `src/services/agent-runtime` → `src/services/agent_runtime`
3. `src/services/enterprise-integrations` → `src/services/enterprise_integrations`
4. `src/services/social-media-automation` → `src/services/social_media_automation`
5. `src/services/video-generation` → `src/services/video_generation`
6. `src/services/voice-agents` → `src/services/voice_agents`

### Migration Strategy
1. Create new directories with underscore naming
2. Move Python files to new directories
3. Update import statements
4. Update any references in configuration files
5. Test on case-sensitive filesystem

### Testing on Case-Sensitive Filesystem
```bash
# Test imports work correctly
python -c "import src.services.secrets_manager"
python -c "import src.services.agent_runtime"
```

## References
- [Python Package Naming](https://packaging.python.org/en/latest/specifications/name-normalization/)
- [PEP 8 - Style Guide](https://peps.python.org/pep-0008/)
"""

    try:
        with open("docs/DIRECTORY_NAMING_CONVENTIONS.md", "w", encoding="utf-8") as f:
            f.write(guide_content)

        print("✅ Created directory naming guide")
        return True

    except Exception as e:
        print(f"❌ Error creating naming guide: {e}")
        return False


def create_ci_workflow_step(self) -> None:
    """Create a GitHub Actions step for filesystem diagnostics"""
    print("🚀 Creating CI workflow step...")

    workflow_step = """# Add this step to your GitHub Actions workflow
- name: Check Filesystem Compatibility
  run: |
    echo "🔍 Checking filesystem compatibility..."
    python scripts/ci_filesystem_check.py
    if [ $? -ne 0 ]; then
      echo "❌ Filesystem compatibility issues detected"
      echo "Please fix the issues listed above before merging"
      exit 1
    fi
    echo "✅ Filesystem compatibility check passed"
"""

    try:
        with open("scripts/ci_filesystem_check_step.yml", "w", encoding="utf-8") as f:
            f.write(workflow_step)

        print("✅ Created CI workflow step")
        return True

    except Exception as e:
        print(f"❌ Error creating workflow step: {e}")
        return False


def main(self) -> None:
    """Main function"""
    print("=" * 60)
    print("PAKE SYSTEM - FILESYSTEM ISSUE FIXES")
    print("=" * 60)

    fixes_applied = 0
    total_fixes = 4

    # Apply fixes
    if fix_ai_security_monitor():
        fixes_applied += 1

    if create_ci_diagnostic_script():
        fixes_applied += 1

    if create_directory_naming_guide():
        fixes_applied += 1

    if create_ci_workflow_step():
        fixes_applied += 1

    print("\\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Applied {fixes_applied}/{total_fixes} fixes")

    if fixes_applied == total_fixes:
        print("✅ All fixes applied successfully!")
        print("\\n📋 Next Steps:")
        print("1. Test the CI diagnostic script: python scripts/ci_filesystem_check.py")
        print("2. Add the CI workflow step to your GitHub Actions")
        print("3. Consider renaming directories with hyphens to underscores")
        print("4. Test imports on a case-sensitive filesystem")
        return 0
    print("❌ Some fixes failed to apply")
    return 1


if __name__ == "__main__":
    sys.exit(main())
