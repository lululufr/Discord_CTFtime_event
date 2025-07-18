import discord
from discord.ext import commands
import asyncio
import feedparser
from src.discord_ctftime.event import Engine
#from src.discord_ctftime.ctftime import CTFtime

from src.discord_ctftime.bot.command import setup_commands


import src.discord_ctftime.bot.dashboard

import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN  = os.getenv("DISCORD_TOKEN")
CHANNEL_ID     = int(os.getenv("CHANNEL_ID"))
RSS_URL        = os.getenv("RSS_URL")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 30))
SERVER_ID = int(os.getenv("SERVER_ID", None))  
DEEP_EVENT = int(os.getenv("DEEP_EVENT", 15)) 

#DEFINE EMOJI REACTION
OK_EMOJI = os.getenv("OK_EMOJI")
MAYBE_EMOJI = os.getenv("MAYBE_EMOJI")
NOT_EMOJI = os.getenv("NOT_EMOJI")

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

        self.channel = self.get_channel(CHANNEL_ID)
        if self.channel is None:                          
            self.channel = await self.fetch_channel(CHANNEL_ID)

        # enregistre toutes les commandes
        setup_commands(self, self.engine, self.channel)

        #dashbaord
        await self.load_extension("src.discord_ctftime.bot.dashboard")

        guild = discord.Object(id=SERVER_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)


    async def on_ready(self):
        print(f"✅ Connecté en tant que {self.user}")

    async def add_default_reactions(self, message: discord.Message) -> None:
        for emoji in (OK_EMOJI, MAYBE_EMOJI,NOT_EMOJI):
            try:
                await message.add_reaction(emoji)
            except discord.HTTPException:
                pass
            

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
