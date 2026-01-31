#!/usr/bin/env python3
"""
Bump version and create git commit with tag automatically.
This script updates the version, commits changes, and creates a git tag.

Usage: python bump-version.py <version> <commit-message>
Example: python bump-version.py 1.1.0 "Add new PDF comparison features"
"""

import sys
import re
import json
import subprocess
from pathlib import Path


def validate_version(version: str) -> bool:
    """Validate semantic version format."""
    pattern = r'^\d+\.\d+\.\d+$'
    return bool(re.match(pattern, version))


def run_command(cmd: list, description: str, capture=False):
    """Run a shell command and handle errors."""
    try:
        if capture:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during {description}: {e}")
        sys.exit(1)


def update_file(file_path: Path, pattern: str, replacement: str):
    """Update a file with regex pattern replacement."""
    if not file_path.exists():
        return False
    
    content = file_path.read_text(encoding='utf-8')
    updated_content = re.sub(pattern, replacement, content)
    
    if content != updated_content:
        file_path.write_text(updated_content, encoding='utf-8')
        return True
    return False


def update_json_version(file_path: Path, new_version: str):
    """Update version in a JSON file."""
    if not file_path.exists():
        return False
    
    data = json.loads(file_path.read_text(encoding='utf-8'))
    data['version'] = new_version
    file_path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return True


def check_git_status():
    """Check if working directory is clean."""
    result = subprocess.run(['git', 'status', '--porcelain'], 
                          capture_output=True, text=True)
    return result.stdout.strip()


def main():
    if len(sys.argv) != 3:
        print("❌ Error: Version and commit message required")
        print("Usage: python bump-version.py <version> <message>")
        print("Example: python bump-version.py 1.1.0 'Add new features'")
        sys.exit(1)
    
    new_version = sys.argv[1]
    commit_message = sys.argv[2]
    
    if not validate_version(new_version):
        print("❌ Error: Version must be in format MAJOR.MINOR.PATCH (e.g., 1.2.3)")
        sys.exit(1)
    
    # Check if git is available
    try:
        subprocess.run(['git', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: Git is not installed or not in PATH")
        sys.exit(1)
    
    # Check for uncommitted changes (excluding version files)
    dirty = check_git_status()
    if dirty:
        # Filter out version-related files
        version_files = ['VERSION', 'package.json', 'environment.ts', 'docker-compose.yml']
        other_changes = [line for line in dirty.split('\n') 
                        if not any(vf in line for vf in version_files)]
        if other_changes:
            print("⚠️  Warning: You have uncommitted changes:")
            print('\n'.join(other_changes))
            response = input("Continue anyway? (y/N): ").strip().lower()
            if response != 'y':
                print("Aborted.")
                sys.exit(0)
    
    print(f"🔄 Bumping version to {new_version}")
    
    # Get project root
    root = Path(__file__).parent
    
    # Update all version references
    version_file = root / "VERSION"
    version_file.write_text(new_version, encoding='utf-8')
    print(f"  ✓ Updated VERSION")
    
    update_json_version(root / "admin" / "package.json", new_version)
    print(f"  ✓ Updated admin/package.json")
    
    update_json_version(root / "viewer" / "package.json", new_version)
    print(f"  ✓ Updated viewer/package.json")
    
    if update_file(
        root / "admin" / "src" / "environments" / "environment.ts",
        r"version: '[^']*'",
        f"version: '{new_version}'"
    ):
        print(f"  ✓ Updated admin/src/environments/environment.ts")
    
    if update_file(
        root / "viewer" / "src" / "environments" / "environment.ts",
        r"version: '[^']*'",
        f"version: '{new_version}'"
    ):
        print(f"  ✓ Updated viewer/src/environments/environment.ts")
    
    update_file(
        root / "docker-compose.yml",
        r'pdfdiff-turbo-(api|worker|flower|viewer|admin):\d+\.\d+\.\d+',
        f'pdfdiff-turbo-\\1:{new_version}'
    )
    print(f"  ✓ Updated docker-compose.yml")
    
    print()
    print("📝 Creating git commit and tag...")
    
    # Stage all changes
    run_command(['git', 'add', '.'], "staging changes")
    print("  ✓ Staged changes")
    
    # Create commit
    full_commit_message = f"chore: bump version to {new_version}\n\n{commit_message}"
    run_command(['git', 'commit', '-m', full_commit_message], "creating commit")
    print(f"  ✓ Created commit")
    
    # Create tag
    tag_name = f"v{new_version}"
    run_command(['git', 'tag', '-a', tag_name, '-m', commit_message], "creating tag")
    print(f"  ✓ Created tag {tag_name}")
    
    print()
    print(f"✅ Version bumped to {new_version} successfully!")
    print()
    print("Next steps:")
    print(f"  Push changes: git push && git push --tags")
    print()
    
    # Ask if user wants to push
    response = input("Push to remote now? (y/N): ").strip().lower()
    if response == 'y':
        print()
        print("🚀 Pushing to remote...")
        run_command(['git', 'push'], "pushing commits")
        print("  ✓ Pushed commits")
        run_command(['git', 'push', '--tags'], "pushing tags")
        print("  ✓ Pushed tags")
        print()
        print("🎉 All done!")


if __name__ == "__main__":
    main()
