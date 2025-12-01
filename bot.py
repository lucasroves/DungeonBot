import discord
from discord import app_commands
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.members = True

CLIENT_ID = 1444915208668844074
GUILD_ID = 1428159266598158522

# IDs dos canais
CANAL_IMD = 1445085686112845885
CANAL_NIGHTSKY = 1430611404204806174

# Limites
LIMIT_IMD = 20
LIMIT_NIGHTSKY = 8


class DungeonBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            application_id=CLIENT_ID
        )

        # DUAS LISTAS SEPARADAS
        self.imd_list = []
        self.nightsky_list = []

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        print(f"🔧 Slash commands sincronizados ({len(synced)} comandos).")


bot = DungeonBot()


@bot.event
async def on_ready():
    print(f"🤖 Bot online como {bot.user}")


# Função para obter lista e limite conforme canal
def get_room(interaction: discord.Interaction):
    if interaction.channel_id == CANAL_IMD:
        return bot.imd_list, LIMIT_IMD, "IMD"
    elif interaction.channel_id == CANAL_NIGHTSKY:
        return bot.nightsky_list, LIMIT_NIGHTSKY, "NightSky"
    else:
        return None, None, None


# /entrar
@bot.tree.command(name="entrar", description="Entrar na lista da dungeon")
async def entrar(interaction: discord.Interaction):

    lista, limite, nome = get_room(interaction)

    if lista is None:
        await interaction.response.send_message(
            "🚫 Este canal não possui uma dungeon associada.",
            ephemeral=True
        )
        return

    nick = interaction.user.display_name

    if nick in lista:
        await interaction.response.send_message("⚠️ Você já está na lista!", ephemeral=True)
        return

    if len(lista) >= limite:
        await interaction.response.send_message(f"❌ A dungeon {nome} está cheia ({limite}).", ephemeral=True)
        return

    lista.append(nick)
    texto = "\n".join([f"{i+1}. {n}" for i, n in enumerate(lista)])

    await interaction.response.send_message(
        f"✅ {nick} entrou na dungeon **{nome}**!\n\n🛡️ **Lista ({len(lista)}/{limite}):**\n{texto}"
    )


# /lista
@bot.tree.command(name="lista", description="Mostrar lista da dungeon")
async def lista(interaction: discord.Interaction):

    lista, limite, nome = get_room(interaction)

    if lista is None:
        await interaction.response.send_message(
            "🚫 Este canal não possui uma dungeon associada.",
            ephemeral=True
        )
        return

    if not lista:
        await interaction.response.send_message(f"📭 A lista da dungeon **{nome}** está vazia!")
        return

    texto = "\n".join([f"{i+1}. {n}" for i, n in enumerate(lista)])
    await interaction.response.send_message(f"🛡️ **Lista da dungeon {nome} ({len(lista)}/{limite}):**\n{texto}")


# /sair
@bot.tree.command(name="sair", description="Sair da lista da dungeon")
async def sair(interaction: discord.Interaction):

    lista, limite, nome = get_room(interaction)

    if lista is None:
        await interaction.response.send_message(
            "🚫 Este canal não possui uma dungeon associada.",
            ephemeral=True
        )
        return

    nick = interaction.user.display_name

    if nick not in lista:
        await interaction.response.send_message("❌ Você não está na lista.", ephemeral=True)
        return

    lista.remove(nick)
    await interaction.response.send_message(f"🚪 {nick} saiu da dungeon **{nome}**.")


# /limpar (admin)
@bot.tree.command(name="limpar", description="Limpar lista da dungeon (admin)")
@app_commands.checks.has_permissions(administrator=True)
async def limpar(interaction: discord.Interaction):

    lista, limite, nome = get_room(interaction)

    if lista is None:
        await interaction.response.send_message(
            "🚫 Este canal não possui uma dungeon associada.",
            ephemeral=True
        )
        return

    lista.clear()
    await interaction.response.send_message(f"🧹 Lista da dungeon **{nome}** foi limpa!")

# 🚀 INICIA O BOT
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
