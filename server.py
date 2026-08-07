"""Wedding invitation site: static pages + RSVP API."""

import html
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

import httpx2
import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator

load_dotenv()

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RSVP_FILE = DATA_DIR / "rsvp.json"
CONFIG_FILE = ROOT / "config.yaml"

TELEGRAM_TOKEN = os.getenv("TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("CHAT_ID", "").strip()

logger = logging.getLogger("wedding")

app = FastAPI(title="Wedding Invitation", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
templates = Jinja2Templates(directory=ROOT / "templates")

_config_cache: dict[str, Any] | None = None
_config_mtime: float | None = None


def load_config() -> dict[str, Any]:
    """Load config.yaml, re-reading when the file changes."""
    global _config_cache, _config_mtime
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Config not found: {CONFIG_FILE}")
    mtime = CONFIG_FILE.stat().st_mtime
    if _config_cache is not None and _config_mtime == mtime:
        return _config_cache
    with CONFIG_FILE.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("config.yaml must contain a top-level object")
    _config_cache = data
    _config_mtime = mtime
    return data


class RsvpIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    guests: int = Field(ge=1, le=20)
    attendance: Literal["yes", "no"]
    message: str = Field(default="", max_length=1000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        cleaned = re.sub(r"\s+", " ", v.strip())
        if not cleaned:
            raise ValueError("Имя обязательно")
        return cleaned

    @field_validator("message")
    @classmethod
    def clean_message(cls, v: str) -> str:
        return v.strip()


def _load_rsvps() -> list[dict]:
    if not RSVP_FILE.exists():
        return []
    try:
        return json.loads(RSVP_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _save_rsvp(entry: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    records = _load_rsvps()
    records.append(entry)
    RSVP_FILE.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _format_created_at(raw: str) -> str:
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local = dt.astimezone(ZoneInfo("Europe/Moscow"))
        return local.strftime("%d.%m.%Y %H:%M")  # 07.08.2026 11:35
    except (TypeError, ValueError):
        return raw or "—"


def _format_rsvp_telegram(entry: dict) -> str:
    coming = entry.get("attendance") == "yes"
    status = "Придёт" if coming else "Не сможет"
    message = entry.get("message") or "—"
    created = entry.get("created_at", "—")

    return (
        "<b>Новый ответ RSVP</b>\n\n"
        f"<b>Имя:</b> {html.escape(str(entry.get('name', '—')))}\n"
        f"<b>Присутствие:</b> {status}\n"
        f"<b>Гостей:</b> {entry.get('guests', '—')}\n"
        f"<b>Пожелание:</b> {html.escape(str(message))}\n"
        f"<b>Время (МСК):</b> {_format_created_at(str(created))}"
    )


async def _notify_telegram(entry: dict) -> None:
    """Best-effort Telegram notify; failures must not break RSVP."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("TOKEN/CHAT_ID not set — skipping Telegram notification")
        return
    if TELEGRAM_TOKEN == "CHANGE_ME" or TELEGRAM_CHAT_ID == "CHANGE_ME":
        logger.warning("TOKEN/CHAT_ID still placeholders — skipping Telegram notification")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": _format_rsvp_telegram(entry),
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        async with httpx2.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, json=payload)
            res.raise_for_status()
            data = res.json()
            if not data.get("ok"):
                logger.error("Telegram API returned an error: %s", data)
    except Exception:
        logger.exception("Failed to send Telegram notification")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    try:
        cfg = load_config()
    except (OSError, ValueError, yaml.YAMLError) as exc:
        raise HTTPException(status_code=500, detail=f"Ошибка конфига: {exc}") from exc
    return templates.TemplateResponse(
        request,
        "index.html",
        {"c": cfg},
    )


@app.post("/api/rsvp")
async def create_rsvp(payload: RsvpIn) -> dict:
    entry = {
        **payload.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        _save_rsvp(entry)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Не удалось сохранить ответ") from exc

    await _notify_telegram(entry)
    return {"ok": True}


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
