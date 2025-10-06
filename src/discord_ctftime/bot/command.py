from __future__ import annotations

import discord
from discord import app_commands, Interaction, Embed, Colour
from discord.ext import commands
from typing import Any, Dict, List
from functools import partial

from src.discord_ctftime.event import Engine
from src.discord_ctftime.ctftime import CTFtime
from src.discord_ctftime.utils.utils import _to_datetime
from src.discord_ctftime.bot.group import Group


from datetime import datetime
from zoneinfo import ZoneInfo


import os
from dotenv import load_dotenv

load_dotenv()


DISCORD_TOKEN  = os.getenv("DISCORD_TOKEN")
CHANNEL_ID     = int(os.getenv("CHANNEL_ID"))
RSS_URL        = os.getenv("RSS_URL")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 30))
SERVER_ID = int(os.getenv("SERVER_ID", None))  
DEEP_EVENT = int(os.getenv("DEEP_EVENT", 15))
CATE_ID = int(os.getenv("CATEGORY_ID_FOR_CTFCHANNEL", None)) 

OK_EMOJI = os.getenv("OK_EMOJI")
MAYBE_EMOJI = os.getenv("MAYBE_EMOJI")
NOT_EMOJI = os.getenv("NOT_EMOJI")



engine = Engine()


async def _send( target: commands.Context | Interaction,content: str | None = None,**kwargs) -> None:
    if isinstance(target, Interaction):
        if target.response.is_done():
            await target.followup.send(content, **kwargs)
        else:
            await target.response.send_message(content, **kwargs)
    else:
        await target.send(content, **kwargs)


def setup_commands(bot: commands.Bot, engine: Engine, channel:TextChannel) -> None:


    @bot.hybrid_command(
    name="aide",
    aliases=["a"],
    description="Affiche l’aide du bot",
    with_app_command=True,
    )
    async def help_cmd(ctx: commands.Context | Interaction) -> None:
        """Commande /help – récapitulatif des commandes disponibles."""

        if isinstance(ctx, Interaction) and not ctx.response.is_done():
            await ctx.response.defer(ephemeral=True)
        elif isinstance(ctx, commands.Context):
            await ctx.defer(ephemeral=True)

        embed = discord.Embed(
            title="📖 Aide du bot",
            description="Voici la liste des commandes disponibles :",
            colour=discord.Colour.green(),
        )

        for cmd in bot.commands:
            if cmd.hidden or not isinstance(cmd, commands.HybridCommand):
                continue

            slash = f"/{cmd.name}"
            pref = f"`{ctx.prefix}{cmd.aliases[0]}`" if cmd.aliases else ""
            liste_noms = " • ".join(filter(None, [slash, pref]))

            desc = cmd.description or "Pas de description."

            embed.add_field(name=liste_noms, value=desc, inline=False)

        embed.set_footer(text="Paramètres facultatifs entre [crochets] • obligatoires entre <chevrons>")

        await _send(ctx, embed=embed, ephemeral=True)



##joke 

    @bot.hybrid_command(
        name="send_feet",
        aliases=["sf"],
        description="Envoi une photo de pied, a un membre aléatoire de l'équipe.",
        with_app_command=True,
    )
    async def joke(ctx: commands.Context):
        await _send(ctx, "Wesh ?? ça va fréro ? 🩴", ephemeral=True)

## joke 



    @bot.hybrid_command(
        name="participants",
        aliases=["part", "p"],
        description="Affiche les participants d'un évènement (ctftime_id).",
        with_app_command=True,
    )
    @app_commands.describe(
        ctftime_id="ID de l'évènement sur CTFtime"
    )
    async def participants_cmd(ctx: commands.Context, ctftime_id: str):

        if ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.interaction.response.defer(ephemeral=True)

        #try:
        ev: Dict[str, Any] = engine.get_event_info(ctftime_id)
        #except KeyError:
        #    await _send(ctx, f"❌ Aucun évènement avec l'ID `{ctftime_id}`.", ephemeral=True)
        #    return

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

    # fonction pour du jolie , du beau, du magnifique 
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



    # Créer un nouvel événement en fonction d'un ID CTFtime
    @bot.hybrid_command(
        name="new_event",
        aliases=["new"],
        description="Créé un event CTF en se fiant a un ID CTFtime",
        with_app_command=True,
    )
    @app_commands.describe(
        ctftime_id="ID de l'évènement sur CTFtime"
    )
    async def add_event(ctx: commands.Context | Interaction, ctftime_id: str):

        if isinstance(ctx, Interaction) and not ctx.response.is_done():
            await ctx.response.defer(thinking=True, ephemeral=True)

        ctf = CTFtime(ctftime_id)


        try:
            event = await ctf.fetch()
        except Exception:
            await _send(ctx, "❌ L'évènement n'existe pas avec cet ID.", ephemeral=True)
            return

 

        if engine.existe(event.id):
            await _send(ctx, "ℹ️ L'évènement est déjà enregistré.", ephemeral=True)
            return

        team_text   = "🚶‍♂️ Individuel" if ctf.solo() else "👥 Équipe"
        online_text = "🛜 En ligne"     if ctf.online() else "🏘️ Présentiel"



        embed = discord.Embed(
            title=f"🔒 {event.title}",
            url=event.url,
            description=(
                f"{OK_EMOJI} **Je participe**   •   {MAYBE_EMOJI} **Peut-être**\n"
                "—\n"
                "Clique sur une réaction pour t’inscrire !"
            ),
            colour=discord.Colour.blurple(),
        )

        embed.add_field(name="📆 Début",  value=f"**{event.start}**", inline=True)
        embed.add_field(name="⏰ Fin",    value=f"**{event.finish}**", inline=True)
        embed.add_field(name="\u200b",   value="\u200b",              inline=True)
        embed.add_field(name="🏅 Weight", value=f"**{event.weight}** pts", inline=True)
        embed.add_field(name="",         value=team_text,             inline=True)
        embed.add_field(name="",         value=online_text,           inline=True)
        embed.add_field(
            name="🗓️ Calendrier",
            value=f"[Ajouter à mon agenda](https://ctftime.org/event/{event.id}.ics)",
            inline=False,
        )
        embed.set_footer(text=f"ID de l’évènement : {event.id}")

        msg = await channel.send(embed=embed)
        await bot.add_default_reactions(msg)

        engine.new_event(
            ctftime_id=event.id,
            msg_id=msg.id,
            title=event.title,
            url=str(event.ctftime_url),
            start=event.start,
            end=event.finish,
            description=event.description,
        )

        grp = Group(ctx.interaction, CATE_ID)
        # création du groupe discord 
        try :
            await grp.new_group(event.title)
        except:
            print("error creation role")


        await _send(
            ctx,
            f"✅ Évènement **{event.title}** créé et publié dans {channel.mention} !",
            ephemeral=True,
        )