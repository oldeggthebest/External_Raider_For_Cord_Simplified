"""Raid bot entry point.

Reads config.json (settings, no secrets), loads the single command cog,
and syncs the tree so every command is user-installable everywhere:
servers, DMs and group DMs.
"""

import json
import os
import sys

import discord
from discord.ext import commands
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.abspath(__file__))

# config.json holds settings only - the bot token lives in .env (DISCORD_TOKEN).
with open(os.path.join(BASE, "config.json"), encoding="utf-8") as f:
    CONFIG = json.load(f)


class RaidBot(commands.Bot):
    """Thin bot shell: load the cog, widen install scopes, sync, done."""

    def __init__(self):
        # guilds only - nothing else needs an intent for this bot.
        intents = discord.Intents.none()
        intents.guilds = True
        super().__init__(
            command_prefix=CONFIG.get("prefix", "!"),
            intents=intents,
            # let @everyone/@role/@user mentions actually go through.
            allowed_mentions=discord.AllowedMentions(
                everyone=True, roles=True, users=True),
        )
        self.config = CONFIG

    async def setup_hook(self):
        # one cog holds every command
        await self.load_extension("cogs.commands")

        # Make every command user-installable in servers, DMs and group
        # DMs. Contexts don't inherit from a group to its subcommands,
        # so walk the whole tree.
        def _allow(cmd):
            try:
                cmd.allowed_installs = discord.AppInstallationType(
                    guilds=True, users=True)
                cmd.allowed_contexts = discord.AppCommandContext(
                    guilds=True, dms=True, private_channels=True)
            except Exception:
                pass
            for child in getattr(cmd, "commands", []) or []:
                _allow(child)

        for cmd in self.tree.get_commands():
            _allow(cmd)

        # global sync - one pass covers every command
        await self.tree.sync()
        print(f"[+] synced {len(self.tree.get_commands())} commands globally")

        # Global sync can take up to an hour to show up; syncing to a
        # guild listed in config.json (sync_guilds) is instant.
        for gid in CONFIG.get("sync_guilds", []) or []:
            try:
                guild = discord.Object(id=int(gid))
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                print(f"[+] synced {len(synced)} commands to guild {gid}")
            except Exception as exc:
                print(f"[!] guild sync failed for {gid}: {exc}")

    async def on_ready(self):
        print(f"[+] logged in as {self.user} ({self.user.id})")


if __name__ == "__main__":
    load_dotenv(os.path.join(BASE, ".env"))

    # token comes from the environment only - config.json stays secret-free.
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("[!] DISCORD_TOKEN is not set - copy .env.example to .env and add your token.")
        sys.exit(1)

    RaidBot().run(token)
