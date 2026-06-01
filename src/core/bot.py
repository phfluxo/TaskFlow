import os
import json
import asyncio
import discord
from discord.ext import commands
from github import Github

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