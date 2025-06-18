import discord
from discord.ext import commands
import asyncio
import feedparser
from src.discord_ctftime.event import Engine
from src.discord_ctftime.rss import Rss

from src.discord_ctftime.bot.command import setup_commands


import src.discord_ctftime.bot.dashboard

import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN  = os.getenv("DISCORD_TOKEN")
CHANNEL_ID     = int(os.getenv("CHANNEL_ID"))
RSS_URL        = os.getenv("RSS_URL")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 30))
SERVER_ID = int(os.getenv("SERVER_ID", None))  # ID du serveur Discord

#DEFINE EMOJI REACTION
OK_EMOJI = "✅"
MAYBE_EMOJI = "❓"
ALLOWED_EMOJIS = {OK_EMOJI, MAYBE_EMOJI}

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

dernier_article = None



class Bot(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.engine = Engine()

    async def setup_hook(self):
        # enregistre toutes les commandes texte
        setup_commands(self, self.engine)

        #dashbaord
        await self.load_extension("src.discord_ctftime.bot.dashboard")

        guild = discord.Object(id=SERVER_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)


        #lance le check RSS
        self.bg_task = asyncio.create_task(self.check_rss())

    async def on_ready(self):
        print(f"✅ Connecté en tant que {self.user}")

    async def check_rss(self):
        global dernier_article
        await self.wait_until_ready()
        channel = self.get_channel(CHANNEL_ID)

        while True:
            flux = feedparser.parse(RSS_URL)

            if flux.entries:
                # On parcourt les 5 premiers items, du plus ancien vers le plus récent
                for item in reversed(flux.entries[:5]):

                    # Si on est déjà passé sur ce lien on peut arrêter la boucle ;
                    # tout ce qui suit est déjà connu.
                    if dernier_article == item.link:
                        break

                    event = Rss(item)

                    # Vérifie si l'évènement existe déjà dans la BDD interne
                    if self.engine.existe(event.ctftime_id):
                        continue

                    print(f"Event {event.ctftime_id} not exists, creating.")

                    embed = discord.Embed(
                        title=event.titre,
                        url=event.lien,
                        description=(
                            "Inscris-toi avec ✅ si tu participes !\n"
                            "…ou avec ❓ si tu n'es pas sûr."
                        ),
                        colour=discord.Colour.blue()
                    )
                    embed.add_field(name="📆 Début", value=event.date_debut, inline=True)
                    embed.add_field(name="⏰ Fin",   value=event.date_fin,   inline=True)
                    embed.add_field(name="🏷️ Weight", value=event.weight,   inline=False)
                    embed.add_field(name="", value=f"[add calendar](https://ctftime.org/event/{event.ctftime_id}.ics)")
                    embed.add_field(name="", value=f"ID : {event.ctftime_id}")

                    msg = await channel.send(embed=embed)

                    self.engine.new_event(
                        ctftime_id=event.ctftime_id,
                        msg_id=msg.id,
                        title=event.titre,
                        url=event.lien,
                        start=event.date_debut,
                        end=event.date_fin,
                        description=item.description,
                    )

                # Met à jour la référence : le tout dernier article traité
                dernier_article = flux.entries[0].link

            await asyncio.sleep(CHECK_INTERVAL)


    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id != SERVER_ID:
            return
        if str(payload.emoji) not in ALLOWED_EMOJIS:
            return
        if payload.user_id == self.user.id:
            return
        if not self.engine.existe(payload.message_id):
            return

        guild   = self.get_guild(payload.guild_id)
        channel = self.get_channel(payload.channel_id)
        user    = guild.get_member(payload.user_id)
        message = await channel.fetch_message(payload.message_id)

        if str(payload.emoji) == OK_EMOJI:
            self.engine.add_participant(payload.message_id, user.display_name)
            title = self.engine.get_event_info(payload.message_id)["title"]
            await channel.send(
                f"ℹ️ {user.display_name} inscrit à : `{title}` {OK_EMOJI}",
                delete_after=30,
            )
        else:
            self.engine.add_maybe_participant(payload.message_id, user.display_name)
            title = self.engine.get_event_info(payload.message_id)["title"]
            await channel.send(
                f"ℹ️ {user.display_name} participera peut-être à : `{title}` {MAYBE_EMOJI}",
                delete_after=30,
            )

    # ───────────────────────── RAW REACTION REMOVE ─────────────────────────
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id != SERVER_ID:
            return
        if str(payload.emoji) not in ALLOWED_EMOJIS:
            return
        if not self.engine.existe(payload.message_id):
            return

        guild   = self.get_guild(payload.guild_id)
        channel = self.get_channel(payload.channel_id)
        user    = guild.get_member(payload.user_id)

        if str(payload.emoji) == OK_EMOJI:
            self.engine.remove_participant(payload.message_id, user.display_name)
            await channel.send(
                f"➖ **{user.display_name}** désinscrit {OK_EMOJI}",
                delete_after=30,
            )
        else:
            self.engine.remove_maybe_participant(payload.message_id, user.display_name)
            await channel.send(
                f"➖ **{user.display_name}** a retiré son « peut-être » {MAYBE_EMOJI}",
                delete_after=30,
            )



client = Bot(command_prefix="/",intents=intents)

client.run(DISCORD_TOKEN)
