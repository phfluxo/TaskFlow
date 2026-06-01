import os
from dotenv import load_dotenv
from src.core.bot import GitHubTaskBot

load_dotenv(override=True)

def main() -> None:
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        raise ValueError("ERRO: DISCORD_TOKEN não encontrado no arquivo .env")
        
    bot = GitHubTaskBot()
    bot.run(token)

if __name__ == '__main__':
    main()