DEFAULT_VALUE = "_No response_"

def build_standard_template(context: str, steps: str, notes: str, blockers: str, user_name: str) -> str:
    """Gera o corpo da issue no formato Padrão - Fluxo"""
    steps_content = steps if steps.strip() else DEFAULT_VALUE
    notes_content = notes if notes.strip() else DEFAULT_VALUE
    blockers_content = blockers if blockers.strip() else DEFAULT_VALUE
    
    return f"""
### Código do Requisito Funcional (se existir)

{DEFAULT_VALUE}

### Contexto e Proposta de Solução

{context}

### Critérios de Aceite (Given / When / Then)

{steps_content}

### Notas de Implementação (opcional)

{notes_content}

### Dependências / Bloqueadores (opcional)

{blockers_content}

---
*Task gerada via Discord por **{user_name}***
"""
