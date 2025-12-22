import discord
from discord import app_commands
from discord.ext import commands, tasks
from collections import deque
import os
from datetime import datetime

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

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
        
        # Listas principais e de espera para cada dungeon
        self.imd_list = []
        self.nightsky_list = []
        self.imd_waitlist = deque()  # Usando deque para fila eficiente
        self.nightsky_waitlist = deque()
        
        # Histórico de notificações para evitar spam
        self.notified_users = set()
        
        # Inicia a tarefa de verificar lista de espera
        self.check_waitlist.start()

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        print(f"🔧 Slash commands sincronizados ({len(synced)} comandos).")
    
    @tasks.loop(seconds=30)  # Verifica a cada 30 segundos
    async def check_waitlist(self):
        """Verifica automaticamente se há vagas nas listas de espera"""
        await self.process_waitlist("IMD", self.imd_list, self.imd_waitlist, LIMIT_IMD)
        await self.process_waitlist("NightSky", self.nightsky_list, self.nightsky_waitlist, LIMIT_NIGHTSKY)
    
    async def process_waitlist(self, dungeon_name, main_list, waitlist, limit):
        """Processa a lista de espera para uma dungeon específica"""
        if not waitlist or len(main_list) >= limit:
            return
        
        # Calcula quantas vagas estão disponíveis
        available_spots = limit - len(main_list)
        
        for _ in range(min(available_spots, len(waitlist))):
            if waitlist:
                user_id = waitlist.popleft()
                try:
                    user = await self.fetch_user(user_id)
                    main_list.append(user.display_name)
                    
                    # Envia DM ao usuário
                    embed = discord.Embed(
                        title="🎉 Vaga Disponível!",
                        description=f"Uma vaga abriu na dungeon **{dungeon_name}**!",
                        color=discord.Color.green(),
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="Status", value=f"✅ Você foi automaticamente adicionado à lista principal", inline=False)
                    embed.add_field(name="Posição", value=f"#{len(main_list)}/{limit}", inline=True)
                    embed.set_footer(text="Use /lista para verificar sua posição")
                    
                    await user.send(embed=embed)
                    print(f"📨 Notificação enviada para {user.display_name} ({dungeon_name})")
                    
                except Exception as e:
                    print(f"❌ Erro ao notificar usuário {user_id}: {e}")
    
    def get_room_data(self, interaction: discord.Interaction):
        """Retorna todos os dados da dungeon baseado no canal"""
        if interaction.channel_id == CANAL_IMD:
            return {
                'main_list': self.imd_list,
                'waitlist': self.imd_waitlist,
                'limit': LIMIT_IMD,
                'name': "IMD",
                'channel_id': CANAL_IMD
            }
        elif interaction.channel_id == CANAL_NIGHTSKY:
            return {
                'main_list': self.nightsky_list,
                'waitlist': self.nightsky_waitlist,
                'limit': LIMIT_NIGHTSKY,
                'name': "NightSky",
                'channel_id': CANAL_NIGHTSKY
            }
        else:
            return None

bot = DungeonBot()

@bot.event
async def on_ready():
    print(f"🤖 Bot online como {bot.user}")
    print(f"📊 Sistema de lista de espera ativo")

# /entrar - COM LISTA DE ESPERA
@bot.tree.command(name="entrar", description="Entrar na lista da dungeon")
async def entrar(interaction: discord.Interaction):
    """Comando para entrar na dungeon ou lista de espera"""
    data = bot.get_room_data(interaction)
    
    if data is None:
        await interaction.response.send_message(
            "🚫 Este canal não possui uma dungeon associada.",
            ephemeral=True
        )
        return
    
    user_id = interaction.user.id
    nick = interaction.user.display_name
    
    # Verifica se já está em alguma lista
    if nick in data['main_list']:
        await interaction.response.send_message("⚠️ Você já está na lista principal!", ephemeral=True)
        return
    
    # Verifica se já está na lista de espera
    if user_id in data['waitlist']:
        await interaction.response.send_message("⚠️ Você já está na lista de espera!", ephemeral=True)
        return
    
    embed = discord.Embed(color=discord.Color.blue(), timestamp=datetime.now())
    
    if len(data['main_list']) < data['limit']:
        # Ainda há vagas na lista principal
        data['main_list'].append(nick)
        embed.title = "✅ Adicionado à Lista Principal"
        embed.description = f"**{nick}** entrou na dungeon **{data['name']}**!"
        embed.add_field(name="Posição", value=f"#{len(data['main_list'])}/{data['limit']}", inline=True)
        embed.add_field(name="Status", value="🎯 Na lista principal", inline=True)
        
    else:
        # Lista principal cheia, vai para lista de espera
        data['waitlist'].append(user_id)
        position = len(data['waitlist'])
        embed.title = "⏳ Adicionado à Lista de Espera"
        embed.description = f"**{nick}** foi para a lista de espera da dungeon **{data['name']}**"
        embed.add_field(name="Posição na fila", value=f"#{position}", inline=True)
        embed.add_field(name="Status", value="🕒 Aguardando vaga", inline=True)
        embed.set_footer(text="Você será notificado por DM quando uma vaga abrir")
    
    # Mostra ambas as listas
    main_text = "\n".join([f"{i+1}. {n}" for i, n in enumerate(data['main_list'])]) or "📭 Vazia"
    waitlist_text = "\n".join([f"{i+1}. <@{uid}>" for i, uid in enumerate(data['waitlist'])]) or "📭 Vazia"
    
    embed.add_field(
        name=f"📋 Lista Principal ({len(data['main_list'])}/{data['limit']})",
        value=main_text[:1024],
        inline=False
    )
    
    embed.add_field(
        name=f"⏳ Lista de Espera ({len(data['waitlist'])})",
        value=waitlist_text[:1024] if len(waitlist_text) <= 1024 else f"{len(data['waitlist'])} pessoas aguardando",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

# /lista - MOSTRA AMBAS AS LISTAS
@bot.tree.command(name="lista", description="Mostrar lista da dungeon com lista de espera")
async def lista(interaction: discord.Interaction):
    data = bot.get_room_data(interaction)
    
    if data is None:
        await interaction.response.send_message(
            "🚫 Este canal não possui uma dungeon associada.",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title=f"📊 Dungeon {data['name']}",
        color=discord.Color.gold(),
        timestamp=datetime.now()
    )
    
    # Lista principal
    if data['main_list']:
        main_text = "\n".join([f"{i+1}. {n}" for i, n in enumerate(data['main_list'])])
        embed.add_field(
            name=f"🛡️ Lista Principal ({len(data['main_list'])}/{data['limit']})",
            value=main_text,
            inline=False
        )
    else:
        embed.add_field(
            name=f"🛡️ Lista Principal (0/{data['limit']})",
            value="📭 Ninguém na lista",
            inline=False
        )
    
    # Lista de espera
    if data['waitlist']:
        waitlist_names = []
        for i, user_id in enumerate(data['waitlist']):
            try:
                user = await bot.fetch_user(user_id)
                waitlist_names.append(f"{i+1}. {user.display_name}")
            except:
                waitlist_names.append(f"{i+1}. <@{user_id}>")
        
        waitlist_text = "\n".join(waitlist_names)
        embed.add_field(
            name=f"⏳ Lista de Espera ({len(data['waitlist'])})",
            value=waitlist_text[:1024],
            inline=False
        )
    else:
        embed.add_field(
            name="⏳ Lista de Espera",
            value="📭 Ninguém na lista de espera",
            inline=False
        )
    
    embed.set_footer(text=f"Use /entrar para se juntar à dungeon")
    await interaction.response.send_message(embed=embed)

# /sair - REMOVE DE AMBAS AS LISTAS
@bot.tree.command(name="sair", description="Sair da lista da dungeon ou lista de espera")
async def sair(interaction: discord.Interaction):
    data = bot.get_room_data(interaction)
    
    if data is None:
        await interaction.response.send_message(
            "🚫 Este canal não possui uma dungeon associada.",
            ephemeral=True
        )
        return
    
    user_id = interaction.user.id
    nick = interaction.user.display_name
    removed_from = []
    
    # Remove da lista principal
    if nick in data['main_list']:
        data['main_list'].remove(nick)
        removed_from.append("lista principal")
    
    # Remove da lista de espera
    if user_id in data['waitlist']:
        data['waitlist'] = deque([uid for uid in data['waitlist'] if uid != user_id])
        removed_from.append("lista de espera")
    
    if removed_from:
        await interaction.response.send_message(
            f"🚪 **{nick}** saiu da {' e '.join(removed_from)} da dungeon **{data['name']}**."
        )
    else:
        await interaction.response.send_message(
            "❌ Você não está em nenhuma lista desta dungeon.",
            ephemeral=True
        )

# /mover - COMANDO ADMIN PARA MOVER PESSOAS
@bot.tree.command(name="mover", description="Mover usuário para lista principal (admin)")
@app_commands.checks.has_permissions(administrator=True)
async def mover(interaction: discord.Interaction, usuario: discord.Member):
    """Move um usuário da lista de espera para a lista principal"""
    data = bot.get_room_data(interaction)
    
    if data is None:
        await interaction.response.send_message(
            "🚫 Este canal não possui uma dungeon associada.",
            ephemeral=True
        )
        return
    
    if usuario.id not in data['waitlist']:
        await interaction.response.send_message(
            f"❌ {usuario.display_name} não está na lista de espera.",
            ephemeral=True
        )
        return
    
    if len(data['main_list']) >= data['limit']:
        await interaction.response.send_message(
            f"❌ A lista principal está cheia ({data['limit']}/{data['limit']})",
            ephemeral=True
        )
        return
    
    # Remove da lista de espera e adiciona à principal
    data['waitlist'] = deque([uid for uid in data['waitlist'] if uid != usuario.id])
    data['main_list'].append(usuario.display_name)
    
    embed = discord.Embed(
        title="🔄 Usuário Movido",
        description=f"**{usuario.display_name}** foi movido para a lista principal",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    embed.add_field(name="Lista Principal", value=f"{len(data['main_list'])}/{data['limit']}", inline=True)
    embed.add_field(name="Lista de Espera", value=f"{len(data['waitlist'])}", inline=True)
    
    await interaction.response.send_message(embed=embed)

# /limparespera - LIMPAR LISTA DE ESPERA
@bot.tree.command(name="limparespera", description="Limpar lista de espera (admin)")
@app_commands.checks.has_permissions(administrator=True)
async def limparespera(interaction: discord.Interaction):
    data = bot.get_room_data(interaction)
    
    if data is None:
        await interaction.response.send_message(
            "🚫 Este canal não possui uma dungeon associada.",
            ephemeral=True
        )
        return
    
    count = len(data['waitlist'])
    data['waitlist'].clear()
    
    await interaction.response.send_message(
        f"🧹 Lista de espera da dungeon **{data['name']}** foi limpa! ({count} pessoas removidas)"
    )

# /info - INFORMAÇÕES DO USUÁRIO
@bot.tree.command(name="info", description="Ver sua posição nas listas")
async def info(interaction: discord.Interaction):
    """Mostra a posição do usuário em todas as dungeons"""
    user_id = interaction.user.id
    nick = interaction.user.display_name
    
    embed = discord.Embed(
        title=f"📊 Suas Inscrições",
        description=f"**Usuário:** {nick}",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    # Verifica IMD
    imd_data = {
        'main_list': bot.imd_list,
        'waitlist': bot.imd_waitlist,
        'limit': LIMIT_IMD,
        'name': "IMD"
    }
    
    # Verifica NightSky
    nightsky_data = {
        'main_list': bot.nightsky_list,
        'waitlist': bot.nightsky_waitlist,
        'limit': LIMIT_NIGHTSKY,
        'name': "NightSky"
    }
    
    for data in [imd_data, nightsky_data]:
        status = "❌ Não inscrito"
        
        if nick in data['main_list']:
            position = data['main_list'].index(nick) + 1
            status = f"✅ **Lista Principal** - Posição #{position}/{data['limit']}"
        elif user_id in data['waitlist']:
            position = list(data['waitlist']).index(user_id) + 1
            status = f"⏳ **Lista de Espera** - Posição #{position}"
        
        embed.add_field(
            name=f"Dungeon {data['name']}",
            value=f"{status}\nPrincipal: {len(data['main_list'])}/{data['limit']}\nEspera: {len(data['waitlist'])}",
            inline=False
        )
    
    embed.set_footer(text="Use /entrar no canal da dungeon para se inscrever")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Mantém os comandos originais limpar e limparchat
@bot.tree.command(name="limpar", description="Limpar lista da dungeon (admin)")
@app_commands.checks.has_permissions(administrator=True)
async def limpar(interaction: discord.Interaction):
    data = bot.get_room_data(interaction)
    
    if data is None:
        await interaction.response.send_message(
            "🚫 Este canal não possui uma dungeon associada.",
            ephemeral=True
        )
        return
    
    data['main_list'].clear()
    await interaction.response.send_message(
        f"🧹 Lista principal da dungeon **{data['name']}** foi limpa!"
    )

@bot.tree.command(name="limparchat", description="Limpar mensagens do canal (admin)")
@app_commands.checks.has_permissions(administrator=True)
async def limparchat(interaction: discord.Interaction, quantidade: int = 50):
    if interaction.channel_id not in [CANAL_IMD, CANAL_NIGHTSKY]:
        await interaction.response.send_message(
            "🚫 Este canal não está autorizado a usar este comando.",
            ephemeral=True
        )
        return
    
    if quantidade > 100:
        quantidade = 100
    
    await interaction.response.send_message(
        f"🧹 Limpando **{quantidade}** mensagens...",
        ephemeral=True
    )
    
    deletadas = await interaction.channel.purge(limit=quantidade)
    
    await interaction.followup.send(
        f"✅ Foram apagadas **{len(deletadas)}** mensagens!",
        ephemeral=True
    )

# Tratamento de erros
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ Você não tem permissão para usar este comando.",
            ephemeral=True
        )
    else:
        print(f"Erro no comando: {error}")
        await interaction.response.send_message(
            "❌ Ocorreu um erro ao executar o comando.",
            ephemeral=True
        )

# Iniciar bot
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)