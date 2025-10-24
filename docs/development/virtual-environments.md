# Virtual Environment Quick Reference Guide

## What is a Virtual Environment?

A virtual environment is an isolated Python environment that allows you to install packages for a specific project without affecting your system Python installation or other projects.

## Quick Commands

### Windows (PowerShell)

```powershell
# Create virtual environment
python -m venv .venv

# Activate
.\.venv\Scripts\Activate.ps1

# Deactivate
deactivate

# Delete virtual environment
Remove-Item .venv -Recurse -Force
```

### Windows (Command Prompt)

```cmd
# Create virtual environment
python -m venv .venv

# Activate
.venv\Scripts\activate.bat

# Deactivate
deactivate

# Delete virtual environment
rmdir /s .venv
```

### macOS/Linux

```bash
# Create virtual environment
python3 -m venv .venv

# Activate
source .venv/bin/activate

# Deactivate
deactivate

# Delete virtual environment
rm -rf .venv
```

## How to Know if Virtual Environment is Active

When activated, you'll see `(.venv)` at the beginning of your command prompt:

**Before activation:**
```
PS C:\Users\jkkic\PycharmProjects\SparkBot>
```

**After activation:**
```
(.venv) PS C:\Users\jkkic\PycharmProjects\SparkBot>
```

## Common Commands After Activation

```bash
# Check which Python is being used
which python     # Mac/Linux
where python     # Windows

# Check installed packages
pip list

# Install from requirements
pip install -r requirements.txt

# Save current packages to requirements
pip freeze > requirements.txt

# Upgrade pip itself
pip install --upgrade pip
```

## Troubleshooting

### PowerShell Execution Policy (Windows)

If you get an error about execution policies:

```powershell
# Check current policy
Get-ExecutionPolicy

# Allow scripts for current user only
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Or run PowerShell as Administrator and set for all users
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned
```

### Using the Right Python

Always ensure you're using the virtual environment's Python:

```bash
# These should point to .venv directory
which python      # Mac/Linux
where python      # Windows
which pip        # Mac/Linux
where pip        # Windows
```

### IDE Integration

#### VS Code
1. Open Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`)
2. Type "Python: Select Interpreter"
3. Choose the interpreter from `.venv` folder

#### PyCharm
1. File → Settings (or PyCharm → Preferences on Mac)
2. Project → Python Interpreter
3. Click gear icon → Add
4. Choose "Existing environment"
5. Browse to `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` (Mac/Linux)

#### Jupyter Notebooks
```bash
# Install ipykernel in your virtual environment
pip install ipykernel

# Add virtual environment to Jupyter
python -m ipykernel install --user --name=sparkbot --display-name="SparkBot (.venv)"
```

## Best Practices

1. **Always use virtual environments** for Python projects
2. **Name consistently**: Use `.venv` or `venv` as the folder name
3. **Don't commit**: Add `.venv/` to your `.gitignore`
4. **Document requirements**: Keep `requirements.txt` updated
5. **One per project**: Each project should have its own virtual environment
6. **Activate before work**: Always activate before installing packages or running code

## Why Use Virtual Environments?

- **Isolation**: Keep project dependencies separate
- **Reproducibility**: Others can recreate your exact environment
- **Cleanliness**: Don't pollute your system Python
- **Version Management**: Different projects can use different package versions
- **Easy Cleanup**: Just delete the `.venv` folder to remove all packages

## Additional Resources

- [Python venv documentation](https://docs.python.org/3/library/venv.html)
- [Real Python Virtual Environments Guide](https://realpython.com/python-virtual-environments-a-primer/)
- [pip documentation](https://pip.pypa.io/en/stable/)