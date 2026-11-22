#!/bin/bash
# Double-click (Mac) or run `./start.command` to open the Off-Grid Library builder.
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "First run: setting up Python environment…"
  python3 -m venv .venv && .venv/bin/pip install -q --upgrade pip && .venv/bin/pip install -q -r requirements.txt || exit 1
fi
exec .venv/bin/python offgrid.py "$@"
