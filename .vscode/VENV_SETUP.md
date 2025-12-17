# VS Code Setup for Odyssey Engine

This workspace is configured for automatic Python virtual environment activation.

## Quick Start

1. **Open VS Code** in this folder
2. **Open a terminal** (Ctrl/Cmd + `) - venv activates automatically
3. **Run the app**: `python main.py` or `odyssey`

## What's Configured

| File | Purpose |
|------|---------|
| `settings.json` | Python interpreter, PYTHONPATH, formatter |
| `launch.json` | Debug configurations |
| `tasks.json` | Run/test tasks |
| `activate_env.sh` | Auto-activation script |

## Available Commands

```bash
# Run research engine
python main.py
odyssey

# Run with query
odyssey -q "your research query"

# Run tests
pytest
pytest -v tests/
```

## Troubleshooting

If venv doesn't activate automatically:

```bash
# Manual activation
source .venv/bin/activate

# Or recreate environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Debug Configurations

- **Odyssey Engine**: Launch `main.py` with debugger
- **Run Tests**: Debug pytest tests
