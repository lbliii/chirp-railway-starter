# Launch Board

**Python + HTMX Full-Stack Starter — powered by Chirp**

Launch Board is a small app with real production seams: server-rendered HTML,
HTMX fragments, out-of-band progress updates, SSE live status, protected forms,
signed sessions, and Railway health checks. It deploys as one service and asks
the user for no configuration.

## Deploy

The Railway marketplace link will appear here after the first template version
is published. The template creates `CHIRP_SECRET_KEY`, sets
`CHIRP_ENV=production`, and uses Railway's supplied `PORT` automatically.

## Run locally

```bash
uv sync
uv run python app.py
```

Open <http://127.0.0.1:8000>. Production and Railway use the same `python app.py`
entrypoint.

## What this proves

- One Jinja-compatible template supplies the full page, HTMX board fragment,
  OOB progress/notice regions, and SSE payload.
- Every mutation remains a normal POST form when JavaScript is unavailable.
- The checklist is bounded and stored in a signed per-browser cookie. It is a
  deliberate zero-database demo, not shared or durable persistence.
- The starter explicitly runs one application worker to stay cost-bounded on
  Railway while Chirp tracks quota-aware auto-detection in `lbliii/chirp#750`.
- `/health` and `/ready` are Chirp's built-in liveness/readiness endpoints.
- `railway-template.json` drives reusable local and deployed conformance checks.

## Customize

Start in `templates/index.html` for the interface, `styles.css` for the visual
system, and `app.py` for routes and state. Replace the signed-session functions
with a database repository when the app needs shared persistence.

## License

MIT
