# Create Flow com Agentes (LLM + MCP)

Este documento descreve a implementação REAL do Create Flow usando agentes autônomos (LLM + MCP tools).

## Visão Geral

O Create Flow agora executa **código real** usando:
- **LLMProvider**: Ollama (primário) + fallback no-LLM
- **MCP Tools**: repo_read, repo_write, shell_run (com allowlist)
- **AgentRunner**: Orquestra execução de steps com auditabilidade
- **Persistência**: Todos os inputs/outputs salvos em `ProductStep`

## Variáveis de Ambiente

### Obrigatórias

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/blugreen

# Workspace (onde produtos são criados)
WORKSPACE_ROOT=/tmp/blugreen_workspaces
```

### Opcionais (com fallback)

```bash
# Ollama (LLM primário)
OLLAMA_URL=http://localhost:11434  # default
OLLAMA_MODEL=llama2                # default
OLLAMA_TIMEOUT=30                  # segundos, default

# CORS
CORS_ORIGINS_RAW=https://app.blugreen.com.br,https://blugreen.com.br
```

## Funcionamento dos Agentes

### 1. LLMProvider

**Ollama (Primário):**
- Tenta conectar em `OLLAMA_URL`
- Timeout de 30s por requisição
- Se falhar → fallback automático

**Fallback (No-LLM Mode):**
- Usa templates e heurísticas
- Gera código/testes/docs básicos
- **Sempre funciona**, mesmo sem LLM

**Exemplo de uso:**
```python
from app.services.llm_provider import LLMProvider

llm = LLMProvider()
response = await llm.generate(
    prompt="Generate a FastAPI endpoint",
    system_prompt="You are a Python expert"
)

print(response.llm_used)  # "ollama" ou "no-llm-fallback"
print(response.content)   # código gerado
```

### 2. MCP Tools (Auditáveis)

**repo_read(file_path: str) -> str**
- Lê arquivo do workspace
- Retorna conteúdo como string
- Auditado em `ProductStep.output_data.tool_calls`

**repo_write(file_path: str, content: str) -> None**
- Escreve arquivo no workspace
- Cria diretórios automaticamente
- Auditado em `ProductStep.output_data.tool_calls`

**shell_run(command: str, timeout: int = 30) -> Dict**
- Executa comando **APENAS** se estiver na allowlist
- Allowlist: `pytest`, `ruff`, `mypy`, `npm test`, `npm run build`
- Timeout padrão: 30s
- Retorna: `{stdout, stderr, returncode}`
- Auditado em `ProductStep.output_data.tool_calls`

**Segurança:**
```python
# ✅ Permitido
shell_run("pytest tests/")
shell_run("ruff check .")
shell_run("npm test")

# ❌ Bloqueado (não está na allowlist)
shell_run("rm -rf /")
shell_run("curl http://evil.com")
```

### 3. AgentRunner

Orquestra execução de cada step:

```python
from app.services.agent_runner import AgentRunner

runner = AgentRunner(workspace_root="/tmp/product_1")
output = await runner.run("generate_code", {
    "product_name": "MyApp",
    "stack": "FastAPI, React",
    "objective": "Create a todo app"
})

# Output inclui:
# - llm_used: "ollama" ou "no-llm-fallback"
# - tool_calls: [{"tool": "repo_write", "args": {...}}]
# - files_changed: ["backend/main.py", "frontend/App.tsx"]
# - output: "Generated 2 files"
```

## Steps Implementados

### 1. generate_code
- **Agente:** Codegen
- **LLM:** Sim (com fallback)
- **Tools:** repo_write
- **Output:** `{llm_used, tool_calls, files_changed, output}`
- **Idempotente:** ✅ Sim

### 2. create_tests
- **Agente:** QA
- **LLM:** Sim (com fallback)
- **Tools:** repo_write, shell_run (pytest)
- **Output:** `{llm_used, tool_calls, files_changed, test_results, output}`
- **Idempotente:** ✅ Sim

### 3. generate_docs
- **Agente:** Docs
- **LLM:** Sim (com fallback)
- **Tools:** repo_write
- **Output:** `{llm_used, tool_calls, files_changed, output}`
- **Idempotente:** ✅ Sim

### 4. validate_structure
- **Agente:** Validator
- **LLM:** Não (usa linters)
- **Tools:** shell_run (ruff, mypy, pytest)
- **Output:** `{llm_used: "none", tool_calls, findings, score, output}`
- **Idempotente:** ✅ Sim

### 5. finalize_product
- **Agente:** Nenhum (consolidação)
- **LLM:** Não
- **Tools:** Nenhum
- **Output:** `{llm_used: "none", summary, version_tag, output}`
- **Idempotente:** ❌ Não (gera version_tag único)

## Auditabilidade

Todos os steps salvam em `ProductStep`:

```python
{
  "step_name": "generate_code",
  "status": "done",
  "input_data": {
    "product_name": "MyApp",
    "stack": "FastAPI, React"
  },
  "output_data": {
    "llm_used": "ollama",
    "tool_calls": [
      {
        "tool": "repo_write",
        "args": {"file_path": "backend/main.py", "content": "..."}
      }
    ],
    "files_changed": ["backend/main.py", "frontend/App.tsx"],
    "output": "Generated 2 files"
  },
  "started_at": "2026-01-04T01:46:33Z",
  "completed_at": "2026-01-04T01:46:34Z",
  "error_message": null
}
```

## Testes

### Unitários (16 testes)
```bash
pytest tests/test_agent_runner.py -v
```

Cobrem:
- LLMProvider (Ollama + fallback)
- MCP Tools (repo_read, repo_write, shell_run)
- AgentRunner (todos os 5 steps)

### E2E (5 testes)
```bash
pytest tests/test_create_flow_e2e.py -v
```

Cobrem:
- Fluxo completo end-to-end
- Idempotência de steps 1-4
- Falha não corrompe steps anteriores
- Persistência de outputs
- Funciona com Ollama indisponível (fallback)

### Todos os testes
```bash
pytest -v  # 94 testes passando
```

## Exemplo de Uso

### Via API

```bash
# Criar produto
curl -X POST "https://api.blugreen.com.br/projects/1/products" \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "Todo App",
    "stack": "FastAPI, React, PostgreSQL",
    "objective": "Create a simple todo application with user authentication"
  }'

# Response
{
  "product_id": 1,
  "status": "draft",
  "monitor_url": "/products/1/status"
}

# Monitorar status
curl "https://api.blugreen.com.br/products/1/status"

# Response
{
  "product_id": 1,
  "product_name": "Todo App",
  "status": "completed",
  "version_tag": "v0.1.0",
  "summary": "Product: Todo App\nStatus: Completed\nGenerated 2 code files\nAll tests passed\nValidation score: 85/100",
  "steps": [
    {
      "step_name": "generate_code",
      "status": "done",
      "started_at": "2026-01-04T01:46:33Z",
      "completed_at": "2026-01-04T01:46:34Z",
      "error": null
    },
    ...
  ]
}
```

### Via Código

```python
from app.services.create_flow import CreateFlowExecutor
from app.database import get_session

with get_session() as session:
    executor = CreateFlowExecutor(session)
    
    # Inicializar produto
    product = executor.initialize_product(
        project_id=1,
        product_name="Todo App",
        stack="FastAPI, React",
        objective="Create a todo app"
    )
    
    # Executar flow
    executor.execute_flow(product.id)
    
    # Verificar status
    status = executor.get_product_status(product.id)
    print(status)
```

## Segurança

### Shell Allowlist
Apenas comandos seguros são permitidos:
- `pytest` (testes)
- `ruff` (linter Python)
- `mypy` (type checker Python)
- `npm test` (testes Node.js)
- `npm run build` (build Node.js)

Qualquer outro comando é **bloqueado**.

### Rate Limiting
Simples proteção por produto:
- Máximo 1 execução simultânea por produto
- Steps em `running` bloqueiam nova execução

### Logs
- Não loga variáveis de ambiente
- Não loga credenciais
- Loga apenas inputs/outputs de tools

## Troubleshooting

### Ollama não conecta
**Sintoma:** Logs mostram "Ollama generation failed"

**Solução:**
1. Verificar se Ollama está rodando: `curl http://localhost:11434/api/tags`
2. Verificar `OLLAMA_URL` no `.env`
3. **Fallback automático:** Sistema continua funcionando sem LLM

### Workspace permission denied
**Sintoma:** Erro "Permission denied" ao criar arquivos

**Solução:**
1. Verificar `WORKSPACE_ROOT` no `.env`
2. Garantir que diretório existe e tem permissão de escrita
3. Padrão: `/tmp/blugreen_workspaces` (sempre tem permissão)

### Tests não executam
**Sintoma:** `shell_run("pytest")` retorna erro

**Solução:**
1. Verificar se `pytest` está instalado no ambiente
2. Verificar se comando está na allowlist
3. Aumentar timeout se necessário

## Próximos Passos

### Melhorias Futuras
1. **Agentes mais sofisticados:** Usar LLMs maiores (GPT-4, Claude)
2. **Tools adicionais:** git, docker, deploy
3. **Feedback loop:** Agente valida e corrige próprio código
4. **Paralelização:** Steps independentes em paralelo
5. **Rollback:** Desfazer steps em caso de falha

### Integração com Devin
O sistema está pronto para ser usado por Devin ou outros agentes:
- Contrato bem definido em `docs/contracts/create_flow_step_based.md`
- APIs REST para controle externo
- Auditabilidade completa via banco de dados
- Fallback garante funcionamento sem LLM

---

**Documentação atualizada em:** 2026-01-04  
**Versão:** 1.0.0
