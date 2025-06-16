from __future__ import annotations

import discord
from discord import app_commands, Interaction, Embed, Colour
from discord.ext import commands
from typing import Any, Dict, List
from functools import partial

from src.discord_ctftime.event import Engine
from src.discord_ctftime.utils.utils import _to_datetime


from datetime import datetime
from zoneinfo import ZoneInfo



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
            ev: Dict[str, Any] = engine.next_event()
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

    def _chunks(seq: List[Any], n: int) -> List[List[Any]]:
        return [seq[i : i + n] for i in range(0, len(seq), n)]


    @bot.hybrid_command(
        name="agenda",
        aliases=["cal", "calendar"],
        description="Affiche un calendrier des évènements à venir (≤ 30 jours) avec des participants.",
        with_app_command=True,
    )
    async def agenda_cmd(
        ctx: commands.Context | Interaction,
        jours: int = 30,
    ):

        if isinstance(ctx, Interaction):
            if not ctx.response.is_done():
                send = ctx.response.send_message
            else:
                send = ctx.followup.send
        else:
            send = partial(_send, ctx)

        try:
            events: List[Dict[str, Any]] = engine.calendar_next_30_days(span_days=jours)
        except LookupError as exc:
            await send(f"❌ {exc}", ephemeral=True)
            return

        title = f"📅 Calendrier des évènements (≤ {jours} jours)"
        colour = Colour.blurple()

        pages = _chunks(events, 25)

        for index, page in enumerate(pages, start=1):
            embed = Embed(title=title, colour=colour)
            if len(pages) > 1:
                embed.set_footer(text=f"Page {index}/{len(pages)}")

            tz_paris = ZoneInfo("Europe/Paris")

            for ev in page:
                dt = _to_datetime(ev.get("start"), tz_paris)
                if dt is None:
                    continue

                ts = int(dt.timestamp())
                when = f"<t:{ts}:f>  •  <t:{ts}:R>"

                participants = ev.get("participants", [])
                maybe = ev.get("maybe_participants", [])

                value = (
                    f"{when}\n"
                    f"👥 {len(participants)} participant(s)  •  "
                    f"❔ {len(maybe)} peut-être"
                )
                embed.add_field(name=f"**{ev['title']}**", value=value, inline=False)

            await send(embed=embed, ephemeral=True)