# Creating Releases

This guide explains how to create a new release of Vela with automatic Docker image builds.

## Quick Release Process

Releases are tagged with semantic versions (e.g., `v1.0.0`). When you push a version tag, GitHub Actions automatically builds and publishes Docker images.

### Steps

1. **Ensure master is ready**:
   ```bash
   git checkout master
   git pull origin master
   ```

2. **Create a version tag**:
   ```bash
   git tag -a v1.0.0 -m "Release version 1.0.0"
   ```

3. **Push the tag**:
   ```bash
   git push origin v1.0.0
   ```

4. **Done!** GitHub Actions will:
   - Run all tests
   - Build the Docker image
   - Push to Docker Hub with multiple tags

## What Gets Published

When you release `v1.2.3`, these Docker images are created:

- `vela:latest` - Latest stable release
- `vela:1.2.3` - Specific version
- `vela:1.2` - Latest patch in 1.2.x
- `vela:1` - Latest minor in 1.x.x

Users can choose how they want to track updates:
```bash
# Always get latest
docker pull yourname/vela:latest

# Pin to specific version
docker pull yourname/vela:1.2.3

# Auto-update patches only
docker pull yourname/vela:1.2
```

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **Major** (`v2.0.0`): Breaking changes
- **Minor** (`v1.1.0`): New features, backward compatible
- **Patch** (`v1.0.1`): Bug fixes only

## GitHub Release (Optional)

After pushing a tag, you can create a GitHub Release:

1. Go to [Releases](https://github.com/jkkicks/Vela/releases)
2. Click "Create a new release"
3. Select your tag
4. Add release notes
5. Publish

## Monitoring Builds

Watch the build progress:
1. Go to [GitHub Actions](https://github.com/jkkicks/Vela/actions)
2. Find your tag in the workflow runs
3. Monitor the build and push process

If the build fails, the workflow will show errors in the logs.

## Requirements

Ensure these GitHub secrets are configured:
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

See [GitHub Secrets documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets) for setup.
