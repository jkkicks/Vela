# Contributing to SparkBot

Thank you for considering contributing to SparkBot! We welcome contributions from everyone. This guide will help you get started.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Process](#development-process)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

### Our Pledge
We are committed to providing a friendly, safe, and welcoming environment for all contributors.

### Expected Behavior
- Be respectful and inclusive
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards other community members

### Unacceptable Behavior
- Harassment, discrimination, or offensive comments
- Personal attacks or trolling
- Publishing private information without consent
- Any conduct that would be inappropriate in a professional setting

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates.

**To report a bug:**
1. Go to [GitHub Issues](https://github.com/jkkicks/SparkBot/issues)
2. Click "New Issue"
3. Choose "Bug Report" template
4. Include:
   - Clear description of the bug
   - Steps to reproduce
   - Expected vs actual behavior
   - System information (OS, Python version)
   - Relevant logs or error messages

### Suggesting Features

We love feature suggestions!

**To suggest a feature:**
1. Check [existing issues](https://github.com/jkkicks/SparkBot/issues) first
2. Create a new issue with "Feature Request" template
3. Describe:
   - The problem you're trying to solve
   - Your proposed solution
   - Alternative solutions considered
   - Any mockups or examples

### Contributing Code

#### First Time Contributors
1. Fork the repository
2. Set up your development environment:
   ```bash
   git clone https://github.com/your-username/SparkBot.git
   cd SparkBot
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

#### Making Changes
1. Write your code following our [coding standards](#coding-standards)
2. Add or update tests as needed
3. Update documentation if necessary
4. Test your changes thoroughly

## Development Process

### 1. Setting Up Development Environment

See [Development Setup Guide](docs/development/setup.md) for detailed instructions.

```bash
# Quick setup
git clone https://github.com/jkkicks/SparkBot.git
cd SparkBot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python download_assets.py
cp .env.example .env
# Edit .env with your configuration
```

### 2. Project Structure

Familiarize yourself with the [project structure](docs/development/project-structure.md):
- `src/bot/` - Discord bot code
- `src/api/` - Web interface
- `src/shared/` - Shared modules
- `templates/` - HTML templates
- `docs/` - Documentation

### 3. Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_bot/test_commands.py

# Run with coverage
pytest --cov=src

# Run linting
black src/
ruff check src/
```

### 4. Testing Your Changes

- **Bot Commands**: Test in a development Discord server
- **Web Interface**: Test at http://localhost:8000
- **API Endpoints**: Use the Swagger UI at http://localhost:8000/docs

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with these specifics:
- Line length: 100 characters (120 for docstrings)
- Use `black` for formatting
- Use `ruff` for linting

### Code Formatting

```bash
# Format code
black src/ tests/

# Check formatting
black --check src/ tests/

# Lint code
ruff check src/ tests/
```

### Naming Conventions

- **Files**: `lowercase_with_underscores.py`
- **Classes**: `PascalCase`
- **Functions/Variables**: `lowercase_with_underscores`
- **Constants**: `UPPERCASE_WITH_UNDERSCORES`
- **Private methods**: `_leading_underscore`

### Documentation

- Add docstrings to all public functions/classes
- Use Google-style docstrings:
  ```python
  def calculate_something(param1: str, param2: int) -> dict:
      """Calculate something important.

      Args:
          param1: Description of param1
          param2: Description of param2

      Returns:
          Dictionary containing the results

      Raises:
          ValueError: If param2 is negative
      """
  ```

### Type Hints

Always use type hints:
```python
from typing import Optional, List, Dict

def process_data(
    user_id: int,
    data: List[str],
    options: Optional[Dict[str, Any]] = None
) -> bool:
    ...
```

## Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, etc.)
- **refactor**: Code refactoring
- **test**: Adding/updating tests
- **chore**: Maintenance tasks

### Examples

```bash
# Feature
git commit -m "feat(bot): add custom welcome message support"

# Bug fix
git commit -m "fix(api): resolve OAuth redirect loop"

# Documentation
git commit -m "docs: update installation guide for Windows"

# With body
git commit -m "feat(web): add user export functionality

- Add CSV export endpoint
- Add JSON export endpoint
- Add export button to UI
- Include date range filtering

Closes #123"
```

## Pull Request Process

### Before Submitting

1. **Update from main**:
   ```bash
   git fetch upstream
   git rebase upstream/master
   ```

2. **Run tests**:
   ```bash
   pytest
   black --check src/
   ruff check src/
   ```

3. **Update documentation** if needed

4. **Write a good PR description**

### PR Template

When you create a PR, fill out the template:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added new tests
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
```

### Review Process

1. **Automated checks** run on PR creation
2. **Maintainer review** - we aim to review within 48 hours
3. **Feedback** - address any requested changes
4. **Approval** - once approved, we'll merge your PR

### After Merge

- Delete your feature branch
- Pull the latest main branch
- Celebrate your contribution! 🎉

## Getting Help

### Resources
- [Documentation](docs/README.md)
- [Discord Server](https://discord.gg/your-invite)
- [GitHub Discussions](https://github.com/jkkicks/SparkBot/discussions)

### Contact
- Open an issue for bugs/features
- Use discussions for questions
- Email: [your-email@example.com]

## Recognition

Contributors are recognized in:
- [README.md](README.md) acknowledgments
- GitHub contributors page
- Release notes

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

---

Thank you for contributing to SparkBot! Your efforts help make this project better for everyone. 🚀