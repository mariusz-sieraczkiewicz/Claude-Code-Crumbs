# Tavily Plugin for Claude Code

Tavily AI search integration providing web search, content extraction, crawling, and site mapping capabilities.

## Features

This plugin adds the following MCP tools to Claude Code:

- **tavily_search** - Powerful web search with customizable parameters
- **tavily_extract** - Extract content from URLs
- **tavily_crawl** - Crawl websites starting from a base URL
- **tavily_map** - Map website structure and navigation paths

## Prerequisites

You need a Tavily API key. Get one at [tavily.com](https://tavily.com).

Set the environment variable before running Claude Code:

```bash
export TAVILY_API_KEY="your-api-key-here"
```

## Installation

### Local Development

```bash
claude --plugin-dir /path/to/tavily-plugin
```

### From Marketplace

If published to a marketplace:

```bash
/plugin marketplace add your-username/your-marketplace
/plugin install tavily
```

### Manual Configuration

Add to your `.claude/settings.json`:

```json
{
  "plugins": {
    "enabled": ["tavily@your-marketplace"]
  }
}
```

## Usage Examples

Once installed, Claude can use Tavily tools automatically. Examples:

- "Search the web for latest React 19 features"
- "Extract content from this URL: https://example.com/article"
- "Crawl the documentation site at https://docs.example.com"
- "Map the structure of https://example.com"

## Plugin Structure

```
tavily-plugin/
├── .claude-plugin/
│   └── plugin.json    # Plugin manifest
├── .mcp.json          # MCP server configuration
└── README.md          # This file
```

## License

MIT
