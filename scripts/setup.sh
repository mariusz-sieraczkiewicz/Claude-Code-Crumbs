#!/bin/bash
set -e

echo "Installing Python and Node.js..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip nodejs npm

echo "Installing uv/uvx..."
curl -LsSf https://astral.sh/uv/install.sh | sh

echo ""
echo "Installation complete!"
echo "Python: $(python3 --version)"
echo "pip: $(pip3 --version)"
echo "Node.js: $(node --version)"
echo "npm: $(npm --version)"
echo "uv: $($HOME/.local/bin/uv --version)"
echo "uvx: $($HOME/.local/bin/uvx --version)"
