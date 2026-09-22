# KYC-Bench server

A small backend so the KYC-Bench toolkit's "Assess" tab can call Claude
without ever exposing an API key in the browser, and without the page
showing that it's Claude under the hood.

## Endpoints

| Method | Path | What it does |
|---|---|---|
| GET | `/health` | Returns `{"ok": true}` — use this to confirm the server is up. |
| POST | `/review` | Runs a case through the active policy and scores it. Body: `{"case_id": "onb-ind-001"}` for a built-in demo case, or `{"brief": "free text case description"}` for anything else. |
| GET | `/policy` | The currently active policy's text and version info. |
| GET | `/policy/versions` | The full history of uploaded policy versions. |
| POST | `/policy` | Upload a new policy version, which becomes active immediately. Body: `{"text": "...", "title": "My Bank Policy v2"}`. Requires header `X-Admin-Key: <your ADMIN_KEY>`. |
| POST | `/policy/activate/<version_id>` | Roll back to an earlier uploaded version. Requires `X-Admin-Key`. |

## Run it locally

```bash
cd kyc-bench-server
pip install -r requirements.txt
cp .env.example .env
# edit .env: put your real Anthropic API key in ANTHROPIC_API_KEY,
# and pick your own long random string for ADMIN_KEY
python app.py
```

It starts on `http://localhost:5000`.

## Deploy it (Render, free tier)

1. Push this folder to a GitHub repo (or a `server/` folder inside `kyc-bench`).
2. On [render.com](https://render.com), New → Web Service → connect the repo.
3. Build command: `pip install -r requirements.txt`. Start command: `gunicorn app:app`.
4. Under Environment, add `ANTHROPIC_API_KEY`, `ADMIN_KEY`, and `ALLOWED_ORIGINS` (your GitHub Pages URL, e.g. `https://dipina1502innovator.github.io`).
5. Deploy. Render gives you a URL like `https://kyc-bench-server.onrender.com`.
6. In the toolkit's HTML file, set `API_BASE` (near the top of the `<script>`) to that URL.

Railway, Fly.io and Vercel (with a Python runtime) work the same way — the only Render-specific part is the exact dashboard steps.

## How to swap in a real policy

Once deployed, upload a bank's real policy with:

```bash
curl -X POST https://your-server-url/policy \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: <your ADMIN_KEY>" \
  -d '{"title": "Acme Bank KYC Policy v3", "text": "...the full policy text..."}'
```

Every case reviewed after that uses the new policy. The old version stays in `/policy/versions` and can be reactivated with `/policy/activate/<id>` if needed — nothing is overwritten.

## What this is not, yet

- **No real authentication** — `X-Admin-Key` is a single shared secret, fine for one admin, not for a real team. A production deployment would want proper user accounts.
- **No retrieval** — the whole policy text goes into every prompt. Fine for a short policy; a real bank's 100+ page manual should be chunked and retrieved (a vector database) rather than pasted whole.
- **File storage is a flat JSON file** — fine for a demo, replace with a real database before this holds anything sensitive.
- **`/review`'s custom `brief` path is unscored** — only the two built-in demo cases have ground truth to score against. A real deployment would score against the bank's actual case queue and its own ground truth or reviewer sign-off.

## Security note

Everything in `cases/`, `answers/` and the seeded demo policy in this repo is synthetic. Never commit a real `.env` file, a real API key, or a real bank's policy document to a public repository.
