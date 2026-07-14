"""Launch Board: a complete one-service Chirp starter for Railway."""

from __future__ import annotations

import asyncio
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from chirp import (
    OOB,
    App,
    AppConfig,
    EventStream,
    Fragment,
    MutationResult,
    Page,
    Request,
    Response,
)
from chirp.middleware.sessions import get_session
from chirp.middleware.stack import secure_stack

ROOT = Path(__file__).parent
MAX_ITEMS = 12
MAX_TITLE_LENGTH = 80
STARTED_AT = time.monotonic()
SEED_ITEMS = (
    {"id": 1, "title": "Deploy the starter", "done": True},
    {"id": 2, "title": "Make one tiny change", "done": False},
    {"id": 3, "title": "Ship your first Chirp app", "done": False},
)

config = AppConfig.from_env(template_dir=ROOT / "templates", worker_mode="async", htmx=True)
if not config.secret_key:
    if config.env != "development":
        raise RuntimeError("CHIRP_SECRET_KEY is required outside development")
    config = replace(config, secret_key="launch-board-local-development-only")
app = App(config)
for middleware in secure_stack(app.config):
    app.add_middleware(middleware)


def _items() -> list[dict[str, Any]]:
    """Return normalized, bounded session state or initialize the seed board."""

    session = get_session()
    raw = session.get("launch_board_items")
    if not isinstance(raw, list):
        items = [dict(item) for item in SEED_ITEMS]
        session["launch_board_items"] = items
        return items

    items: list[dict[str, Any]] = []
    for raw_item in raw[:MAX_ITEMS]:
        if not isinstance(raw_item, dict):
            continue
        item_id = raw_item.get("id")
        title = raw_item.get("title")
        done = raw_item.get("done")
        if isinstance(item_id, int) and isinstance(title, str) and isinstance(done, bool):
            clean_title = title.strip()[:MAX_TITLE_LENGTH]
            if clean_title:
                items.append({"id": item_id, "title": clean_title, "done": done})
    if not items:
        items = [dict(item) for item in SEED_ITEMS]
    if items != raw:
        session["launch_board_items"] = items
    return items


def _context(filter_name: str = "all", *, notice: str = "") -> dict[str, Any]:
    items = _items()
    selected = filter_name if filter_name in {"all", "active", "done"} else "all"
    visible = [
        item for item in items if selected == "all" or (selected == "done") is bool(item["done"])
    ]
    done_count = sum(bool(item["done"]) for item in items)
    return {
        "items": visible,
        "filter_name": selected,
        "done_count": done_count,
        "total_count": len(items),
        "percent": round(done_count / len(items) * 100) if items else 0,
        "notice": notice,
        "max_items": MAX_ITEMS,
    }


def _result(notice: str) -> MutationResult:
    context = _context(notice=notice)
    return MutationResult(
        "/",
        Fragment("index.html", "board", **context),
        Fragment("index.html", "progress", target="progress", **context),
        Fragment("index.html", "notice", target="notice", **context),
        trigger="boardChanged",
    )


@app.route("/", name="home")
def index(request: Request) -> Page | OOB:
    context = _context(request.query.get("filter", "all") or "all")
    if request.is_narrow_fragment:
        return OOB(
            Fragment("index.html", "board", **context),
            Fragment("index.html", "progress", target="progress", **context),
        )
    return Page("index.html", "board", page_block_name="page_root", **context)


@app.route("/items", methods=["POST"], name="items.add")
async def add_item(request: Request) -> MutationResult:
    form = await request.form()
    title = str(form.get("title") or "").strip()
    items = _items()
    if not title:
        return _result("Give the next step a short name.")
    if len(title) > MAX_TITLE_LENGTH:
        return _result(f"Keep the next step under {MAX_TITLE_LENGTH} characters.")
    if len(items) >= MAX_ITEMS:
        return _result(f"Launch Board stays focused at {MAX_ITEMS} items.")
    next_id = max((int(item["id"]) for item in items), default=0) + 1
    get_session()["launch_board_items"] = [
        *items,
        {"id": next_id, "title": title, "done": False},
    ]
    return _result(f"Added “{title}”.")


@app.route("/items/{item_id}/toggle", methods=["POST"], name="items.toggle")
def toggle_item(item_id: int) -> MutationResult:
    items = _items()
    changed = False
    updated: list[dict[str, Any]] = []
    for item in items:
        if item["id"] == item_id:
            updated.append({**item, "done": not item["done"]})
            changed = True
        else:
            updated.append(item)
    get_session()["launch_board_items"] = updated
    return _result("Progress saved." if changed else "That item is no longer on this board.")


@app.route("/reset", methods=["POST"], name="board.reset")
def reset_board() -> MutationResult:
    get_session()["launch_board_items"] = [dict(item) for item in SEED_ITEMS]
    return _result("Board reset to the guided launch path.")


@app.route("/events", referenced=True)
def events(request: Request) -> EventStream:
    async def stream():
        while True:
            elapsed = max(1, round(time.monotonic() - STARTED_AT))
            yield Fragment(
                "index.html",
                "live_status",
                target="live-status",
                elapsed=elapsed,
            )
            await asyncio.sleep(10)

    return EventStream(stream(), heartbeat_interval=15)


@app.route("/styles.css", referenced=True)
def styles(request: Request) -> Response:
    css = (ROOT / "styles.css").read_text(encoding="utf-8")
    return Response(css, content_type="text/css; charset=utf-8")


if __name__ == "__main__":
    app.run()
