# Análise Técnica: Fluxo Assume - Detecção de Branch Padrão

## 📋 Contexto

O fluxo **Assume** é responsável por analisar repositórios Git existentes. Atualmente, o sistema assume que a branch padrão é sempre `main` (hardcoded na linha 49 do `project_assumption.py`).

## 🔍 Problema Identificado

### Localização do Problema
**Arquivo:** `backend/app/services/project_assumption.py`  
**Linha:** 49  
**Código Atual:**
```python
async def assume_project(
    self,
    project: Project,
    repository_url: str,
    branch: str = "main",  # ← HARDCODED
) -> dict[str, Any]:
```

### Impacto
- ❌ Falha ao clonar repositórios que usam `master` como branch padrão
- ❌ Falha ao clonar repositórios que usam outras branches padrão (ex: `develop`, `trunk`)
- ❌ Erro: `fatal: Remote branch main not found in upstream origin`

### Fluxo Atual
```
1. API recebe repository_url
2. assume_project() usa branch="main" (padrão)
3. git clone --branch main <url>
4. Se branch não existir → FALHA
```

---

## ✅ Solução Proposta

### Algoritmo de Detecção Automática

```
1. Tentar clonar sem especificar branch
   → git clone <url> (usa branch padrão do remoto)
   
2. Se falhar, tentar branches comuns em ordem:
   a) main
   b) master
   c) develop
   d) trunk
   
3. Se todas falharem:
   → Listar branches remotas: git ls-remote --heads <url>
   → Usar a primeira branch encontrada
   
4. Fallback final:
   → Retornar erro descritivo com branches disponíveis
```

### Fluxo Proposto

```
┌─────────────────────────────────────┐
│ 1. Receber repository_url          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 2. Detectar branch padrão remota    │
│    git ls-remote --symref <url> HEAD│
└──────────────┬──────────────────────┘
               │
               ├─── Sucesso ──────────┐
               │                      │
               ├─── Falha             │
               │                      │
               ▼                      ▼
┌──────────────────────┐   ┌──────────────────────┐
│ 3a. Usar branch      │   │ 3b. Tentar branches  │
│     detectada        │   │     comuns (main,    │
│                      │   │     master, etc)     │
└──────┬───────────────┘   └──────┬───────────────┘
       │                          │
       └──────────┬───────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ 4. git clone --branch <detected>    │
└──────────────┬──────────────────────┘
               │
               ├─── Sucesso ──────────┐
               │                      │
               ├─── Falha             │
               │                      │
               ▼                      ▼
┌──────────────────────┐   ┌──────────────────────┐
│ 5a. Continuar fluxo  │   │ 5b. Listar branches  │
│     Assume           │   │     disponíveis e    │
│                      │   │     retornar erro    │
└──────────────────────┘   └──────────────────────┘
```

---

## 📝 Contrato Técnico

### Entrada
```python
{
    "repository_url": str,  # URL do repositório Git
    "branch": Optional[str] = None  # Branch específica (opcional)
}
```

### Saída (Sucesso)
```python
{
    "detected_branch": str,  # Branch detectada/usada
    "repository_url": str,
    "local_path": str,
    "git_output": str
}
```

### Saída (Falha)
```python
{
    "error": str,
    "available_branches": List[str],  # Branches disponíveis no remoto
    "attempted_branches": List[str]   # Branches que foram tentadas
}
```

---

## 🔧 Implementação Sugerida

### Novo Método: `_detect_default_branch()`

```python
async def _detect_default_branch(self, repository_url: str) -> Optional[str]:
    """
    Detecta a branch padrão de um repositório Git remoto.
    
    Estratégias (em ordem):
    1. git ls-remote --symref <url> HEAD
    2. Tentar branches comuns: main, master, develop, trunk
    3. Listar todas as branches e usar a primeira
    
    Returns:
        str: Nome da branch padrão detectada
        None: Se não conseguir detectar
    """
    # Estratégia 1: Detectar via symref
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--symref", repository_url, "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            # Parse output: "ref: refs/heads/main\tHEAD"
            for line in result.stdout.split("\n"):
                if line.startswith("ref:"):
                    branch = line.split("/")[-1].split("\t")[0]
                    return branch
    except Exception as e:
        logger.warning(f"Failed to detect branch via symref: {e}")
    
    # Estratégia 2: Tentar branches comuns
    common_branches = ["main", "master", "develop", "trunk"]
    for branch in common_branches:
        try:
            result = subprocess.run(
                ["git", "ls-remote", "--heads", repository_url, f"refs/heads/{branch}"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                return branch
        except Exception:
            continue
    
    # Estratégia 3: Listar todas e usar a primeira
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--heads", repository_url],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            first_line = result.stdout.split("\n")[0]
            branch = first_line.split("refs/heads/")[-1]
            return branch
    except Exception as e:
        logger.error(f"Failed to list branches: {e}")
    
    return None
```

### Modificação em `assume_project()`

```python
async def assume_project(
    self,
    project: Project,
    repository_url: str,
    branch: Optional[str] = None,  # Agora opcional
) -> dict[str, Any]:
    """
    Assume an existing repository.
    
    If branch is not specified, automatically detects the default branch.
    """
    logger.info(f"Starting project assumption for: {repository_url}")
    
    # Detectar branch se não especificada
    if branch is None:
        branch = await self._detect_default_branch(repository_url)
        if branch is None:
            return {
                "status": "error",
                "error": "Could not detect default branch",
                "message": "Please specify a branch explicitly"
            }
        logger.info(f"Detected default branch: {branch}")
    
    # Continuar com o fluxo normal...
```

---

## ⚠️ Considerações de Segurança

1. **Timeout:** Todas as operações Git devem ter timeout (30s recomendado)
2. **Validação de URL:** Validar formato da URL antes de executar comandos Git
3. **Sanitização:** Não interpolar URLs diretamente em comandos shell
4. **Rate Limiting:** Considerar rate limiting para evitar abuso
5. **Logs:** Não logar URLs com credenciais (se houver)

---

## 🧪 Casos de Teste

### Teste 1: Repositório com branch `main`
```python
repository_url = "https://github.com/user/repo-with-main"
# Esperado: detectar "main"
```

### Teste 2: Repositório com branch `master`
```python
repository_url = "https://github.com/user/repo-with-master"
# Esperado: detectar "master"
```

### Teste 3: Repositório com branch customizada
```python
repository_url = "https://github.com/user/repo-with-develop"
# Esperado: detectar "develop" ou primeira branch disponível
```

### Teste 4: Repositório privado sem acesso
```python
repository_url = "https://github.com/private/repo"
# Esperado: erro descritivo
```

### Teste 5: URL inválida
```python
repository_url = "not-a-valid-url"
# Esperado: erro de validação
```

---

## 📊 Métricas de Sucesso

- ✅ Taxa de sucesso na detecção de branch: > 95%
- ✅ Tempo médio de detecção: < 5 segundos
- ✅ Zero falsos positivos (branch incorreta)
- ✅ Mensagens de erro descritivas em 100% dos casos

---

## 🚀 Próximos Passos (para Devin)

1. Implementar método `_detect_default_branch()`
2. Modificar `assume_project()` para usar detecção automática
3. Adicionar testes unitários para cada estratégia
4. Adicionar testes de integração com repositórios reais
5. Atualizar documentação da API
6. Adicionar logs detalhados para debugging

---

## 📌 Decisões Técnicas

| Decisão | Justificativa |
|---------|---------------|
| Usar `git ls-remote` | Não requer clone completo, mais rápido |
| Fallback para branches comuns | Compatibilidade com 99% dos repositórios |
| Timeout de 30s | Balance entre confiabilidade e UX |
| Branch opcional na API | Permite override manual quando necessário |
| Retornar branches disponíveis em erro | Facilita debugging e correção manual |

---

**Status:** 📋 Análise Completa - Pronto para Implementação  
**Responsável pela Implementação:** Devin  
**Data:** 03/01/2026
