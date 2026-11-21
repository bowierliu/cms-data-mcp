#!/bin/sh
set -eu
cd "$(dirname "$0")"
PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
export PATH
if ! command -v uv >/dev/null 2>&1; then
    echo "Install uv from https://docs.astral.sh/uv/ and open this launcher again."
    exit 1
fi
exec uv run --locked python -m cms_mcp.recruiter --launch
