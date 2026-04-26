# data_pipeline

Out-of-band data fetcher. This code is **not** shipped in the runtime
Docker image — it runs only as a scheduled GitHub Actions job (see
`.github/workflows/fetch-cards.yml`) and writes its output to the
`gh-pages` branch, which the running container fetches over HTTPS at
startup.

## What it does

`fetch_cards.py` calls the [Lorcast API](https://lorcast.com/) once per
set, normalizes each card into our internal schema, and writes a flat
JSON list to disk. The runtime then `requests.get` + `.json()` and
loads the list straight into memory — no schema mapping happens at
runtime.

Lorcast is public and unauthenticated; the only caller-side concern is
politeness, so the script paces requests at ~120ms apart and retries
on 429 / 5xx responses.

Run locally:

```sh
uv run python data_pipeline/fetch_cards.py allCards.json
```

## Why this layer exists

The middle layer (gh-pages CDN between Lorcast and the running
container) buys two things:

- **Resilience for first-time pulls.** If Lorcast is down or has a
  breaking schema change, the gh-pages snapshot keeps serving
  last-known-good data; new container starts succeed even while the
  upstream is broken. Recovery is async on our side.
- **Lorcast rate-limit insulation.** Many MCP clients pulling once per
  day from gh-pages CDN ≪ many MCP clients pulling on every cold
  start from Lorcast directly.

## Credits

Schema and request patterns adapted from the public
[Lorcast API documentation](https://lorcast.com/api). Lorcast itself
is a third-party project — please be a good API citizen if you're
running this script outside of CI.
