# TypeScript LSP Plugin for Claude Code

TypeScript and JavaScript language server integration for code intelligence.

## Features

- Type checking and diagnostics
- Go to definition
- Hover information
- Code completion
- Find references
- Rename symbol
- Code actions

## Prerequisites

Install TypeScript Language Server before using this plugin. Requires Node.js.

### macOS

```bash
# Using npm
npm install -g typescript-language-server typescript

# Using Homebrew (Node.js)
brew install node
npm install -g typescript-language-server typescript
```

### Linux

```bash
# Using npm
npm install -g typescript-language-server typescript

# Arch Linux
sudo pacman -S typescript-language-server

# Ubuntu/Debian - install Node.js first
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs
npm install -g typescript-language-server typescript
```

### Windows

```powershell
# Using npm (requires Node.js)
npm install -g typescript-language-server typescript

# Install Node.js first if needed
# Download from https://nodejs.org or use winget:
winget install OpenJS.NodeJS.LTS
npm install -g typescript-language-server typescript

# Using Scoop
scoop install nodejs
npm install -g typescript-language-server typescript
```

## Installation

### Local Development

```bash
claude --plugin-dir /path/to/lsp-typescript-plugin
```

### From Marketplace

```bash
/plugin marketplace add your-username/your-marketplace
/plugin install lsp-typescript
```

## Supported File Extensions

- `.ts` - TypeScript
- `.tsx` - TypeScript React
- `.js` - JavaScript
- `.jsx` - JavaScript React
- `.mjs` - ES modules
- `.mts` - TypeScript ES modules

## License

MIT
