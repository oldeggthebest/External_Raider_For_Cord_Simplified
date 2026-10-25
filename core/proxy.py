"""Proxy rotation - spread farm raid traffic across farm_proxies.txt.

/raid-farm and /all-raid fire through this pool so IP-level
throttling and Cloudflare pressure spread out instead of stalling
the whole burst. Token-level global limits survive rotation (they
ride on the interaction token, not the IP).
"""

import asyncio
import json
import logging
import time

import aiohttp

log = logging.getLogger("raider.proxy")

_REQUEST_TIMEOUT = 3
_QUARANTINE_BASE = 10
_QUARANTINE_CAP = 120

_SESSION = None


def _get_session():
    """Lazily create the shared session inside the running event loop."""
    global _SESSION
    if _SESSION is None or _SESSION.closed:
        _SESSION = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=0))
    return _SESSION


def parse_proxy_line(line):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    # farm format: ip:port:user:pass
    if "@" not in line and "://" not in line and line.count(":") == 3:
        ip, port, user, pw = line.split(":")
        return f"http://{ip}:{port}", aiohttp.BasicAuth(user, pw)
    if "://" not in line:
        line = "http://" + line
    auth = None
    if "@" in line:
        scheme, rest = line.split("://", 1)
        creds, hostport = rest.rsplit("@", 1)
        if ":" in creds:
            user, pw = creds.split(":", 1)
            auth = aiohttp.BasicAuth(user, pw)
        line = f"{scheme}://{hostport}"
    return line, auth


def load_proxies(path):
    out = []
    try:
        with open(path, encoding="utf-8") as fh:
            for raw in fh:
                parsed = parse_proxy_line(raw)
                if parsed is not None:
                    out.append(parsed)
    except OSError:
        return out
    return out


class ProxyPool:
    def __init__(self, entries):
        self._slots = [
            {"proxy": proxy, "auth": auth, "fails": 0, "retry_at": 0.0}
            for proxy, auth in entries
        ]
        self._idx = 0

    def __len__(self):
        return len(self._slots)

    def __bool__(self):
        return bool(self._slots)

    def _pick(self):
        n = len(self._slots)
        now = time.monotonic()
        for _ in range(n):
            slot = self._slots[self._idx % n]
            self._idx += 1
            if slot["retry_at"] <= now:
                return slot
        return min(self._slots, key=lambda s: s["retry_at"])

    def next(self):
        slot = self._pick()
        return slot["proxy"], slot["auth"], slot

    def mark_ok(self, slot):
        slot["fails"] = 0

    def mark_failed(self, slot):
        slot["fails"] += 1
        backoff = min(_QUARANTINE_BASE * (2 ** min(slot["fails"] - 1, 4)),
                      _QUARANTINE_CAP)
        slot["retry_at"] = time.monotonic() + backoff
        log.warning("proxy %s unreachable - quarantined for %.0fs (fail #%d)",
                    slot["proxy"], backoff, slot["fails"])


# per-webhook send pace: each invocation (its own interaction token in
# the webhook url) paces only itself, so two users raiding at once no
# longer queue behind each other. Farm paths pass their own pace.
GLOBAL_PACE = 0.40
_PACE_LOCKS = {}
_PACE_LAST = {}

# global rate-limit gate: when ANY webhook POST eats a 429, every sender
# backs off until it passes (discord.py does the same for global limits).
_GLOBAL_RL_UNTIL = 0.0


async def _pace(pool, interval, key=None):
    if not interval or interval <= 0:
        return
    if key is None:
        key = id(pool) if pool is not None else "direct"
    lock = _PACE_LOCKS.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _PACE_LOCKS[key] = lock
    async with lock:
        now = time.monotonic()
        wait = interval - (now - _PACE_LAST.get(key, 0.0))
        if wait > 0:
            await asyncio.sleep(wait)
        _PACE_LAST[key] = time.monotonic()


async def _global_gate():
    _wait = _GLOBAL_RL_UNTIL - time.monotonic()
    if _wait > 0:
        await asyncio.sleep(min(_wait, 60.0))


def _global_note(retry_after):
    global _GLOBAL_RL_UNTIL
    try:
        _ra = float(retry_after)
    except (TypeError, ValueError):
        _ra = 1.0
    _GLOBAL_RL_UNTIL = max(_GLOBAL_RL_UNTIL, time.monotonic() + _ra + 0.5)


async def webhook_post(url, payload, *, wait=True, no_retry=False,
                       pool=None, pace=None):
    """POST a webhook message through a rotating proxy.

    Every attempt leaves from a fresh proxy, so IP-level throttling
    spreads across the pool instead of stalling the whole burst. 429s
    sleep their retry_after and hop proxies; dead proxies get
    quarantined. Returns the message JSON on a waited POST, True on a
    bare 2xx, False when the pool gives up.

    Without a pool (no farm_proxies.txt) the request goes out direct,
    so the bot still works everywhere.
    """
    endpoint = f"{url}?wait=true" if wait else f"{url}?wait=false"
    # farm fires read aloud too - same rule as raids._webhook_request
    if payload and "tts" not in payload and payload.get("content"):
        payload = {**payload, "tts": True}
    await _pace(pool, pace if pace is not None else GLOBAL_PACE, key=url)
    await _global_gate()
    attempts = 12 if pool is not None and pool else 3
    for attempt in range(attempts):
        proxy_url, auth, slot = None, None, None
        if pool is not None and pool:
            proxy_url, auth, slot = pool.next()
        try:
            async with _get_session().post(
                endpoint,
                json=payload,
                proxy=proxy_url, proxy_auth=auth,
                timeout=aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT),
            ) as resp:
                if resp.status == 429:
                    retry_after = None
                    try:
                        body = await resp.json()
                        retry_after = float(body.get("retry_after"))
                    except Exception:
                        pass
                    _global_note(retry_after)
                    await asyncio.sleep((retry_after or 1.0) + 0.05)
                    continue
                if resp.status < 300:
                    if slot is not None:
                        pool.mark_ok(slot)
                    try:
                        return await resp.json()
                    except Exception:
                        pass
                    return True
                # a real failure - the caller decides what it means
                if slot is not None:
                    pool.mark_failed(slot)
                try:
                    _body = (await resp.text())[:500]
                except Exception:
                    _body = "<no body>"
                log.warning("HTTP %s on POST %s (attempt %d/%d) body=%r",
                            resp.status, url, attempt + 1, attempts, _body)
                return False
        except (OSError, asyncio.TimeoutError, aiohttp.ClientError) as _exc:
            if attempt == 0 or attempt == attempts - 1:
                log.warning("attempt %d/%d exc=%s: %s",
                            attempt + 1, attempts, type(_exc).__name__, _exc)
            if no_retry:
                # the request may have landed - never retry, or the
                # message duplicates
                return False
            if slot is not None:
                pool.mark_failed(slot)
            await asyncio.sleep(0.3)
    log.warning("ALL %d attempts failed for POST %s", attempts, url)
    return False
