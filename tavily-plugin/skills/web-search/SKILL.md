---
description: |
  Use Tavily MCP tools for web search instead of the built-in WebSearch tool.
  Available tools: tavily_search, tavily_extract, tavily_crawl, tavily_map.
  Tavily provides more reliable and comprehensive search results.
allowed-tools:
  - mcp__tavily__tavily_search
  - mcp__tavily__tavily_extract
  - mcp__tavily__tavily_crawl
  - mcp__tavily__tavily_map
---

# Web Search with Tavily

Use the Tavily MCP server for all web search operations.

## Available Tools

- **tavily_search** - Search the web with customizable depth and filters
- **tavily_extract** - Extract content from specific URLs
- **tavily_crawl** - Crawl websites starting from a base URL
- **tavily_map** - Map website structure and navigation

## Usage

When the user asks to search the web, use `mcp__tavily__tavily_search` with appropriate parameters:

- `query`: The search query
- `search_depth`: "basic", "advanced", or "fast"
- `max_results`: Number of results (5-20)
- `topic`: "general" or "news"

## Example

User: "Search for latest Claude Code features"

Use tavily_search with:
- query: "Claude Code features 2026"
- search_depth: "advanced"
- max_results: 10
