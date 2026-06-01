import os
import json
import sqlite3
import discord
from discord.ext import commands
from src.utils.permissions import is_staff

# Configuração do caminho do banco de dados dentro do volume persistente
DB_DIR = "data"
DB_FILE = os.path.join(DB_DIR, "users.db")

# --- FUNÇÕES AUXILIARES DE PERSISTÊNCIA (SQLITE) ---
def init_db() -> None:
    """Garante que o diretório data/ e a tabela de usuários existam no banco."""
    os.makedirs(DB_DIR, exist_ok=True)
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                discord_name TEXT PRIMARY KEY,
                github_name TEXT NOT NULL
            )
        """)
        conn.commit()

def get_users() -> dict:
    """Busca todos os usuários e retorna no formato de dicionário {discord: github}."""
    init_db()
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT discord_name, github_name FROM users")
        return {row[0]: row[1] for row in cursor.fetchall()}

def add_user(discord_name: str, github_name: str, overwrite: bool = False) -> bool:
    """Adiciona um usuário. Retorna True se adicionado/atualizado e False se ignorado."""
    init_db()
    with sqlite3.connect(DB_FILE) as conn:
        try:
            if overwrite:
                conn.execute(
                    "INSERT OR REPLACE INTO users (discord_name, github_name) VALUES (?, ?)", 
                    (discord_name, github_name)
                )
            else:
                conn.execute(
                    "INSERT INTO users (discord_name, github_name) VALUES (?, ?)", 
                    (discord_name, github_name)
                )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def delete_users(names_to_delete: list[str]) -> None:
    """Remove múltiplos usuários de uma única vez do banco de dados."""
    init_db()
    with sqlite3.connect(DB_FILE) as conn:
        conn.executemany("DELETE FROM users WHERE discord_name = ?", [(name,) for name in names_to_delete])
        conn.commit()


# --- MODAL DE CADASTRO INDIVIDUAL ---
class RegisterModal(discord.ui.Modal, title="Vincular Conta do GitHub"):
    github_username = discord.ui.TextInput(
        label="Seu Username do GitHub",
        placeholder="Digite exatamente seu nick do GitHub...",
        required=True,
        max_length=40
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        discord_name = interaction.user.name
        
        # Salva forçando o overwrite caso ele decida atualizar o nick dele
        add_user(discord_name, self.github_username.value, overwrite=True)
        await interaction.response.send_message(
            f"✅ Sucesso! Seu perfil foi vinculado ao GitHub `{self.github_username.value}`.", 
            ephemeral=True
        )


# --- MODAL DE CADASTRO EM MASSA (TEXTO/VÍRGULA) ---
class BulkRegisterModal(discord.ui.Modal, title="Cadastro em Massa"):
    discord_names = discord.ui.TextInput(
        label="Nomes do Discord (separados por vírgula)",
        style=discord.TextStyle.paragraph,
        placeholder="Ex: fulanoDisc, johnDoe99",
        required=True
    )
    github_names = discord.ui.TextInput(
        label="Nomes do GitHub (separados por vírgula)",
        style=discord.TextStyle.paragraph,
        placeholder="Ex: fulanGit, johnDoeGitHub",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        discord_list = [name.strip() for name in self.discord_names.value.split(",") if name.strip()]
        github_list = [name.strip() for name in self.github_names.value.split(",") if name.strip()]

        if len(discord_list) != len(github_list):
            await interaction.response.send_message(
                f"❌ **Erro de correspondência!**\n"
                f"Você enviou {len(discord_list)} nomes de Discord e {len(github_list)} nomes de GitHub. "
                f"As quantidades precisam ser exatamente iguais.",
                ephemeral=True
            )
            return

        added = 0
        ignored = 0

        for discord_name, github_name in zip(discord_list, github_list):
            # Se já existir, a restrição UNIQUE do SQLite impede e retorna False
            if add_user(discord_name, github_name, overwrite=False):
                added += 1
            else:
                ignored += 1
        
        await interaction.response.send_message(
            f"✅ **Cadastro em massa concluído!**\n"
            f"🆕 **Novos usuários:** {added}\n"
            f"⚠️ **Ignorados (já cadastrados):** {ignored}",
            ephemeral=True
        )


# --- MODAL DE IMPORTAÇÃO VIA JSON ---
class ImportJsonModal(discord.ui.Modal, title="Importar Usuários via JSON"):
    json_data = discord.ui.TextInput(
        label="Cole o Dicionário JSON",
        style=discord.TextStyle.paragraph,
        placeholder='{\n    "fulanoDisc": "fulanGit",\n    "johnDisc": "johnGit"\n}',
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            new_users = json.loads(self.json_data.value)
            if not isinstance(new_users, dict):
                await interaction.response.send_message(
                    "❌ **Erro de formato!** O JSON enviado precisa ser um dicionário/objeto estruturado em `{ \"chave\": \"valor\" }`.",
                    ephemeral=True
                )
                return
        except json.JSONDecodeError:
            await interaction.response.send_message(
                "❌ **Erro de Sintaxe JSON!** Certifique-se de que usou aspas duplas `\"` em vez de aspas simples `'` e validou as vírgulas.",
                ephemeral=True
            )
            return

        added = 0
        ignored = 0

        for discord_name, github_name in new_users.items():
            if add_user(discord_name, str(github_name), overwrite=False):
                added += 1
            else:
                ignored += 1

        await interaction.response.send_message(
            f"✅ **Importação JSON concluída!**\n"
            f"🆕 **Novos usuários adicionados:** {added}\n"
            f"⚠️ **Ignorados (já cadastrados):** {ignored}",
            ephemeral=True
        )


# --- VIEWS DE CONFIRMAÇÃO E LISTAGEM ---
class DeleteConfirmationView(discord.ui.View):
    def __init__(self, names_to_delete: list[str]):
        super().__init__(timeout=60)
        self.names_to_delete = names_to_delete

    @discord.ui.button(label="Sim, Deletar", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        delete_users(self.names_to_delete)
        await interaction.response.edit_message(
            content=f"🗑️ Os seguintes cadastros foram excluídos: **{', '.join(self.names_to_delete)}**", 
            view=None
        )

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ListUsersView(users_dict=get_users())
        await interaction.response.edit_message(
            content="### 👥 Gerenciador de Usuários Cadastrados\nSelecione um ou mais usuários abaixo para deletar:", 
            view=view
        )


class ListUsersView(discord.ui.View):
    def __init__(self, users_dict: dict):
        super().__init__(timeout=180)
        self.users_dict = users_dict
        self.selected = []

        options = [
            discord.SelectOption(label=discord_name, value=discord_name, description=f"GitHub: {github_name}")
            for discord_name, github_name in list(users_dict.items())[:25]
        ]
        
        self.select = discord.ui.Select(
            placeholder="Selecione os usuários que deseja apagar...",
            min_values=1,
            max_values=len(options),
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        self.selected = self.select.values
        await interaction.response.defer()

    @discord.ui.button(label="Deletar Selecionados", style=discord.ButtonStyle.danger, row=1)
    async def delete_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected:
            await interaction.response.send_message("⚠️ Selecione pelo menos um usuário na lista acima!", ephemeral=True)
            return

        confirm_view = DeleteConfirmationView(self.selected)
        await interaction.response.edit_message(
            content=f"⚠️ **Confirmação:** Tem certeza de que deseja apagar o vínculo de: **{', '.join(self.selected)}**?",
            view=confirm_view
        )


# --- COG DE GERENCIAMENTO DE MEMBROS ---
class UserCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="registrar-se", description="Vincula seu usuário do GitHub ao sistema do bot")
    async def register(self, ctx: commands.Context) -> None:
        if ctx.interaction:
            users = get_users()
            if ctx.author.name in users:
                await ctx.send("❌ Você já possui um cadastro ativo! Para alterar, use `/unregister` primeiro.", ephemeral=True)
                return
            await ctx.interaction.response.send_modal(RegisterModal())
        else:
            await ctx.send("⚠️ Por limitações do Discord, use este comando as Slash Command: `/registrar-se`.")

    @commands.hybrid_command(name="desregistrar-se", description="Remove o seu cadastro do sistema do bot")
    async def unregister(self, ctx: commands.Context) -> None:
        users = get_users()
        user_name = ctx.author.name
        if user_name in users:
            delete_users([user_name])
            await ctx.send("✅ Seu cadastro foi removido com sucesso.", ephemeral=True)
        else:
            await ctx.send("❌ Você não foi encontrado no nosso banco de cadastros.", ephemeral=True)

    @commands.hybrid_command(name="cadastrar_usuarios_formulario", description="[Admin] Cadastra vários usuários de uma vez (Vírgulas)")
    @is_staff()
    async def register_users(self, ctx: commands.Context) -> None:
        if ctx.interaction:
            await ctx.interaction.response.send_modal(BulkRegisterModal())
        else:
            await ctx.send("⚠️ Por limitações do Discord, use este comando as Slash Command: `/cadastrar_usuarios_formulario`.")

    @commands.hybrid_command(name="importar_usuarios_json", description="[Admin] Importa um dicionário JSON bruto contendo os mapeamentos de usuários")
    @is_staff()
    async def import_users_json(self, ctx: commands.Context) -> None:
        if ctx.interaction:
            await ctx.interaction.response.send_modal(ImportJsonModal())
        else:
            await ctx.send("⚠️ Por limitações do Discord, use este comando as Slash Command: `/importar_usuarios_json`.")

    @commands.hybrid_command(name="listar_usuarios", description="[Admin] Lista e remove usuários cadastrados")
    @is_staff()
    async def list_users(self, ctx: commands.Context) -> None:
        users = get_users()
        if not users:
            await ctx.send("📂 Nenhum usuário cadastrado no momento.", ephemeral=True)
            return
            
        view = ListUsersView(users_dict=users)
        await ctx.send(
            "### 👥 Gerenciador de Usuários Cadastrados\nSelecione um ou mais usuários abaixo para deletar:", 
            view=view, 
            ephemeral=True
        )

    @commands.hybrid_command(name="print_users", description="[Admin] Exibe o conteúdo atual do banco para backup (Formato JSON)")
    @is_staff()
    async def print_users(self, ctx: commands.Context) -> None:
        users = get_users()
        if not users:
            await ctx.send("📂 O banco de dados está vazio. Nenhum usuário cadastrado.", ephemeral=True)
            return

        json_formatted = json.dumps(users, indent=4, ensure_ascii=False)
        backup_message = (
            "### 💾 Backup de Usuários Cadastrados (`users.db` -> JSON)\n"
            "Copie o bloco abaixo se desejar transferir ou salvar estes dados:\n"
            f"```json\n{json_formatted}\n```")
        await ctx.send(backup_message, ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UserCog(bot))