import os
import json
import asyncio
import traceback
import discord
from discord.ext import commands
from github import Github
from src.utils.permissions import PERMITTED_ROLES

class GitHubTaskBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix="!", intents=discord.Intents.default())
        self.repositorios_disponiveis: list[tuple[str, str]] = []

    async def setup_hook(self) -> None:
        # 1. Carrega os repositórios dinamicamente antes de abrir os comandos
        await self.load_repositories()
        
        # 2. Carrega o Cog usando o novo caminho do diretório 'src'
        await self.load_extension('src.cogs.task_commands')
        await self.load_extension('src.cogs.user_commands')
        
        # 3. Sincroniza os comandos de barra
        await self.tree.sync()
        print(f"🤖 {self.user} configurado e comandos sincronizados!")

    async def load_repositories(self) -> None:
        auto_discover = os.getenv('AUTO_DISCOVER_REPOS', 'false').lower() == 'true'
        github_token = os.getenv('GITHUB_TOKEN')
        org_name = os.getenv('GITHUB_ORG')

        if not github_token:
            print("❌ Erro: GITHUB_TOKEN não encontrado no ambiente.")
            return

        gh = Github(github_token)

        if auto_discover:
            print("🔍 Buscando repositórios automaticamente no GitHub...")
            try:
                def fetch_repos() -> list[tuple[str, str]]:
                    # Se houver uma Org configurada, busca dela. Se não, busca do usuário do token.
                    target = gh.get_organization(org_name) if org_name else gh.get_user()
                    
                    repos = []
                    for r in target.get_repos():
                        # Filtro: Apenas repositórios onde o bot realmente consegue criar Issues (permissão de push)
                        if r.permissions.push:
                            repos.append((r.name, r.full_name))
                        
                        # Limite do dropdown do Discord
                        if len(repos) >= 25:
                            break
                    return repos

                # Roda a busca síncrona do PyGithub em uma thread separada (Non-blocking)
                self.repositorios_disponiveis = await asyncio.to_thread(fetch_repos)
                print(f"✅ {len(self.repositorios_disponiveis)} repositórios descobertos automaticamente via API.")
                return
            except Exception as e:
                print(f"⚠️ Falha na descoberta automática ({e}). Mudando para o modo manual...")
                auto_discover = False

        # --- MODO MANUAL (FALLBACK) ---
        if not auto_discover:
            print("📝 Carregando repositórios manualmente através do .env...")
            git_repos_str = os.getenv('GIT_REPOS', '{}')
            try:
                repos_dict = json.loads(git_repos_str)
                self.repositorios_disponiveis = list(repos_dict.items())[:25]
                print(f"✅ {len(self.repositorios_disponiveis)} repositórios manuais carregados.")
            except json.JSONDecodeError:
                print("❌ Erro: Formato JSON inválido na variável GIT_REPOS.")
                self.repositorios_disponiveis = []


    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Captura e trata erros de TODOS os comandos e Cogs do sistema."""
        
        if hasattr(error, "original"):
            error = error.original

        if isinstance(error, commands.MissingPermissions):
            mensagem_erro = (
                "❌ **Acesso Negado!**\n"
                "Você não tem os privilégios necessários para executar este comando.\n"
                f"👉 Este comando é restrito a **Administradores** ou membros com os cargos **{', '.join(PERMITTED_ROLES)}**."
            )
            await self._enviar_resposta_erro(ctx, mensagem_erro)
            return

        # 2. Tratamento para comando não encontrado (Evita logs se digitarem algo errado com prefixo !)
        if isinstance(error, commands.CommandNotFound):
            return

        # 3. Qualquer outro erro não previsto (Gera log detalhado no terminal para você debugar)
        print(f"🔴 Erro não tratado no comando '{ctx.command}': {error}")
        traceback.print_exception(type(error), error, error.__traceback__)

    # --- FUNÇÃO AUXILIAR DE RESPOSTA ---
    async def _enviar_resposta_erro(self, ctx: commands.Context, texto: str) -> None:
        """Garante que a resposta vá como Slash (ephemeral) ou mensagem normal com auto-delete."""
        if ctx.interaction:
            # Se for um Slash Command, responde de forma privada (apenas o usuário vê)
            if not ctx.interaction.response.is_done():
                await ctx.interaction.response.send_message(texto, ephemeral=True)
            else:
                await ctx.interaction.followup.send(texto, ephemeral=True)
        else:
            # Se for comando por texto antigo (!print_users), manda no chat e apaga após 15 segundos
            await ctx.send(texto, delete_after=15)