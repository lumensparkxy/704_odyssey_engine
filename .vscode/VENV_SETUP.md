# VS Code Virtual Environment Auto-Activation

This workspace is configured to automatically activate the Python virtual environment (`.venv`) whenever you open a new terminal in VS Code.

## What's been configured:

### 1. VS Code Settings (`.vscode/settings.json`)
- **Default Terminal Profile**: Set to "Python (.venv)" which automatically activates the virtual environment
- **Python Interpreter**: Points to `./.venv/bin/python`
- **Environment Variables**: `PYTHONPATH` is set to include `src/` directory
- **Python Analysis**: Configured to find modules in `src/`
- **Code Formatting**: Black formatter enabled
- **Testing**: pytest integration enabled

### 2. Custom Activation Script (`.vscode/activate_env.sh`)
- Checks if virtual environment is already active
- Activates `.venv` if not already active
- Sets up `PYTHONPATH` correctly
- Provides helpful information about available commands

### 3. Launch Configuration (`.vscode/launch.json`)
- Debug configurations for main application and tests
- Uses the virtual environment Python interpreter
- Sets correct environment variables

### 4. Tasks Configuration (`.vscode/tasks.json`)
- Updated to use virtual environment for pip and python commands
- Proper environment variable setup

## How it works:

1. **New Terminal**: When you open a new terminal (Ctrl/Cmd + `), it automatically:
   - Activates the `.venv` virtual environment
   - Sets up the Python path
   - Shows helpful information

2. **Python Commands**: All Python-related tasks and debugging use the virtual environment

3. **Code Intelligence**: VS Code's Python extension uses the virtual environment for:
   - Code completion
   - Error checking
   - Import resolution

## Available Commands (once activated):

- `odyssey` - Run the Odyssey Engine CLI
- `python main.py` - Run the main application  
- `pytest` - Run tests
- `pip list` - Show installed packages
- `python --version` - Check Python version

## Troubleshooting:

If the virtual environment doesn't activate automatically:

1. **Reload VS Code**: Close and reopen VS Code
2. **Check Terminal Profile**: In terminal, click the dropdown next to "+" and select "Python (.venv)"
3. **Manual Activation**: Run `source .venv/bin/activate` in any terminal
4. **Recreate Environment**: If `.venv` is missing, run `python3 -m venv .venv` then `source .venv/bin/activate && pip install -r requirements.txt`

## Files Modified:

- `.vscode/settings.json` - VS Code workspace settings
- `.vscode/launch.json` - Debug configurations  
- `.vscode/tasks.json` - Build tasks
- `.vscode/activate_env.sh` - Custom activation script
- `.vscode/VENV_SETUP.md` - This documentation

All terminal sessions in this workspace will now automatically use the virtual environment!
