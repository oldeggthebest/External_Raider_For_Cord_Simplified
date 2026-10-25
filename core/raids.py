"""Raid engine - interaction webhook spam at max speed.

An interaction token buys one response plus followup posts on the
webhook endpoint, so a raid is just that endpoint fired in bursts.
Everything goes out direct over aiohttp.
"""

import asyncio
import os
import time

import aiohttp

# webhook messages need allowed_mentions.parse to include everyone,
# otherwise Discord silently strips @everyone/@here from the content
MENTIONS = {"parse": ["everyone", "roles", "users"]}

ZWSP = "\u200b"
DEFAULT_BLANK = "\n".join(ZWSP * 100 for _ in range(19))

# per-webhook send pace: each interaction token paces only itself, so
# two users raiding at once don't queue behind each other
GLOBAL_PACE = 0.40
_REQUEST_TIMEOUT = 3
_ATTEMPTS = 3
_USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
               "AppleWebKit/537.36 (KHTML, like Gecko) "
               "Chrome/131.0.0.0 Safari/537.36")

_SESSION = None
_pace_locks = {}
_pace_last = {}
_rate_limit_until = 0.0


def _session():
    global _SESSION
    if _SESSION is None or _SESSION.closed:
        _SESSION = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=0))
    return _SESSION


def raid_payload(message):
    """Raid message with an @everyone @here prefix, so every payload
    pings the whole server when the caller has mention permission."""
    base = message or "raid"
    if "@everyone" in base and "@here" in base:
        return base
    return "@everyone @here\n" + base


def load_blank_message(path=None):
    """Invisible ZWSP wall for blank floods - reads blank_mesg.txt when
    present, regenerates it with the default wall when not."""
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "blank_mesg.txt")
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        if text:
            return text
    except OSError:
        pass
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(DEFAULT_BLANK)
    except OSError:
        pass
    return DEFAULT_BLANK


def _followup_url(interaction):
    return (f"https://discord.com/api/v10/webhooks/"
            f"{interaction.application_id}/{interaction.token}")


async def _pace(key):
    lock = _pace_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _pace_locks[key] = lock
    async with lock:
        wait = GLOBAL_PACE - (time.monotonic() - _pace_last.get(key, 0.0))
        if wait > 0:
            await asyncio.sleep(wait)
        _pace_last[key] = time.monotonic()


# when any webhook POST eats a 429 every sender backs off until it
# passes - without this parallel bursts just burn retries
async def _rate_gate():
    wait = _rate_limit_until - time.monotonic()
    if wait > 0:
        await asyncio.sleep(min(wait, 60.0))


def _note_rate_limit(retry_after):
    global _rate_limit_until
    _rate_limit_until = max(_rate_limit_until,
                            time.monotonic() + retry_after + 0.5)


async def _retry_after(resp):
    try:
        body = await resp.json()
        return float(body.get("retry_after"))
    except Exception:
        return 1.0


async def _webhook_request(url, payload=None, *, wait=True, files=None,
                           message_id=None, no_retry=False):
    """POST to a webhook, or DELETE message_id when one is given.

    Returns the message JSON on a waited POST, True on a bare 2xx,
    False on failure. 429s sleep their retry_after; network errors
    retry unless no_retry - a timed-out POST may have landed already,
    so retrying duplicates the message.
    """
    # every content-bearing raid message goes out with tts on, so the
    # target channel hears the robotic voice reading the spam aloud
    if (payload and not message_id and "tts" not in payload
            and payload.get("content")):
        payload = {**payload, "tts": True}
    await _pace(url)
    await _rate_gate()
    if message_id:
        method, endpoint = "DELETE", f"{url}/messages/{message_id}"
    else:
        method = "POST"
        endpoint = f"{url}?wait={'true' if wait else 'false'}"
    for _ in range(_ATTEMPTS):
        kwargs = {"json": payload}
        if files:
            form = aiohttp.FormData()
            for filename, data in files:
                form.add_field("files[0]", data, filename=filename,
                               content_type="image/gif")
            kwargs = {"data": form}
        try:
            async with _session().request(
                method, endpoint, timeout=aiohttp.ClientTimeout(
                    total=_REQUEST_TIMEOUT),
                **kwargs,
            ) as resp:
                if resp.status == 429:
                    retry_after = await _retry_after(resp)
                    _note_rate_limit(retry_after)
                    await asyncio.sleep(retry_after + 0.05)
                    continue
                if resp.status < 300:
                    if wait:
                        try:
                            return await resp.json()
                        except Exception:
                            pass
                    return True
                return False
        except (OSError, asyncio.TimeoutError, aiohttp.ClientError):
            if no_retry:
                return False
            await asyncio.sleep(0.3)
    return False


async def get_json(url, *, headers=None):
    """Plain GET - parsed JSON, or None on any failure."""
    hdrs = {"User-Agent": _USER_AGENT}
    if headers:
        hdrs.update(headers)
    try:
        async with _session().get(
            url, headers=hdrs,
            timeout=aiohttp.ClientTimeout(total=8),
        ) as resp:
            if resp.status >= 300:
                return None
            return await resp.json(content_type=None)
    except (aiohttp.ClientError, asyncio.TimeoutError, OSError):
        return None


async def raw_followup(interaction, data):
    """Fire a raw components-v2 payload at the interaction's followup
    webhook - used after the hidden "Sent." ack went out."""
    return bool(await _webhook_request(_followup_url(interaction), data))


async def interaction_fire(interaction, message, count=1,
                           hidden_first=True, username="anon",
                           embeds=None, ephemeral=False, ghost=False,
                           no_retry=False):
    """Fire `message` (or `embeds`) `count` times through the
    interaction webhook and return how many landed.

    ghost=True posts a batch of 10, lets it flash for 1.5s, then
    deletes it (/ghost-ping, /ghost-say). no_retry=True skips the
    network-error retry - used by /say (count=1), where exactly one
    message must land.
    """
    landed = 0

    if hidden_first:
        try:
            await interaction.response.send_message("Sent.", ephemeral=True)
            landed += 1
        except Exception:
            pass

    url = _followup_url(interaction)
    if embeds is not None:
        payload = {"embeds": embeds, "username": username,
                   "allowed_mentions": MENTIONS}
    else:
        payload = {"content": message, "username": username,
                   "allowed_mentions": MENTIONS}

    remaining = count
    if ghost:
        # wait=True so the message ids ride back for the deletes -
        # the 1.5s flash sleep happens once per batch, not per message
        while remaining > 0:
            batch = min(remaining, 10)
            sent = await asyncio.gather(
                *(_webhook_request(url, payload) for _ in range(batch)),
                return_exceptions=True,
            )
            ids = [r["id"] for r in sent
                   if isinstance(r, dict) and r.get("id")]
            landed += len(ids)
            await asyncio.sleep(1.5)
            if ids:
                await asyncio.gather(
                    *(_webhook_request(url, message_id=mid) for mid in ids),
                    return_exceptions=True,
                )
            remaining -= batch
    else:
        # burst fire - 20 concurrent per batch, wait=False (fire and
        # forget - Discord answers 204 the moment it accepts the
        # message). 429s self-throttle inside _webhook_request.
        while remaining > 0:
            batch = min(remaining, 20)
            results = await asyncio.gather(
                *(_webhook_request(url, payload, wait=False,
                                   no_retry=no_retry)
                  for _ in range(batch)),
                return_exceptions=True,
            )
            landed += sum(1 for r in results if r is True)
            remaining -= batch

    return landed


async def fire_followup(interaction, message="", username="anon",
                        files=None, embeds=None, poll=None):
    """One public followup. `files` is a list of (filename, bytes)
    uploaded as attachments, so extensionless CDN files still embed as
    GIFs. `poll` is a native poll payload dict."""
    payload = {"content": message, "username": username,
               "allowed_mentions": MENTIONS}
    if embeds is not None:
        payload["embeds"] = embeds
        payload.pop("content", None)
    if poll is not None:
        payload["poll"] = poll
    return await _webhook_request(_followup_url(interaction), payload,
                                  files=files, wait=False)
