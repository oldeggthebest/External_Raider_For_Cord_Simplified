# Kiox Clean

A user-installable Discord raid bot — its commands work everywhere: servers, DMs, group DMs.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then put your bot token in .env
# edit config.json (prefix, raid counts, sync_guilds, ...)
python main.py
```

The token only goes in `.env` (`DISCORD_TOKEN`). `config.json` is settings, no secrets.

## Structure

| Path | What it is |
|---|---|
| `main.py` | entry point — loads config, the cog, syncs commands |
| `cogs/commands.py` | every command |
| `core/raids.py` | webhook raid engine |
| `fonts/`, `raid_message.txt` | data files (fake-message fonts, raid text) |

## Commands

| Category | Commands |
|---|---|
| Raid | `raid`, `embed-raid`, `poll-raid`, `button-raid`, `slow-raid`, `blank-flood` |
| Spam & ghost | `massping`, `ghost-ping`, `massghostping`, `say`, `ghost-say`, `button-say`, `fake-nitro`, `rickroll-spam`, `lagger`, `fake-message` |
| Tools | `ping`, `uptime`, `invite`, `help`, `server-info`, `whois`, `check`, `blame`, `fake-ip`, `analytics` |

Every command is user-installable, so they all work in servers, DMs and group DMs without adding the bot anywhere.
