FROM python:3.14-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Evita que o Python escreva os arquivos .pyc no disco e bufferize o stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala o Poetry no sistema do container
RUN pip install --no-cache-dir poetry

# Configura o Poetry para não criar um ambiente virtual separado dentro do container
# (Como o container já é isolado, instalar direto no escopo global dele é mais limpo)
RUN poetry config virtualenvs.create false

# Copia apenas os arquivos de configuração de dependências primeiro
# (Isso otimiza o cache do Docker se você mudar o código mas não mudar as libs)
COPY pyproject.toml poetry.lock* ./

# Instala todas as dependências (incluindo as de desenvolvimento para o hot-reload)
RUN poetry install --no-root --no-interaction --no-ansi

# Copia o restante dos arquivos do projeto
COPY . .

# Comando padrão caso o container rode em produção (sem hot-reload)
CMD ["python", "main.py"]