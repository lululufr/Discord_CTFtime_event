import discord
from discord.ext import commands
import asyncio
import feedparser
from src.discord_ctftime.event import Event, Engine
from command import setup_commands

import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN  = os.getenv("DISCORD_TOKEN")
CHANNEL_ID     = int(os.getenv("CHANNEL_ID"))
RSS_URL        = os.getenv("RSS_URL")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 30))

#DEFINE EMOJI REACTION
OK_EMOJI = "✅"
MAYBE_EMOJI = ""

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

        # 2) lance la tâche de surveillance RSS
        self.bg_task = asyncio.create_task(self.check_rss())

    async def on_ready(self):
        print(f"✅ Connecté en tant que {self.user}")

    # ─────────────────────────── RSS ───────────────────────────
    async def check_rss(self):
        global dernier_article
        await self.wait_until_ready()
        channel = self.get_channel(CHANNEL_ID)

        while True:
            flux = feedparser.parse(RSS_URL)
            if flux.entries:
                nouvel_article = flux.entries[0]
                if dernier_article != nouvel_article.link:
                    titre = nouvel_article.title
                    lien  = nouvel_article.link
                    summary = nouvel_article.summary

                    date_debut = nouvel_article.summary.split("\n")[1].split(";")[0].replace("Date:","").replace("&mdash","").strip()
                    date_fin = nouvel_article.summary.split("\n")[1].split(";")[1].replace("Date:","").replace("&nbsp","").strip()

                    weight = nouvel_article.summary.split("\n")[6].replace("<br />:","").strip()

                    debug = str(nouvel_article)


                    ctftime_id = nouvel_article.id.split("/")[-1]  # ID CTFTIME à partir du lien

                    # 1) envoie le message
                    embed = discord.Embed(
                        title=titre,
                        url=lien,  # le titre devient cliquable
                        description="Inscris-toi avec ✅ si tu participes !",
                        colour=discord.Colour.blue()
                    )
                    embed.add_field(name="📆 Début", value=date_debut, inline=True)
                    embed.add_field(name="⏰ Fin", value=date_fin, inline=True)
                    embed.add_field(name="🏷️ Weight", value=weight, inline=True)

                    embed.add_field(name="ID", value=ctftime_id)

                    msg = await channel.send(embed=embed)




                    event = Event(
                        ctftime_id=ctftime_id,
                        msg_id=msg.id,
                        title=titre,
                        url=lien,
                        start="a venir",
                        end="à venir",
                        description=nouvel_article.description,
                    )


                    dernier_article = nouvel_article.link

            await asyncio.sleep(CHECK_INTERVAL)

    async def on_reaction_add(
        self,
        reaction: discord.Reaction,
        user: discord.abc.User,
    ):
        if user == self.user:                              # ignore le bot lui-même
            return

        if str(reaction.emoji) == OK_EMOJI:
            self.engine.add_participant(reaction.message.id, user.display_name)
            await reaction.message.channel.send(
                f"ℹ️ {user.display_name} Inscrit a : `{self.engine.get_event_info_by_msgid(reaction.message.id)['title']}` {reaction.emoji} "
            )
            return



    async def on_reaction_remove(self, reaction: discord.Reaction, user: discord.abc.User):
        if user == self.user:
            return

        if str(reaction.emoji) == OK_EMOJI:
            self.engine.remove_participant(reaction.message.id, user.display_name)
            await reaction.message.channel.send(
                f"➖ **{user.display_name}** Désinscrit !! {reaction.emoji} "
                f"`{reaction.message.id}`"
            )
            return



client = Bot(command_prefix="!",intents=intents)

client.run(DISCORD_TOKEN)
