# data_pipeline

Out-of-band data fetcher. This code is **not** shipped in the runtime
Docker image — it runs only as a scheduled GitHub Actions job (see
`.github/workflows/fetch-cards.yml`) and writes its output to the
`gh-pages` branch, which the running container fetches over HTTPS at
startup.

## What it does

`fetch_cards.py` calls the Ravensburger SSO endpoint to mint a short-lived
access token, then pulls the English card catalog from the official
Lorcana API. The Basic-auth client credential is read from the
`RAVENSBURGER_BASIC_AUTH` environment variable so it never lives in
source.

Run locally:

```sh
RAVENSBURGER_BASIC_AUTH=<base64-blob> uv run python data_pipeline/fetch_cards.py allCards.json
```

## Credits

The approach here — calling the Ravensburger SSO + catalog endpoints
exactly the way the official app does, with the same Unity user-agent
and headers — is derived from prior work by others. Specifically:

- **[lorcanajson](https://lorcanajson.org/)** — the project we
  previously consumed as a third-party data source. The
  `retrieveCardCatalog` flow (token request, auth header, catalog GET)
  in `fetch_cards.py` is adapted directly from the lorcanajson
  downloader.
- **[entchen66/LorcanaCardCollector](https://github.com/entchen66/LorcanaCardCollector)**
  — independent reference for the same API shape and request pattern.

Thanks to both projects for doing the legwork of figuring out how to
talk to the Ravensburger API. This pipeline exists so we can run on
our own cadence rather than depending on a third party, but the
request pattern itself is theirs.
