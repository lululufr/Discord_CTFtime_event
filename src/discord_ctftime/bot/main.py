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
                nouvel_article = flux.entries[0]
                if dernier_article != nouvel_article.link:

                    event = Rss(nouvel_article)

                    embed = discord.Embed(
                        title=event.titre,
                        url=event.lien,
                        description="Inscris-toi avec ✅ si tu participes !\n ou avec ❓ si tu n'es pas sûr.",
                        colour=discord.Colour.blue()
                    )
                    embed.add_field(name="📆 Début", value=event.date_debut, inline=True)
                    embed.add_field(name="⏰ Fin", value=event.date_fin, inline=True)

                    embed.add_field(name="🏷️ Weight", value=event.weight, inline=False)

                    embed.add_field(name="", value=f"[add calendar](https://ctftime.org/event/{event.ctftime_id}.ics)")

                    embed.add_field(name="", value=f"ID : {event.ctftime_id}")

                    msg = await channel.send(embed=embed)


                    event = self.engine.new_event(
                        ctftime_id=event.ctftime_id,
                        msg_id=msg.id,
                        title=event.titre,
                        url=event.lien,
                        start=event.date_debut,
                        end=event.date_fin,
                        description=nouvel_article.description,
                    )


                    dernier_article = nouvel_article.link

            await asyncio.sleep(CHECK_INTERVAL)

    async def on_reaction_add(
        self,
        reaction: discord.Reaction,
        user: discord.abc.User,
    ):
        if user == self.user:
            return

        if str(reaction.emoji) == OK_EMOJI:
            self.engine.add_participant(reaction.message.id, user.display_name)
            await reaction.message.channel.send(
                f"ℹ️ {user.display_name} Inscrit a : `{self.engine.get_event_info(reaction.message.id)['title']}` {reaction.emoji} ",
                # f"`{reaction.message.id}`"
                delete_after=30,
            )
            return

        if str(reaction.emoji) == MAYBE_EMOJI:
            self.engine.add_maybe_participant(reaction.message.id, user.display_name)
            await reaction.message.channel.send(
                f"ℹ️ {user.display_name} Participera peut etre a : `{self.engine.get_event_info(reaction.message.id)['title']}` {reaction.emoji} ",
                # f"`{reaction.message.id}`"
                delete_after=30,
            )
            return



    async def on_reaction_remove(self, reaction: discord.Reaction, user: discord.abc.User):
        if user == self.user:
            return

        if str(reaction.emoji) == OK_EMOJI:
            self.engine.remove_participant(reaction.message.id, user.display_name)
            await reaction.message.channel.send(
                f"➖ **{user.display_name}** Désinscrit !! {reaction.emoji} ",
                #f"`{reaction.message.id}`"
                delete_after=30,
            )
            return

        if str(reaction.emoji) == MAYBE_EMOJI:
            self.engine.remove_maybe_participant(reaction.message.id, user.display_name)
            await reaction.message.channel.send(
                f"➖ **{user.display_name}** A retiré son \"peut etre\" {reaction.emoji} ",
                #f"`{reaction.message.id}`"
                delete_after=30,
            )
            return



client = Bot(command_prefix="/",intents=intents)

client.run(DISCORD_TOKEN)
