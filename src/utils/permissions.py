from discord.ext import commands

PERMITTED_ROLES = ["Moderador", "bot-manager"]

def is_staff():
    """Permite a execução se o usuário for Administrador OU tiver o cargo 'Moderador'."""
    def predicate(ctx: commands.Context) -> bool:
        has_permission = (
            ctx.author.guild_permissions.administrator or
            any(role.name == role_name for role in ctx.author.roles for role_name in PERMITTED_ROLES)
        )
        
        if has_permission:
            return True
            
        raise commands.MissingPermissions(["Administrador ou Cargo Moderador"])

    return commands.check(predicate)