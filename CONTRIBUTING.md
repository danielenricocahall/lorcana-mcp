# Contributing

Contributions are always welcome!

## Reporting Issues & Feature Requests

Before submitting a new issue, please check the existing issues to avoid duplicates. We have predefined templates to help categorize things efficiently:

- 🐞 **Bug Report** – Provide clear reproduction steps and expected behavior.
- 🚀 **Feature Request** – Suggest new functionality with a clear use case.
- 📖 **Documentation Request** – Report missing or unclear documentation.

Open an issue from the [Issues Page](https://github.com/danielenricocahall/lorcana-mcp/issues/new/choose).

## Local Environment Setup

[Fork the repository](https://github.com/danielenricocahall/lorcana-mcp/fork) and clone your fork, then create your environment with `uv`:

```shell
uv sync --dev
```

Install the `pre-commit` hook (uses `ruff` for linting and formatting):

```shell
uv run pre-commit install
```

## Unit Testing

`pytest` is used for all unit testing:

```shell
uv run pytest tests
```

Tests are executed as part of CI on every push and should behave consistently with local runs.

## Testing the MCP Server Locally

For architectural changes — especially anything touching the repository, data loading, or tool definitions — it's worth testing the server end-to-end in Claude Desktop or another MCP client before opening a PR.

**Running the server directly:**

```shell
uv run python -m lorcana_mcp
```

**Registering with Claude Desktop** — add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "lorcana-mcp": {
      "command": "uv",
      "args": ["run", "python", "-m", "lorcana_mcp"],
      "cwd": "/path/to/lorcana-mcp"
    }
  }
}
```

**Things worth verifying manually for architectural changes:**

- `resolve_card` returns the correct card as the top result for informal names (e.g. "Maui Half Shark", "Madam Mim Snake")
- `search_cards` filters, pagination, and sorting work as expected
- `aggregate_cards` returns correct counts for valid fields and a clear error for invalid ones
- The server starts correctly from both a cold state (no `cards.db`) and a warm state (cached DB)
- If you change the database schema, delete `cards.db` before testing — `CREATE TABLE IF NOT EXISTS` will not apply schema changes to an existing database
