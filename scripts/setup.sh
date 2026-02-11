#!/bin/bash
set -e

export NODE_USE_SYSTEM_CA=1

echo "Installing Python and Node.js..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-certifi ca-certificates nodejs npm

echo "Installing uv/uvx..."
curl -LsSf https://astral.sh/uv/install.sh | sh

echo "Installing pip-system-certs..."
pip3 install --break-system-packages pip-system-certs

echo "Creating .mcp.json..."
cat > .mcp.json << 'EOF'
{
  "mcpServers": {
    "globaljira": {
      "command": "uvx",
      "args": [
        "mcp-atlassian"
      ],
      "env": {
        "JIRA_URL": "https://globaljira.roche.com",
        "JIRA_PERSONAL_TOKEN": "${JIRA_PERSONAL_TOKEN}",
        "JIRA_SSL_VERIFY": "false",
        "JIRA_READ_ONLY": "true"
      }
    },
    "tavily": {
      "command": "npx",
      "args": [
        "-y",
        "tavily-mcp@latest"
      ],
      "env": {
        "TAVILY_API_KEY": "${TAVILY_API_KEY}"
      }
    }
  }
}
EOF

echo ""
echo "Installation complete!"
echo "Python: $(python3 --version)"
echo "pip: $(pip3 --version)"
echo "Node.js: $(node --version)"
echo "npm: $(npm --version)"
echo "uv: $($HOME/.local/bin/uv --version)"
echo "uvx: $($HOME/.local/bin/uvx --version)"

claude --dangerously-skip-permissions
