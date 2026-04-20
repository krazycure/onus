#!/usr/bin/env bash
# Install Onus custom interface into an existing ACE-Step 1.5 install.
# Usage: ./install.sh [/path/to/ACE-Step-1.5]

set -euo pipefail

TARGET="${1:-$(pwd)}"

if [[ ! -d "$TARGET/acestep" ]]; then
    echo "Error: '$TARGET' does not look like an ACE-Step install (missing acestep/ directory)" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing Onus custom interface into $TARGET ..."

# Copy modified upstream modules
for f in constants.py inference.py llm_inference.py; do
    cp -f "$SCRIPT_DIR/acestep/$f" "$TARGET/acestep/$f"
    echo "  -> acestep/$f"
done

# Copy all custom interface files
for f in "$SCRIPT_DIR"/acestep/ui/custom_interface*.py; do
    cp -f "$f" "$TARGET/$(basename $f)"
    echo "  -> $(basename $f)"
done

echo ""
echo "Done. Start with:"
echo "  cd '$TARGET' && uv sync && uv run acestep-custom --port 8090"
