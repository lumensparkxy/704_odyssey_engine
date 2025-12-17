#!/bin/bash

# Compatibility wrapper (deprecated).
# The setup script was moved into scripts/ to reduce repository-root clutter.

set -euo pipefail

exec "$(dirname "$0")/scripts/setup.sh" "$@"
