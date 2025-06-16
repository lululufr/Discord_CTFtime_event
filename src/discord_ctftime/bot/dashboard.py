import discord, datetime as dt, asyncio
from discord.ext import commands, tasks

from src.discord_ctftime.event import Engine

import os
CHANNEL_ID_DASH = int(os.getenv("DASH_CHANNEL_ID", 0))

REFRESH_EVERY   = 20               # seconde
SPAN_DAYS       = 30               # fenêtre du calendrier

class Dashboard(commands.Cog):

    def __init__(self, bot: commands.Bot, engine: Engine):
        self.bot     = bot
        self.engine  = engine
        self.msg_id: int | None = None
        self.refresh_loop.start()


    async def _ensure_message(self) -> discord.Message:
        channel = self.bot.get_channel(CHANNEL_ID_DASH)

        # si rien en cache ⇒ on tente l’API REST
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(CHANNEL_ID_DASH)
            except discord.NotFound:
                raise RuntimeError(
                    f"Salon {CHANNEL_ID_DASH} introuvable ou inaccessible pour le bot."
                )

        if self.msg_id:
            try:
                return await channel.fetch_message(self.msg_id)
            except discord.NotFound:
                self.msg_id = None

        msg = await channel.send(embed=discord.Embed(description="Initialisation…"))
        self.msg_id = msg.id
        return msg

    def _make_calendar_embed(self) -> discord.Embed:
        try:
            events = self.engine.calendar_next_30_days(span_days=SPAN_DAYS)
        except LookupError:
            embed = discord.Embed(
                title="📅 Aucun évènement à venir",
                description="Aucun CTF prévu avec des inscrits dans les "
                            f"{SPAN_DAYS} prochains jours.",
                colour=discord.Colour.orange(),
            )
            return embed

        embed = discord.Embed(
            title=f"📅 Les {len(events)} prochains évènements (≤{SPAN_DAYS} j)",
            colour=discord.Colour.blue(),
            timestamp=dt.datetime.now(),
        )
        for ev in events:
            p = ", ".join(ev["participants"]) or "—"
            m = ", ".join(ev["maybe_participants"]) or "—"
            field_val = (
                f"**Début :** {ev['start']}\n"
                f"**Fin :** {ev['end']}\n"
                f"**Inscrits :** {p}\n"
                f"**Peut-être :** {m}"
            )
            embed.add_field(
                name=f"🔗 [{ev['title']}]({ev['url']})",
                value=field_val,
                inline=False,
            )
        embed.set_footer(text="Mise à jour auto")
        return embed

    @commands.hybrid_command(
        name="dashboard_refresh", description="Ré-affiche le calendrier des 30 prochains jours."
    )
    async def dashboard_cmd(self, ctx: commands.Context):
        msg = await self._ensure_message()
        await msg.edit(embed=self._make_calendar_embed())
        await ctx.reply("✅ Dashboard rafraîchi !", ephemeral=True)

    @tasks.loop(seconds=REFRESH_EVERY)
    async def refresh_loop(self):
        if not self.bot.is_ready():
            return
        msg = await self._ensure_message()
        await msg.edit(embed=self._make_calendar_embed())

    @refresh_loop.before_loop
    async def _wait_bot(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(Dashboard(bot, bot.engine))
