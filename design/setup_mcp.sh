#!/bin/bash
# OpenPencil MCP setup script for Claude Code
# Usage: bash design/setup_mcp.sh
#
# This script:
# 1. Installs bun (if missing)
# 2. Installs @open-pencil/mcp in ~/.openpencil-mcp
# 3. Patches missing exports in @open-pencil/core
# 4. Starts MCP HTTP server on port 7600
# 5. Registers with Claude Code (HTTP transport)

set -e

MCP_DIR="$HOME/.openpencil-mcp"
MCP_PORT=7600
MCP_WS_PORT=7601

echo "=== OpenPencil MCP Setup ==="

# 1. Check bun
if ! command -v bun &> /dev/null; then
    echo "[1/5] Installing bun..."
    curl -fsSL https://bun.sh/install | bash
    export PATH="$HOME/.bun/bin:$PATH"
else
    echo "[1/5] bun found: $(bun --version)"
fi

# 2. Create local MCP workspace
echo "[2/5] Setting up MCP at $MCP_DIR..."

mkdir -p "$MCP_DIR"
cd "$MCP_DIR"

# Init and install
if [ ! -f package.json ]; then
    bun init -y > /dev/null 2>&1
fi
bun add @open-pencil/mcp > /dev/null 2>&1
echo "  Installed @open-pencil/mcp"

# 3. Patch missing exports in @open-pencil/core
echo "[3/5] Patching @open-pencil/core exports..."
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

# 4. Start MCP server (kill existing if running)
echo "[4/5] Starting MCP server on port $MCP_PORT..."
lsof -ti:$MCP_PORT,$MCP_WS_PORT 2>/dev/null | xargs -r kill -9 2>/dev/null || true
sleep 1

BUN_PATH="$(which bun)"
MCP_ENTRY="$MCP_DIR/node_modules/@open-pencil/mcp/dist/index.js"
nohup "$BUN_PATH" "$MCP_ENTRY" > /tmp/openpencil-mcp.log 2>&1 &
MCP_PID=$!
sleep 2

if kill -0 $MCP_PID 2>/dev/null; then
    echo "  MCP server running (PID: $MCP_PID)"
    echo "  HTTP: http://127.0.0.1:$MCP_PORT"
    echo "  MCP:  http://127.0.0.1:$MCP_PORT/mcp"
else
    echo "  ERROR: MCP server failed to start. Check /tmp/openpencil-mcp.log"
    exit 1
fi

# 5. Register with Claude Code (HTTP transport)
echo "[5/5] Registering MCP with Claude Code..."
claude mcp remove open-pencil 2>/dev/null || true
claude mcp add --transport http open-pencil "http://127.0.0.1:$MCP_PORT/mcp"

echo ""
echo "=== Setup complete! ==="
echo ""
echo "MCP server is running in background."
echo "Restart Claude Code to use OpenPencil MCP (90+ design tools)."
echo ""
echo "To stop the server:  kill $MCP_PID"
echo "To check logs:       cat /tmp/openpencil-mcp.log"
echo "To restart server:   bash design/setup_mcp.sh"
