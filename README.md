# ravelry-mcp

An MCP server that connects Claude to the [Ravelry](https://www.ravelry.com) API, letting knitters and crocheters search for patterns, find yarn, and calculate how much to buy — all through natural language without leaving their workflow.

## Tools

| Tool | Description |
|------|-------------|
| `search_patterns` | Search Ravelry patterns by keyword, craft, yarn weight, difficulty, and price |
| `get_pattern_details` | Fetch full details for a pattern including yardage, gauge, sizes, and a direct link |
| `search_yarn` | Search the Ravelry yarn database by name, brand, weight, or fiber content |
| `calculate_yarn_needed` | Calculate how many skeins of a specific yarn are needed for a pattern, with a buffer |

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- A [Ravelry developer account](https://www.ravelry.com/pro/developer) with a personal app (for Basic Auth credentials)

## Setup

```bash
git clone https://github.com/yourname/ravelry-mcp.git
cd ravelry-mcp
uv pip install -e .
cp .env.example .env
```

Edit `.env` with your Ravelry credentials:

```
RAVELRY_USERNAME=your_username
RAVELRY_PASSWORD=your_personal_auth_token
```

> **Note:** v0 only needs Basic Auth read-only access. On Ravelry, go to Pro → Apps → Create a personal app — this gives you a username and password token with no OAuth setup required.

## Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ravelry": {
      "command": "uv",
      "args": ["run", "ravelry-mcp"],
      "cwd": "/path/to/ravelry-mcp"
    }
  }
}
```

## Development

Run the MCP inspector to test tools interactively:

```bash
uv run mcp dev src/ravelry_mcp/server.py:mcp
```

## Roadmap

The following features require OAuth (user-level access) rather than Basic Auth:

- **Stash matching** — search a user's yarn stash against a pattern's requirements
- **Queue access** — read and manage a user's pattern queue
- **Project progress tracker** — log and update in-progress knitting projects
