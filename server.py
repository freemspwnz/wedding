"""Свадебная визитка: статика + API для RSVP."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RSVP_FILE = DATA_DIR / "rsvp.json"
CONFIG_FILE = ROOT / "config.yaml"

app = FastAPI(title="Wedding Invitation", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
templates = Jinja2Templates(directory=ROOT / "templates")

_config_cache: dict[str, Any] | None = None
_config_mtime: float | None = None


def load_config() -> dict[str, Any]:
    """Читает config.yaml, перечитывает при изменении файла."""
    global _config_cache, _config_mtime
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Конфиг не найден: {CONFIG_FILE}")
    mtime = CONFIG_FILE.stat().st_mtime
    if _config_cache is not None and _config_mtime == mtime:
        return _config_cache
    with CONFIG_FILE.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("config.yaml должен содержать объект верхнего уровня")
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
    return {"ok": True}


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
