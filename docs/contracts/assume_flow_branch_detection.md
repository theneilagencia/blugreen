# Análise Técnica: Detecção Automática de Branch Padrão no Fluxo Assume

## 📋 Contexto

O fluxo **Assume** é responsável por analisar repositórios Git existentes. Atualmente, ele assume que a branch padrão é sempre `main`, o que causa falhas em repositórios que usam `master`, `develop`, `trunk` ou outras convenções.

Este documento detalha a solução técnica para detectar a branch padrão automaticamente, garantindo que o fluxo funcione com qualquer repositório Git.

## 🔍 Problema e Impacto

### Localização do Problema

**Arquivo:** `backend/app/services/project_assumption.py`

**Método:** `assume_project()`
```python
async def assume_project(
    self,
    project: Project,
    repository_url: str,
    branch: str = "main",  # <-- Problema aqui
) -> dict[str, Any]:
```

**Método:** `_step_fetch_repository()`
```python
result = subprocess.run(
    ["git", "clone", "--branch", branch, repository_url, str(repo_path)],
    # ...
)
```

### Impacto

- **Falha no Clone:** O `git clone` falha se a branch `main` não existir.
- **Experiência do Usuário:** O usuário recebe um erro genérico, sem saber o motivo.
- **Limitação do Produto:** Blugreen não consegue analisar repositórios que não usam `main`.

---

## 🎯 Solução Técnica: Detecção Automática

A solução consiste em implementar um algoritmo de detecção de branch padrão que é executado antes do `git clone`.

### Algoritmo de Detecção

O algoritmo deve seguir esta ordem de prioridade:

#### 1. `git ls-remote --symref <url> HEAD`

Este é o método mais confiável. Ele consulta o servidor Git e retorna a referência simbólica de `HEAD`, que aponta para a branch padrão.

**Comando:**
```bash
git ls-remote --symref https://github.com/tiangolo/fastapi.git HEAD
```

**Saída Esperada:**
```
ref: refs/heads/master    HEAD
<hash>                    HEAD
```

**Lógica de Extração:**
- Procurar pela linha que começa com `ref:`
- Extrair o nome da branch de `refs/heads/<branch_name>`
- Neste caso, `master`

---

#### 2. Tentativa de Branches Comuns

Se o primeiro método falhar (ex: servidor Git antigo), tentar clonar as branches mais comuns em ordem de prioridade.

**Ordem de Tentativa:**
1. `main`
2. `master`
3. `develop`
4. `trunk`

**Lógica:**
- Tentar `git clone --branch <branch_name>` para cada uma.
- A primeira que funcionar é a branch padrão.

---

#### 3. Listar Branches Remotas

Se as tentativas falharem, listar todas as branches remotas e usar a primeira como fallback.

**Comando:**
```bash
git ls-remote --heads https://github.com/tiangolo/fastapi.git
```

**Saída Esperada:**
```
<hash>    refs/heads/master
<hash>    refs/heads/dependabot/pip/uv-0.1.13
...
```

**Lógica:**
- Usar a primeira branch da lista como fallback.
- Registrar um aviso de que a branch foi inferida.

---

#### 4. Falha Total

Se todos os métodos falharem, retornar um erro descritivo para o usuário.

**Erro Esperado:**
```json
{
    "error": "Could not determine default branch",
    "available_branches": ["main", "master", ...],
    "attempted_branches": ["main", "master", "develop", "trunk"]
}
```

---

## 📝 Contrato de Implementação

### Função de Detecção

**Nome:** `detect_default_branch(repository_url: str) -> str`

**Entrada:**
- `repository_url` (str): URL do repositório Git.

**Saída (Sucesso):**
- `str`: Nome da branch padrão detectada.

**Saída (Erro):**
- `Exception`: `CouldNotDetectBranchError`

### Modificação no Fluxo Assume

**Arquivo:** `backend/app/services/project_assumption.py`

**Método:** `assume_project()`

```python
async def assume_project(
    self,
    project: Project,
    repository_url: str,
    branch: Optional[str] = None,  # Branch agora é opcional
) -> dict[str, Any]:
    
    # ...
    
    try:
        if not branch:
            # 1. Detectar branch padrão
            detected_branch = await self._detect_default_branch(repository_url)
        else:
            detected_branch = branch
            
    except CouldNotDetectBranchError as e:
        # Retornar erro para o usuário
        return {"error": str(e)}

    # 2. Usar a branch detectada no git clone
    step_result = await self._step_fetch_repository(
        workflow, project, repository_url, detected_branch
    )
    
    # ...
```

### Contrato de Saída (API)

**Endpoint:** `POST /assume/project`

**Saída (Erro de Detecção):**
```json
{
    "status": "error",
    "message": "Could not determine default branch for repository",
    "details": {
        "repository_url": "https://github.com/user/repo",
        "error_details": "Failed to connect to git server",
        "available_branches": ["feat/new-feature", "fix/bug"],
        "attempted_branches": ["main", "master", "develop", "trunk"]
    }
}
```

---

## 🛡️ Regras de Implementação

1. **Timeout:** Todas as chamadas `git` devem ter um timeout de **30 segundos**.
2. **Validação de URL:** Validar a URL do repositório antes de usar.
3. **Segurança:**
   - **NÃO** interpolar a URL diretamente em comandos shell.
   - Usar `subprocess.run` com lista de argumentos.
   - **NÃO** logar credenciais ou tokens.
4. **Logging:** Logar cada etapa do algoritmo de detecção.

---

## 🧪 Casos de Teste Esperados

| Cenário | Repositório de Exemplo | Branch Esperada | Método de Detecção |
|---|---|---|---|
| Branch `main` | `https://github.com/pallets/flask` | `main` | `ls-remote --symref` |
| Branch `master` | `https://github.com/tiangolo/fastapi` | `master` | `ls-remote --symref` |
| Branch custom | (Criar repo de teste) | `production` | Tentativa de branches |
| Repo inacessível | `https://github.com/invalid/repo` | Erro | Falha total |
| URL inválida | `not-a-url` | Erro | Validação de URL |
| Sem `HEAD` symref | (Servidor Git antigo) | `main` ou `master` | Tentativa de branches |

---

## 📊 Métricas de Sucesso

- **Taxa de Sucesso:** > 95% dos repositórios públicos devem ser analisados com sucesso.
- **Performance:** Detecção deve levar < 5 segundos em média.
- **Cobertura:** Algoritmo deve cobrir os casos mais comuns (GitHub, GitLab, Bitbucket).

---

## 🚀 Próximos Passos (para Devin)

1. **Implementar `_detect_default_branch()`:**
   - Implementar os 4 passos do algoritmo.
   - Adicionar tratamento de erros e logging.

2. **Integrar no `assume_project()`:**
   - Chamar a nova função quando `branch` não for fornecida.
   - Passar a branch detectada para `_step_fetch_repository()`.

3. **Adicionar Testes Unitários:**
   - Criar testes para cada um dos cenários definidos.
   - Mockar `subprocess.run` para simular saídas do `git`.

4. **Testar Manualmente:**
   - Testar com repositórios reais para validar a solução.

---

**Status:** 📋 Análise Completa - Pronto para Implementação  
**Responsável pela Implementação:** Devin  
**Data:** 03/01/2026
