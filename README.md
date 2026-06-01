# 🤖 GitHub Task Bot para Discord

Este bot do Discord foi desenvolvido para automatizar e centralizar a gestão de tarefas do seu time. Ele permite criar **GitHub Issues (Tasks)** diretamente do chat do Discord através de formulários dinâmicos (Modals) e garante que essas tarefas sejam inseridas de forma automatizada no seu **GitHub Project Board v2**.

---

## 🚀 Funcionalidades Principais

* **Fluxo Sequencial de Criação (`/criar_task`):**
  1. **Passo 1:** Seleção do responsável (Assignee) puxando a lista de desenvolvedores vinculados.
  2. **Passo 2:** Escolha do repositório de destino da tarefa.
  3. **Passo 3:** Formulário estruturado de 5 campos (Título, Contexto/Descrição, Critérios de Aceite, Notas de Implementação e Bloqueadores) com geração automática de layout padronizado.
* **Ponte de Identidades (`users.db` via SQLite):** Mapeamento persistente que vincula o usuário do Discord à sua respectiva conta do GitHub para atribuição automática de tarefas (`/register`).
* **Sincronização com Project Board v2:** Injeção direta da Issue dentro do quadro Kanban utilizando a API GraphQL do GitHub.
* **Gestão Administrativa Completa:** Comandos para administradores cadastrarem usuários manualmente, em massa via texto, por importação de JSON bruto ou gerenciamento via menus visuais.
* **Tratamento de Erros Resiliente (Global Error Handler):** Captura centralizada de exceções no núcleo do bot, oferecendo feedback instantâneo e amigável para falhas de permissão, comandos em cooldown ou não encontrados, mantendo os logs do terminal limpos.

---

## 🛠️ Passo a Passo para Configuração e Instalação

### 1. Pré-requisitos
* Python 3.11 ou superior instalado.
* Uma conta de Bot criada no [Discord Developer Portal](https://discord.com/developers/applications).

### 2. Variáveis de Ambiente (`.env`)
Configure um arquivo `.env` na raiz do projeto com as seguintes chaves:

```env
DISCORD_TOKEN=seu_token_do_discord_aqui
GITHUB_TOKEN=seu_token_pessoal_do_github_ghp_...
GITHUB_PROJECT_NUMBER=numero_do_seu_projeto_v2
GITHUB_ORG=nome_da_organizacao_se_aplicavel
AUTO_DISCOVER_REPOS=true_ou_false
GIT_REPOS={"NomeExibicao": "usuario/repositorio"}
```

#### ⚙️ Explicação Detalhada das Variáveis de Ambiente (`.env`)

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

## ⌨️ Comandos Disponíveis

### 📋 Comandos de Tasks (`task_commands.py`)

* `/criar_task`: Dispara o assistente interativo em etapas. O bot guiará o usuário na seleção do responsável, na escolha do repositório e abrirá o formulário modal de 5 campos. Ao enviar, a issue é criada no repositório escolhido e fixada de forma transparente no Kanban do projeto definido no `.env`.

### 👥 Comandos de Usuários (`user_commands.py`)

* `/registrar-se`: Abre um modal individual para o membro do Discord vincular o seu próprio username do GitHub. Essencial para que o bot saiba quem marcar como responsável pelas tasks.
* `/desregistrar-se`: Remove o vínculo atual do usuário do banco de dados do bot.
* `/cadastrar_usuarios_formulario ` **[Admin]**: Abre um modal para cadastrar múltiplos usuários simultaneamente por meio de caixas de texto com nomes separados por vírgula.
* `/importar_usuarios_json ` **[Admin]**: Abre um modal para importar um dicionário JSON bruto contendo os mapeamentos de usuários no formato `{"discord": "github"}`. Útil para migrações rápidas.
* `/listar_usuarios` **[Admin]**: Exibe uma interface visual com menu de seleção (Dropdown) listando os membros mapeados, permitindo remover cadastros antigos instantaneamente.
* `/print_users` **[Admin]**: Exibe o conteúdo atual do arquivo `users.db` formatado no chat em formato de bloco de código, ideal para a realização de backups.

---

## 🐳 Executando com Docker e Docker Compose (Desenvolvimento com Hot-Reload)

O projeto está totalmente containerizado e preparado para o desenvolvimento ágil. Para subir o bot com sincronização em tempo real do código fonte:

```bash
docker compose up -d --build

```

O contêiner utilizará o `watchdog` (`watchmedo`) internamente para monitorar alterações nos arquivos `.py`. Sempre que um arquivo for salvo na sua máquina, o processo do bot será reiniciado automaticamente dentro do contêiner.

---

## 🔄 Arquitetura e Fluxo de Execução

### ⚖️ Controle de Acesso e Segurança

O bot utiliza um sistema centralizado de controle de permissões decorado por `@is_staff()`. Comandos administrativos são restritos a:

* Usuários com permissão explícita de **Administrador** no servidor.
* Usuários que possuam os cargos específicos: `Moderador` ou `bot-manager`.

### 🚨 Gestão Centralizada de Erros

Para garantir uma experiência de usuário fluida e evitar o aviso genérico de *"O aplicativo não respondeu"* do Discord, o bot implementa um interceptador global de exceções (`on_command_error`) na classe base `GitHubTaskBot`:

* **Falta de Permissão:** Caso um usuário comum tente rodar um comando restrito, o bot captura o erro e responde de forma privada (**ephemeral**) explicando quais cargos são necessários.
* **Comandos Clássicos:** Se disparados via prefixo de texto (`!comando`), mensagens de erro de permissão ou cooldown expiram e são deletadas automaticamente após 15 segundos para manter o canal limpo.
* **Falhas Críticas:** Bugs internos e erros não mapeados geram logs limpos e rastreáveis (*Stack Traces*) diretamente no terminal do contêiner para fins de depuração.

### ⚙️ Ciclo de Criação de Tarefas

1. Quando iniciado, o bot autentica-se no Discord e mapeia a API do GitHub.
2. Ele carrega os repositórios disponíveis (via descoberta automática ou arquivo de configuração manual estruturado).
3. Ao rodar `/criar_task`, o bot faz a validação cruzada do responsável escolhido usando a tabela persistente do SQLite.
4. Após o preenchimento do formulário modal, o bot faz a requisição REST (via PyGithub) para abrir a Issue no repositório alvo.
5. De posse do ID Global (Node ID) da nova Issue, o bot executa uma chamada GraphQL para localizar o ID do Project Board v2 e executa a mutação `addProjectV2ItemById`, inserindo a tarefa de forma bem-sucedida dentro do quadro visual Kanban.
