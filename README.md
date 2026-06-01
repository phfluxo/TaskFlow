# 🤖 GitHub Task Bot para Discord

Este bot do Discord foi desenvolvido para automatizar e centralizar a gestão de tarefas do seu time. Ele permite criar **GitHub Issues (Tasks)** diretamente do chat do Discord através de formulários dinâmicos (Modals) e garante que essas tarefas sejam inseridas de forma automatizada no seu **GitHub Project Board v2**.

---

## 🚀 Funcionalidades Principais

* **Fluxo Sequencial de Criação (`/criar_task`):**
  1. **Passo 1:** Seleção do responsável (Assignee) puxando a lista de desenvolvedores vinculados.
  2. **Passo 2:** Escolha do repositório de destino da tarefa.
  3. **Passo 3:** Formulário estruturado de 5 campos (Título, Contexto/Descrição, Critérios de Aceite, Notas de Implementação e Bloqueadores) com geração automática de layout padronizado.
* **Ponte de Identidades (`users.json`):** Mapeamento persistente que vincula o usuário do Discord à sua respectiva conta do GitHub para atribuição automática de tarefas (`/register`).
* **Sincronização com Project Board v2:** Injeção direta da Issue dentro do quadro Kanban utilizando a API GraphQL do GitHub.
* **Gestão Administrativa Completa:** Comandos para administradores cadastrarem usuários manualmente, em massa via texto, por importação de JSON bruto ou gerenciamento via menus visuais.

---

## 🛠️ Passo a Passo para Configuração e Instalação

### 1. Pré-requisitos
* Python 3.11 ou superior instalado.
* Uma conta de Bot criada no [Discord Developer Portal](https://discord.com/developers/applications) com os escopos de **Slash Commands (Applications.commands)** e as **Intents** básicas ativadas.
* Um Token de Acesso Pessoal (PAT) do GitHub.

### 2. Configurando as Permissões Críticas do Token do GitHub
Para que o bot consiga injetar as tarefas no seu Project Board, o token do GitHub precisa de permissões especiais de nível de conta.

* **Se estiver usando Fine-grained Personal Access Token (Recomendado):**
  1. No topo das configurações do token, em **Repository Access**, selecione **All repositories** (Todos os repositórios). *Nota: Se restringir a apenas alguns repositórios, o GitHub ocultará as opções de quadro de projeto.*
  2. Vá na aba **Account** (ao lado de *Repositories*).
  3. Clique em **Add permissions**, selecione **Projects** e mude o nível de acesso para **Read and Write** (Ler e Escrever).
  4. Salve clicando em **Update token**.

* **Se estiver usando Personal Access Token Classic (Antigo):**
  1. Marque o escopo completo **`repo`**.
  2. Marque o escopo completo **`project`**.
  3. Salve clicando em **Update token**.

### 3. Instalação e Estrutura do Projeto

Organize os arquivos na seguinte estrutura de diretórios:

```text
📂 seu-projeto
├── 📂 src
│   ├── 📂 cogs
│   │   ├── task_commands.py
│   │   └── user_commands.py
│   └── 📂 templates
│       └── task_layouts.py
├── 📂 core
│   └── bot.py
├── .env
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── users.json
└── main.py

```

Instale as dependências necessárias utilizando o gerenciador de sua preferência:

```bash
# Utilizando o Poetry (Recomendado)
poetry install

# Ou utilizando o pip tradicional
pip install discord.py PyGithub requests python-dotenv watchdog

```

---

## ⚙️ Explicação Detalhada das Variáveis de Ambiente (`.env`)

Crie um arquivo chamado `.env` na raiz do seu projeto. Ele deve conter a estrutura abaixo:

```env
# Token secreto de autenticação do seu bot do Discord.
# Obtido no Discord Developer Portal (Bot -> Reset Token).
DISCORD_TOKEN=seu_discord_token_aqui

# Token de Acesso Pessoal (PAT) do GitHub configurado com permissão de escrita em Repositórios e Projetos.
GITHUB_TOKEN=seu_github_token_aqui

# O número de identificação do seu Project Board v2.
# Pode ser localizado diretamente no final da URL do seu projeto no navegador.
# Exemplo: se a URL for [github.com/orgs/SuaOrg/projects/3](https://github.com/orgs/SuaOrg/projects/3), o número é 3.
GITHUB_PROJECT_NUMBER=3

# Nome/Slug da Organização no GitHub onde o projeto está hospedado.
# OBRIGATÓRIO se o seu projeto estiver dentro de uma Organização.
# DEIXE EM BRANCO ou remova a linha se o projeto pertencer ao seu perfil pessoal (User).
GITHUB_ORG=nome-da-sua-organizacao

# Define se o bot deve listar automaticamente todos os repositórios da conta ('true')
# ou se usará uma lista pré-definida manualmente ('false').
AUTO_DISCOVER_REPOS=true

# Lista manual de repositórios reserva (usada apenas se AUTO_DISCOVER_REPOS for false).
# Deve seguir estritamente o formato JSON de chave-valor: {"Nome Exibição": "dono/nome-repo"}.
GIT_REPOS='{"Backend API": "john/star-backend", "Frontend App": "john/web-app"}'

```

---

## ⌨️ Comandos Disponíveis no Bot

### 👥 Comandos de Usuários (`user_commands.py`)

* `/register`: Abre um modal individual para o membro do Discord vincular o seu próprio username do GitHub. Essencial para que o bot saiba quem marcar como responsável pelas tasks.
* `/unregister`: Remove o vínculo atual do usuário do banco de dados do bot.
* `/register_users` **[Admin]**: Abre um modal para cadastrar múltiplos usuários simultaneamente por meio de caixas de texto com nomes separados por vírgula.
* `/import_users_json` **[Admin]**: Abre um modal para importar um dicionário JSON bruto contendo os mapeamentos de usuários no formato `{"discord": "github"}`. Útil para migrações rápidas.
* `/print_users` **[Admin]**: Exibe o conteúdo atual do arquivo `users.json` formatado no chat em formato de bloco de código, ideal para a realização de backups.
* `/list_users` **[Admin]**: Exibe uma interface visual com menu de seleção (Dropdown) listando os membros mapeados, permitindo remover cadastros antigos instantaneamente.

### 📋 Comandos de Tasks (`task_commands.py`)

* `/criar_task`: Dispara o assistente interativo em etapas. O bot guiará o usuário na seleção do responsável, na escolha do repositório e abrirá o formulário modal de 5 campos. Ao enviar, a issue é criada no repositório escolhido e fixada de forma transparente no Kanban do projeto definido no `.env`.

---

## 🐳 Executando com Docker e Docker Compose (Desenvolvimento com Hot-Reload)

O projeto está totalmente containerizado e preparado para o desenvolvimento ágil. Para subir o bot com sincronização em tempo real do código fonte:

```bash
docker compose up -d --build

```

O contêiner utilizará o `watchdog` (`watchmedo`) internamente para monitorar alterações nos arquivos `.py`. Sempre que um arquivo for salvo na sua máquina, o processo do bot será reiniciado automaticamente dentro do contêiner em menos de 2 segundos.

---

## 🔄 Fluxo de Execução do Bot

1. Quando iniciado, o bot autentica-se no Discord e no GitHub.
2. Ele carrega a lista de repositórios disponíveis (via descoberta automática ou arquivo de configuração configurado no `.env`).
3. Ao rodar `/criar_task`, o bot faz a validação cruzada do responsável escolhido usando o arquivo `users.json`.
4. Após o preenchimento do formulário, o bot faz a requisição REST (via PyGithub) para abrir a Issue no repositório alvo.
5. De posse do ID Global (Node ID) da nova Issue, o bot faz uma chamada GraphQL para localizar o ID do Project Board v2 e executa a mutação `addProjectV2ItemById`, inserindo a tarefa de forma bem-sucedida dentro do quadro visual Kanban.

```

```