from discord.ext import commands
import discord
from typing import Any, Dict
from src.discord_ctftime.event import Engine


def setup_commands(bot: commands.Bot, engine: Engine) -> None:


    @bot.command(
        name="participants",
        aliases=["part", "p"],
        help="Affiche les participants d'un évènement (ctftime_id).",
    )
    async def participants_cmd(ctx: commands.Context, ctftime_id: str):
        try:
            ev = engine.get_event_info_by_ctftime(ctftime_id)
        except KeyError:
            await ctx.send(f"❌ Aucun évènement avec l'ID `{ctftime_id}`.")
            return

        embed = discord.Embed(
            title=f"Participants pour « {ev['title']} »",
            colour=discord.Colour.red(),
        )
        participants = ev.get("participants", [])
        embed.add_field(
            name="👥 Participants",
            value="\n".join(participants) if participants else "Aucun inscrit pour le moment... BOUGEZ VOUS BANDE DE FEIGNASSES !",
            inline=False,
        )
        await ctx.send(embed=embed)
