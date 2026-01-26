# Python LSP Plugin for Claude Code

Python language server integration using Pyright for code intelligence.

## Features

- Type checking and diagnostics
- Go to definition
- Hover information
- Code completion suggestions
- Find references

## Prerequisites

Install Pyright language server before using this plugin.

### macOS

```bash
# Using Homebrew
brew install pyright

# Or using pip
pip install pyright

# Or using npm
npm install -g pyright
```

### Linux

```bash
# Using pip
pip install pyright

# Or using npm
npm install -g pyright

# Arch Linux
sudo pacman -S pyright
```

### Windows

```powershell
# Using pip
pip install pyright

# Or using npm
npm install -g pyright

# Or using winget
winget install pyright
```

## Installation

### Local Development

```bash
claude --plugin-dir /path/to/lsp-python-plugin
```

### From Marketplace

```bash
/plugin marketplace add your-username/your-marketplace
/plugin install lsp-python
```

## Supported File Extensions

- `.py` - Python source files
- `.pyi` - Python stub files

## License

MIT
