# Wedding Invitation

A self-hosted wedding invitation site with an RSVP API, YAML-driven content, optional Telegram notifications, and Docker/Traefik deployment.

## Features

- **SSR landing page** — FastAPI + Jinja2, content from `config.yaml` (hot-reloaded on file change)
- **RSVP form** — validates and stores guest responses in `data/rsvp.json`
- **Telegram alerts** — best-effort notify on new RSVPs (failures never block saving)
- **Responsive UI** — Tailwind CSS, sticky nav, scroll reveal, reduced-motion support
- **Production-ready** — Docker image, Compose + Traefik labels for HTTPS via Let’s Encrypt

## Stack

| Layer | Tech |
| --- | --- |
| Backend | Python 3.12, FastAPI, Uvicorn, Pydantic 2 |
| Templates / config | Jinja2, PyYAML |
| Frontend | Tailwind CSS (CDN), vanilla JS, custom CSS |
| Notifications | httpx2 → Telegram Bot API |
| Deploy | Docker, Docker Compose, Traefik |

## Quick start (local)

```bash
cp config.example.yaml config.yaml
cp .env.example .env   # optional: fill TOKEN / CHAT_ID for Telegram

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000](http://localhost:8000).

## Docker

```bash
cp config.example.yaml config.yaml
cp .env.example .env

docker compose up -d --build
```

- App listens on port **8000** inside the container
- Guest RSVPs persist in `./data` (bind-mounted)
- `config.yaml` is mounted read-only; edit it on the host without rebuilding

### Traefik

`docker-compose.yml` expects an external Traefik network named `traefik` and Let’s Encrypt via `certresolver=letsencrypt`. Change the host rule before deploy:

```yaml
- traefik.http.routers.wedding.rule=Host(`your-domain.example`)
```

## Configuration

All page copy lives in `config.yaml` (start from `config.example.yaml`). Sections include:

- `couple`, `date`, `venue`
- `hero`, `invite`, `timeline`
- `dress_code`, `closing`, `rsvp`

The server caches the file and reloads it when `mtime` changes — no container rebuild needed for text/date/image updates.

### Environment

| Variable | Required | Description |
| --- | --- | --- |
| `TOKEN` | No | Telegram bot token (`@BotFather`) |
| `CHAT_ID` | No | Chat/user id for RSVP notifications |

If `TOKEN` / `CHAT_ID` are missing or still `CHANGE_ME`, RSVPs are saved locally and Telegram is skipped.

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Invitation page |
| `POST` | `/api/rsvp` | Submit RSVP JSON body |
| `GET` | `/api/health` | Liveness check |

Example RSVP body:

```json
{
  "name": "Alex",
  "guests": 2,
  "attendance": "yes",
  "message": "Looking forward to it"
}
```

OpenAPI docs (`/docs`, `/redoc`) are disabled.

## Project layout

```
.
├── server.py              # FastAPI app
├── config.example.yaml    # Content template
├── templates/index.html   # Landing page
├── static/                # CSS, JS, images
├── data/                  # RSVP JSON (gitignored)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## License

[MIT](LICENSE) © 2026 Freems
