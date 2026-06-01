import os
import json
import discord
import requests  # Utilizado para a API GraphQL do GitHub
from discord.ext import commands
from github import Github
from src.templates.task_layouts import build_standard_template

# Inicializa o cliente do GitHub
gh = Github(os.getenv('GITHUB_TOKEN'))
USER_FILE = "users.json"

def get_users() -> dict:
    if not os.path.exists(USER_FILE):
        return {}
    with open(USER_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

# --- FUNÇÃO AUXILIAR: VINCIULAÇÃO COM PROJECTS V2 (GRAPHQL) ---
def link_to_project_v2(issue_node_id: str) -> None:
    token = os.getenv('GITHUB_TOKEN')
    project_num_str = os.getenv('GITHUB_PROJECT_NUMBER')
    org_name = os.getenv('GITHUB_ORG')
    
    if not token or not project_num_str:
        print("ℹ️ Integração com Project Board ignorada: GITHUB_PROJECT_NUMBER não configurado.")
        return
        
    try:
        project_number = int(project_num_str)
        headers = {"Authorization": f"Bearer {token}"}
        url = "https://api.github.com/graphql"
        
        # 1. Busca o ID global (Node ID) do quadro de projeto v2
        if org_name:
            query_find_project = """
            query($org: String!, $num: Int!) {
              organization(login: $org) {
                projectV2(number: $num) {
                  id
                }
              }
            }
            """
            variables = {"org": org_name, "num": project_number}
        else:
            # Fallback para projetos de contas pessoais (User) se não houver Org definida
            query_find_project = """
            query($num: Int!) {
              viewer {
                projectV2(number: $num) {
                  id
                }
              }
            }
            """
            variables = {"num": project_number}
            
        response = requests.post(url, json={"query": query_find_project, "variables": variables}, headers=headers)
        res_data = response.json()
        
        if "errors" in res_data:
            print(f"⚠️ Erro ao buscar ID do projeto no GitHub: {res_data['errors']}")
            return
            
        if org_name:
            project_node_id = res_data["data"]["organization"]["projectV2"]["id"]
        else:
            project_node_id = res_data["data"]["viewer"]["projectV2"]["id"]
            
        # 2. Insere a Issue recém-criada para dentro do Projeto localizado
        mutation_add_item = """
        mutation($projectId: ID!, $contentId: ID!) {
          addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
            item {
              id
            }
          }
        }
        """
        mutation_vars = {"projectId": project_node_id, "contentId": issue_node_id}
        mut_response = requests.post(url, json={"query": mutation_add_item, "variables": mutation_vars}, headers=headers)
        mut_data = mut_response.json()
        
        if "errors" in mut_data:
            print(f"⚠️ Erro ao linkar a task dentro do Project Board: {mut_data['errors']}")
        else:
            print("📋 Task adicionada com sucesso ao Project Board v2!")
            
    except Exception as e:
        print(f"⚠️ Falha inesperada na integração com o Project Board: {e}")


# --- DROPDOWN 2: SELEÇÃO DE REPOSITÓRIO ---
class RepoSelect(discord.ui.Select):
    def __init__(self, repos: list[tuple[str, str]], assignee: str | None):
        options = [discord.SelectOption(label=name, value=repo) for name, repo in repos]
        super().__init__(placeholder="Escolha o repositório destino...", options=options)
        self.assignee = assignee

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(TaskModal(repo_path=self.values[0], assignee=self.assignee))
        await interaction.delete_original_response()


# --- DROPDOWN 1: SELEÇÃO DE RESPONSÁVEL (ASSIGNEE) ---
class UserSelect(discord.ui.Select):
    def __init__(self, bot, users_dict: dict):
        self.bot = bot
        options = [
            discord.SelectOption(label=discord_name, value=github_name)
            for discord_name, github_name in users_dict.items()
        ]
        options.insert(0, discord.SelectOption(label="Nenhum (Criar sem responsável)", value="NENHUM"))
        
        super().__init__(placeholder="Quem será o responsible (Assignee)?...", options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        choice = self.values[0]
        assignee_defined = None if choice == "NENHUM" else choice
        
        next_view = discord.ui.View()
        next_view.add_item(RepoSelect(repos=self.bot.repositorios_disponiveis, assignee=assignee_defined))
        
        await interaction.response.edit_message(
            content="🔄 Responsável definido! Agora selecione o repositório destino:", 
            view=next_view
        )


# --- MODAL (FORMULÁRIO DE 5 CAMPOS) ---
class TaskModal(discord.ui.Modal):
    def __init__(self, repo_path: str, assignee: str | None):
        short_name = repo_path.split('/')[-1]
        super().__init__(title=f'Nova Task: {short_name[:20]}')
        self.repo_path = repo_path
        self.assignee = assignee

    task_title = discord.ui.TextInput(
        label='Título da Task', 
        placeholder='Ex: [BUG] Falha na autenticação', 
        required=True, 
        max_length=100
    )
    task_context = discord.ui.TextInput(
        label='Contexto / Descrição', 
        style=discord.TextStyle.paragraph, 
        placeholder='Explique o problema ou objetivo de negócio...',
        required=True
    )
    task_steps = discord.ui.TextInput(
        label='Critérios de Aceite (Opcional)', 
        style=discord.TextStyle.paragraph, 
        placeholder='- [ ] Fazer X;\n- [ ] Fazer Y.',
        required=False
    )
    task_notes = discord.ui.TextInput(
        label='Notas de Implementação (Opcional)', 
        style=discord.TextStyle.paragraph, 
        placeholder='Abordagem técnica, links de referência, decisões arquiteturais...',
        required=False
    )
    task_blockers = discord.ui.TextInput(
        label='Bloqueadores (Opcional)', 
        style=discord.TextStyle.paragraph, 
        placeholder='Liste PRs, issues ou fatores externos necessários...',
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            repo = gh.get_repo(self.repo_path)
            
            issue_body = build_standard_template(
                context=self.task_context.value,
                steps=self.task_steps.value,
                notes=self.task_notes.value,
                blockers=self.task_blockers.value,
                user_name=interaction.user.display_name
            )
            
            assignees_list = [self.assignee] if self.assignee else []
            
            # Cria a issue no repositório alvo
            issue = repo.create_issue(title=self.task_title.value, body=issue_body, assignees=assignees_list)
            
            # 🔥 CRUCIAL: Captura o ID global da issue e vincula ao quadro do projeto via GraphQL
            link_to_project_v2(issue.node_id)
            
            await interaction.followup.send(f"✅ Task criada com sucesso e adicionada ao Project Board!\n[Ver Issue]({issue.html_url})", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao criar task: {e}", ephemeral=True)


# --- COG PRINCIPAL DE TASKS ---
class TaskCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="criar_task", description="Abre o assistente sequencial para criar uma task")
    async def create_task(self, ctx: commands.Context) -> None:
        interaction: discord.Interaction = ctx.interaction
        
        if not self.bot.repositorios_disponiveis:
            await interaction.response.send_message("❌ Nenhum repositório disponível.", ephemeral=True)
            return

        users = get_users()
        
        # 🚀 SE NÃO HOUVER USUÁRIOS: Pula direto para a seleção de repositório (Sem Assignee)
        if not users:
            view = discord.ui.View()
            view.add_item(RepoSelect(repos=self.bot.repositorios_disponiveis, assignee=None))
            await interaction.response.send_message(
                "ℹ️ Nenhum desenvolvedor cadastrado no banco do bot.\n**Selecione o repositório destino para a task (será criada sem responsável):**", 
                view=view, 
                ephemeral=True
            )
            return

        # 👥 SE HOUVER USUÁRIOS: Segue o fluxo normal com o Dropdown de escolha
        view = discord.ui.View()
        view.add_item(UserSelect(bot=self.bot, users_dict=users))
        await interaction.response.send_message("Passo 1: Quem será o responsável por essa task?", view=view, ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TaskCog(bot))