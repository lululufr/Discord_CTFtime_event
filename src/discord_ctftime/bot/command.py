# src/discord_ctftime/commands/participants.py
from __future__ import annotations

import discord
from discord import app_commands, Interaction, Embed, Colour
from discord.ext import commands
from typing import Any, Dict

from src.discord_ctftime.event import Engine


async def _send( target: commands.Context | Interaction,content: str | None = None,**kwargs) -> None:

    if isinstance(target, Interaction):
        if target.response.is_done():
            await target.followup.send(content, **kwargs)
        else:
            await target.response.send_message(content, **kwargs)
    else:
        await target.send(content, **kwargs)


def setup_commands(bot: commands.Bot, engine: Engine) -> None:

    @bot.hybrid_command(
        name="participants",
        aliases=["part", "p"],
        description="Affiche les participants d'un évènement (ctftime_id).",
        with_app_command=True,
    )
    @app_commands.describe(
        ctftime_id="ID de l'évènement sur CTFtime"
    )
    async def participants_cmd( ctx: commands.Context | Interaction,ctftime_id: str):

        try:
            ev: Dict[str, Any] = engine.get_event_info(ctftime_id)
        except KeyError:
            await _send(ctx, f"❌ Aucun évènement avec l'ID `{ctftime_id}`.")
            return

        embed = Embed(
            title=f"Participants pour « {ev['title']} »",
            colour=Colour.red(),
        )

        participants = ev.get("participants", [])
        embed.add_field(
            name="👥 Participants",
            value="\n".join(participants) if participants else "Aucun inscrit…",
            inline=False,
        )

        maybe = ev.get("maybe_participants", [])
        embed.add_field(
            name="❓ Peut-être ?",
            value="\n".join(maybe) if maybe else "X",
            inline=False,
        )

        await _send(ctx, embed=embed, ephemeral=True)


    @bot.hybrid_command(
        name="next_event",
        aliases=["next", "n"],
        description="Affiche le prochaine évènement avec des participants",
        with_app_command=True,
    )
    async def next_event_cmd( ctx: commands.Context):

        try:
            ev: Dict[str, Any] = engine.next_event()  # ✅ plus de double appel
        except LookupError as exc:
            await _send(ctx, f"❌ {exc}")
            return

        embed = Embed(
            title=f"Prochain événement « {ev['title']} »",
            colour=Colour.red(),
        )

        when = ev.get("start")
        embed.add_field(
            name="⌚ Quand : ",
            value=f"{when}",
            inline=False,
        )

        participants = ev.get("participants", [])
        embed.add_field(
            name="👥 Participants",
            value="\n".join(participants) if participants else "Aucun inscrit…",
            inline=False,
        )

        maybe = ev.get("maybe_participants", [])
        embed.add_field(
            name="❓ Peut-être ?",
            value="\n".join(maybe) if maybe else "X",
            inline=False,
        )

        await _send(ctx, embed=embed, ephemeral=True)
