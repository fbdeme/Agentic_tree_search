#!/bin/bash
# OpenPencil MCP setup script for Claude Code
# Usage: bash design/setup_mcp.sh

set -e

echo "=== OpenPencil MCP Setup ==="

# 1. Check bun
if ! command -v bun &> /dev/null; then
    echo "[1/4] Installing bun..."
    curl -fsSL https://bun.sh/install | bash
    export PATH="$HOME/.bun/bin:$PATH"
else
    echo "[1/4] bun found: $(bun --version)"
fi

# 2. Create local MCP workspace
MCP_DIR="$HOME/.openpencil-mcp"
echo "[2/4] Setting up MCP at $MCP_DIR..."

mkdir -p "$MCP_DIR"
cd "$MCP_DIR"

# Init and install
if [ ! -f package.json ]; then
    bun init -y > /dev/null 2>&1
fi
bun add @open-pencil/mcp > /dev/null 2>&1
echo "  Installed @open-pencil/mcp"

# 3. Patch missing exports in @open-pencil/core
echo "[3/4] Patching @open-pencil/core exports..."
python3 -c "
import json, os

core_src = 'node_modules/@open-pencil/core/src'

def find_all_modules(base, prefix=''):
    results = []
    for item in sorted(os.listdir(base)):
        path = os.path.join(base, item)
        if os.path.isfile(path) and item.endswith('.ts') and not item.startswith('global'):
            name = item.replace('.ts', '')
            key = f'./{prefix}{name}' if prefix else f'./{name}'
            results.append((key, f'./src/{prefix}{name}.ts'))
        elif os.path.isdir(path) and not item.startswith('.'):
            idx = os.path.join(path, 'index.ts')
            key = f'./{prefix}{item}'
            if os.path.exists(idx):
                results.append((key, f'./src/{prefix}{item}/index.ts'))
            results.extend(find_all_modules(path, f'{prefix}{item}/'))
    return results

with open('node_modules/@open-pencil/core/package.json') as f:
    pkg = json.load(f)

exports = pkg['exports']
added = 0
for key, path in find_all_modules(core_src):
    if key not in exports:
        exports[key] = {'types': path, 'bun': path, 'default': path}
        added += 1

with open('node_modules/@open-pencil/core/package.json', 'w') as f:
    json.dump(pkg, f, indent=2)

print(f'  Patched {added} missing exports')
"

# 4. Register with Claude Code
echo "[4/4] Registering MCP with Claude Code..."
MCP_ENTRY="$MCP_DIR/node_modules/@open-pencil/mcp/dist/index.js"
BUN_PATH="$(which bun)"

# Remove existing if any
claude mcp remove open-pencil 2>/dev/null || true

claude mcp add --transport stdio open-pencil -- "$BUN_PATH" "$MCP_ENTRY"

echo ""
echo "=== Setup complete! ==="
echo "Restart Claude Code to use OpenPencil MCP."
echo "Available tools: create_shape, set_fill, open_file, save_file, export, etc. (90+ tools)"
