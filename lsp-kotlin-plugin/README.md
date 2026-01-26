# Kotlin LSP Plugin for Claude Code

Kotlin language server integration for code intelligence.

## Features

- Syntax and semantic diagnostics
- Go to definition
- Hover information
- Code completion
- Find references

## Prerequisites

Install Kotlin Language Server before using this plugin.

### macOS

```bash
# Using Homebrew
brew install kotlin-language-server
```

### Linux

```bash
# Arch Linux (AUR)
yay -S kotlin-language-server

# Ubuntu/Debian - manual installation
# 1. Download from https://github.com/fwcd/kotlin-language-server/releases
# 2. Extract to /opt/kotlin-language-server
# 3. Add to PATH:
sudo ln -s /opt/kotlin-language-server/server/bin/kotlin-language-server /usr/local/bin/

# Using SDKMAN (if available)
sdk install kls
```

### Windows

```powershell
# Using Scoop
scoop install kotlin-language-server

# Manual installation
# 1. Download from https://github.com/fwcd/kotlin-language-server/releases
# 2. Extract to C:\tools\kotlin-language-server
# 3. Add C:\tools\kotlin-language-server\server\bin to PATH
```

### Build from Source (All Platforms)

```bash
git clone https://github.com/fwcd/kotlin-language-server.git
cd kotlin-language-server
./gradlew :server:installDist
# Binary at server/build/install/server/bin/kotlin-language-server
```

## Installation

### Local Development

```bash
claude --plugin-dir /path/to/lsp-kotlin-plugin
```

### From Marketplace

```bash
/plugin marketplace add your-username/your-marketplace
/plugin install lsp-kotlin
```

## Supported File Extensions

- `.kt` - Kotlin source files
- `.kts` - Kotlin script files

## License

MIT
