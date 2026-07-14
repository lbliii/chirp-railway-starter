from __future__ import annotations

import re
from urllib.parse import urlencode

import pytest
from chirp.testing import TestClient

from app import app

pytestmark = pytest.mark.issue(738)
_CSRF_RE = re.compile(r'name="_csrf_token" value="([^"]+)"')


def _cookie(response) -> str:
    value = response.header("set-cookie", "")
    assert value.startswith("chirp_session=")
    return value.split(";", 1)[0]


async def _page_context(client: TestClient) -> tuple[str, str]:
    response = await client.get("/")
    match = _CSRF_RE.search(response.text)
    assert match is not None
    return match.group(1), _cookie(response)


async def test_full_page_health_and_asset_contracts() -> None:
    async with TestClient(app) as client:
        page = await client.get("/")
        health = await client.get("/health")
        ready = await client.get("/ready")
        css = await client.get("/styles.css")

    assert page.status == health.status == ready.status == css.status == 200
    assert "Launch Board" in page.text
    assert "Ship your first Chirp app" in page.text
    assert "--ink:" in css.text


async def test_htmx_filter_returns_board_and_oob_progress() -> None:
    async with TestClient(app) as client:
        response = await client.get(
            "/?filter=done",
            headers={"HX-Request": "true", "HX-Target": "board"},
        )

    assert response.status == 200
    assert 'id="board"' in response.text
    assert "Deploy the starter" in response.text
    assert "Make one tiny change" not in response.text
    assert 'id="progress"' in response.text
    assert "hx-swap-oob" in response.text


async def test_plain_and_htmx_form_mutations_share_the_session() -> None:
    async with TestClient(app) as client:
        token, cookie = await _page_context(client)
        body = urlencode({"title": "Invite the first tester", "_csrf_token": token}).encode()
        plain = await client.post(
            "/items",
            body=body,
            headers={"Content-Type": "application/x-www-form-urlencoded", "Cookie": cookie},
        )
        updated_cookie = plain.header("set-cookie", "").split(";", 1)[0] or cookie
        page = await client.get("/", headers={"Cookie": updated_cookie})

        token_match = _CSRF_RE.search(page.text)
        assert token_match is not None
        htmx = await client.post(
            "/items",
            body=urlencode(
                {"title": "Share the link", "_csrf_token": token_match.group(1)}
            ).encode(),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": updated_cookie,
                "HX-Request": "true",
                "HX-Target": "board",
            },
        )

    assert plain.status == 303
    assert plain.header("location") == "/"
    assert "Invite the first tester" in page.text
    assert htmx.status == 200
    assert "Share the link" in htmx.text
    assert "hx-swap-oob" in htmx.text


async def test_sse_emits_rendered_live_status() -> None:
    async with TestClient(app) as client:
        result = await client.sse("/events", max_events=1)

    assert len(result.events) == 1
    assert result.events[0].event == "live-status"
    assert "Launch Board is live" in result.events[0].data


def test_app_contracts_pass() -> None:
    assert app.config.workers == 1
    app.check()
