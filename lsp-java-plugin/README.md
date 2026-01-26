# Java LSP Plugin for Claude Code

Java language server integration using Eclipse JDT Language Server for code intelligence.

## Features

- Syntax and semantic diagnostics
- Go to definition
- Hover information
- Code completion
- Find references
- Code actions and refactoring

## Prerequisites

Install Eclipse JDT Language Server before using this plugin.

### macOS

```bash
# Using Homebrew
brew install jdtls
```

### Linux

```bash
# Arch Linux
sudo pacman -S jdtls

# Ubuntu/Debian - manual installation
# 1. Download from https://github.com/eclipse-jdtls/eclipse.jdt.ls/releases
# 2. Extract to /opt/jdtls
# 3. Add to PATH:
echo 'export PATH="/opt/jdtls/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Using SDKMAN
sdk install jdtls
```

### Windows

```powershell
# Using Scoop
scoop bucket add extras
scoop install jdtls

# Manual installation
# 1. Download from https://github.com/eclipse-jdtls/eclipse.jdt.ls/releases
# 2. Extract to C:\tools\jdtls
# 3. Add C:\tools\jdtls\bin to PATH
```

### Alternative: VS Code Java Extension

If you have VS Code with the Java extension pack installed, jdtls is bundled at:
- macOS/Linux: `~/.vscode/extensions/redhat.java-*/server/`
- Windows: `%USERPROFILE%\.vscode\extensions\redhat.java-*\server\`

## Installation

### Local Development

```bash
claude --plugin-dir /path/to/lsp-java-plugin
```

### From Marketplace

```bash
/plugin marketplace add your-username/your-marketplace
/plugin install lsp-java
```

## Supported File Extensions

- `.java` - Java source files

## License

MIT
