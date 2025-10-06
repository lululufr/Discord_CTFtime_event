import discord


class Group():
    def __init__(self, interaction: discord.Interaction,CATEGORY_ID:int):
        self.interaction = interaction
        self.category = interaction.guild.get_channel(CATEGORY_ID)
        self.guild = interaction.guild
        return

    async def new_group(self, nom: str):
        # Vérifie si le rôle existe déjà
        role = discord.utils.get(self.interaction.guild.roles, name=nom)

        if role is None:
            # Crée un rôle avec couleur grise
            role = await self.guild.create_role(
                name=nom,
                colour=discord.Colour.greyple(),
                reason=f"Création par bot : {self.interaction.user}, pour l'event : {nom}"
            )

        # met les perms seulement sur le salon
        overwrites = {
            self.guild.default_role: discord.PermissionOverwrite(view_channel=False),  # @everyone ne voit pas
            role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            self.interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        # verifie si le saloon existe : 
        existing_channel = discord.utils.get(self.guild.text_channels, name=nom)

        if existing_channel is None:
            # Crée le salon texte privé
            channel = await self.guild.create_text_channel(
                name=nom,
                overwrites=overwrites,
                category=self.category,
                reason=f"Salon privé pour le groupe {nom}"
            )

            await self.interaction.response.send_message(
                f"✅ Groupe **{nom}** créé avec succès !\nSalon : {channel.mention}",
                ephemeral=False
            )

        else:
            await self.interaction.response.send_message(
                f"ℹ️ Le salon **{existing_channel.mention}** existe déjà pour le groupe **{nom}**.",
                ephemeral=True
            )


    async def add_member(self, membre: discord.Member, group_name: str):
        role = discord.utils.get(self.guild.roles, name=group_name)

        if role is None:
            await self.interaction.response.send_message(f"❌ Le rôle **{group_name}** n’existe pas.")
            return

        await Group.add_member_group(self.interaction, membre, role)

    

    #TODO: faire un garbage collector des vieux groupes
    async def clean_group(self):
        return
