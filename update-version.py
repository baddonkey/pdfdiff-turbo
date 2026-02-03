#!/usr/bin/env python3
"""
Update version across all components of pdfdiff-turbo project.
This script is cross-platform and works on Windows, Linux, and macOS.

Usage: python update-version.py <version>
Example: python update-version.py 1.1.0
"""

import sys
import re
import json
from pathlib import Path


def validate_version(version: str) -> bool:
    """Validate semantic version format."""
    pattern = r'^\d+\.\d+\.\d+$'
    return bool(re.match(pattern, version))


def update_file(file_path: Path, pattern: str, replacement: str, description: str):
    """Update a file with regex pattern replacement."""
    if not file_path.exists():
        print(f"  ⚠ Skipping {file_path} (not found)")
        return
    
    content = file_path.read_text(encoding='utf-8')
    updated_content = re.sub(pattern, replacement, content)
    
    if content != updated_content:
        file_path.write_text(updated_content, encoding='utf-8')
        print(f"  ✓ Updated {description}")
    else:
        print(f"  ⚠ No changes needed for {description}")


def update_json_version(file_path: Path, new_version: str, description: str):
    """Update version in a JSON file."""
    if not file_path.exists():
        print(f"  ⚠ Skipping {file_path} (not found)")
        return
    
    data = json.loads(file_path.read_text(encoding='utf-8'))
    data['version'] = new_version
    file_path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    print(f"  ✓ Updated {description}")


def main():
    if len(sys.argv) != 2:
        print("❌ Error: Version number required")
        print("Usage: python update-version.py <version>")
        print("Example: python update-version.py 1.1.0")
        sys.exit(1)
    
    new_version = sys.argv[1]
    
    if not validate_version(new_version):
        print("❌ Error: Version must be in format MAJOR.MINOR.PATCH (e.g., 1.2.3)")
        sys.exit(1)
    
    print(f"🔄 Updating pdfdiff-turbo to version {new_version}")
    
    # Get project root (script location)
    root = Path(__file__).parent
    
    # Update root VERSION file
    version_file = root / "VERSION"
    version_file.write_text(new_version, encoding='utf-8')
    print(f"  ✓ Updated VERSION")
    
    # Update package.json files
    update_json_version(
        root / "admin" / "package.json",
        new_version,
        "admin/package.json"
    )
    update_json_version(
        root / "viewer" / "package.json",
        new_version,
        "viewer/package.json"
    )
    update_json_version(
        root / "admin" / "package-lock.json",
        new_version,
        "admin/package-lock.json"
    )
    update_json_version(
        root / "viewer" / "package-lock.json",
        new_version,
        "viewer/package-lock.json"
    )
    
    # Update environment.ts files
    update_file(
        root / "admin" / "src" / "environments" / "environment.ts",
        r"version: '[^']*'",
        f"version: '{new_version}'",
        "admin/src/environments/environment.ts"
    )
    update_file(
        root / "viewer" / "src" / "environments" / "environment.ts",
        r"version: '[^']*'",
        f"version: '{new_version}'",
        "viewer/src/environments/environment.ts"
    )
    
    # Update docker-compose.yml
    update_file(
        root / "docker-compose.yml",
        r'pdfdiff-turbo-(api|worker|flower|viewer|admin):\d+\.\d+\.\d+',
        f'pdfdiff-turbo-\\1:{new_version}',
        "docker-compose.yml image tags"
    )

    # Update k8s base image tags
    update_file(
        root / "k8s" / "base" / "api.yaml",
        r'pdfdiff-turbo-api:\d+\.\d+\.\d+',
        f'pdfdiff-turbo-api:{new_version}',
        "k8s/base/api.yaml image tag"
    )
    update_file(
        root / "k8s" / "base" / "worker.yaml",
        r'pdfdiff-turbo-worker:\d+\.\d+\.\d+',
        f'pdfdiff-turbo-worker:{new_version}',
        "k8s/base/worker.yaml image tag"
    )
    update_file(
        root / "k8s" / "base" / "flower.yaml",
        r'pdfdiff-turbo-flower:\d+\.\d+\.\d+',
        f'pdfdiff-turbo-flower:{new_version}',
        "k8s/base/flower.yaml image tag"
    )
    update_file(
        root / "k8s" / "base" / "viewer.yaml",
        r'pdfdiff-turbo-viewer:\d+\.\d+\.\d+',
        f'pdfdiff-turbo-viewer:{new_version}',
        "k8s/base/viewer.yaml image tag"
    )
    update_file(
        root / "k8s" / "base" / "admin.yaml",
        r'pdfdiff-turbo-admin:\d+\.\d+\.\d+',
        f'pdfdiff-turbo-admin:{new_version}',
        "k8s/base/admin.yaml image tag"
    )

    # Update k8s local overlay tags
    update_file(
        root / "k8s" / "overlays" / "local" / "kustomization.yaml",
        r'newTag:\s*\d+\.\d+\.\d+',
        f'newTag: {new_version}',
        "k8s/overlays/local/kustomization.yaml newTag entries"
    )
    
    print()
    print(f"✅ Version updated to {new_version} successfully!")
    print()
    print("Next steps:")
    print(f"  1. Review changes: git diff")
    print(f"  2. Commit: git commit -am 'chore: bump version to {new_version}'")
    print(f"  3. Tag: git tag v{new_version}")
    print(f"  4. Push: git push && git push --tags")


if __name__ == "__main__":
    main()
