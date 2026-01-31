# Semantic Versioning for pdfdiff-turbo

This project uses [Semantic Versioning](https://semver.org/) with the format: **MAJOR.MINOR.PATCH**

## Current Version
See the [VERSION](VERSION) file for the current version.

## Version Components

- **MAJOR**: Breaking changes that are not backward compatible
- **MINOR**: New features that are backward compatible
- **PATCH**: Bug fixes and minor improvements that are backward compatible

## How to Update the Version

### Quick Bump with Git (Recommended)

```bash
python bump-version.py 1.1.0 "Add new PDF comparison features"
```

This script automatically:
- Updates all version references
- Creates a git commit
- Creates a git tag
- Optionally pushes to remote

### Update Version Only

If you just want to update version files without git operations:

```bash
python update-version.py 1.1.0
```

### Manual Update
1. Update the [VERSION](VERSION) file in the project root
2. Manually update all other locations (see below)

### Version Locations

The version is managed in these locations:

1. **Root VManagement Scripts

### bump-version.py (Recommended)

Complete version bump with git integration:

```bash
python bump-version.py 1.2.0 "Description of changes"
```

**Features:**
- Updates all version references
- Creates git commit with your message
- Creates annotated git tag (v1.2.0)
- Optionally pushes to remote
- Checks for uncommitted changes
- Cross-platform (Windows, Linux, macOS)

### update-version.py

Version update only (no git operations):

```bash
python update-version.py 1.2.0
```

**What both scripts updateon.py` script synchronizes the version across all components:

```bash
python update-version.py 1.2.0
```

**Features:**
- Cross-platform (Windows, Linux, macOS)
- No external dependencies (Python standard library only)
- Validates semantic version format
- Updates all version references atomically

**What it updates:**
- Root VERSION file
- admin/package.json
- viewer/package.json
- admin/src/environments/environment.ts
- viewer/src/environments/environment.ts
- docker-compose.yml image tags

## API Version Endpoint

The API exposes version information at:
- `GET /version` - Returns `{"version": "1.0.0"}`
- `/docs` - Includes version in OpenAPI documentation

## Docker Image Versioning

Docker images are tagged with the version:
- `pdfdiff-turbo-api:1.0.0`
- `pdfdiff-turbo-worker:1.0.0`
- `pdfdiff-turbo-flower:1.0.0`
- `pdfdiff-turbo-viewer:1.0.0`
- `pdfdiff-turbo-admin:1.0.0`

## Release Checklist

When releasing a new version:

1. Update VERSION file with new version number
2. Run `.\update-version.ps1` to sync all files
3. Commit changes: `git commit -am "chore: bump version to X.Y.Z"`
4. Tag release: `git tag vX.Y.Z`
5. Push with tags: `git push && git push --tags`
6. Build Docker images: `docker-compose build`
7. Optional: Push images to registry

## Example Version History

- `1.0.0` - Initial release with semantic versioning
- `1.0.1` - Bug fixes (PATCH)
- `1.1.0` - New features (MINOR)
- `2.0.0` - Breaking changes (MAJOR)
