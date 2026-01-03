# Análise Técnica: Fluxo Create - Criação de Produtos

## 📋 Contexto

O fluxo **Create** é responsável por criar produtos completos do zero, orquestrando um workflow de 10 etapas que vai desde a interpretação de requisitos até o deploy e monitoramento em produção.

## 🔍 Análise do Código Atual

### Localização
**Arquivo:** `backend/app/services/product_creation.py`  
**Classe:** `ProductCreationService`

### Workflow Atual (10 Steps)

```python
steps = [
    WorkflowStepType.INTERPRET_REQUIREMENT,  # 1
    WorkflowStepType.CREATE_PLAN,            # 2
    WorkflowStepType.VALIDATE_PLAN,          # 3
    WorkflowStepType.GENERATE_CODE,          # 4
    WorkflowStepType.CREATE_TESTS,           # 5
    WorkflowStepType.RUN_TESTS,              # 6
    WorkflowStepType.BUILD,                  # 7
    WorkflowStepType.DEPLOY,                 # 8
    WorkflowStepType.MONITOR,                # 9
    # WorkflowStepType.ROLLBACK (10 - condicional)
]
```

### Status da Implementação

| Step | Método | Status | Observação |
|------|--------|--------|------------|
| 1. Interpret Requirement | `_step_interpret_requirement()` | ✅ Implementado | Usa ArchitectAgent |
| 2. Create Plan | `_step_create_plan()` | ✅ Implementado | Usa ArchitectAgent |
| 3. Validate Plan | `_step_validate_plan()` | ✅ Implementado | Usa UXAgent + UIRefinementAgent |
| 4. Generate Code | `_step_generate_code()` | ⚠️ Parcial | Cria tasks mas não gera código real |
| 5. Create Tests | `_step_create_tests()` | ⚠️ Parcial | Cria tasks mas não gera testes reais |
| 6. Run Tests | `_step_run_tests()` | ⚠️ Parcial | Simula execução de testes |
| 7. Build | `_step_build()` | ⚠️ Parcial | Simula build |
| 8. Deploy | `_step_deploy()` | ⚠️ Parcial | Simula deploy |
| 9. Monitor | `_step_monitor()` | ⚠️ Parcial | Simula monitoramento |
| 10. Rollback | `rollback()` | ✅ Implementado | Rollback funcional |

---

## 📝 Contratos de Cada Step

### Step 1: Interpret Requirement

**Objetivo:** Analisar e interpretar os requisitos fornecidos pelo usuário.

**Entrada:**
```python
{
    "requirements": str,  # Requisitos em linguagem natural
    "project_id": int
}
```

**Processamento:**
- Usa **ArchitectAgent** para interpretar requisitos
- Cria **Task** do tipo `PLANNING`
- Analisa viabilidade, escopo e complexidade

**Saída (Sucesso):**
```python
{
    "step": "interpret_requirement",
    "success": True,
    "result": {
        "status": "success",
        "interpretation": {
            "summary": str,           # Resumo dos requisitos
            "features": List[str],    # Features identificadas
            "constraints": List[str], # Restrições técnicas
            "complexity": str,        # "low" | "medium" | "high"
            "estimated_effort": str   # Estimativa de esforço
        }
    }
}
```

**Saída (Falha):**
```python
{
    "step": "interpret_requirement",
    "success": False,
    "error": str
}
```

---

### Step 2: Create Plan

**Objetivo:** Criar plano técnico detalhado baseado nos requisitos interpretados.

**Entrada:**
```python
{
    "requirements": str,
    "interpretation": dict,  # Output do Step 1
    "project_id": int
}
```

**Processamento:**
- Usa **ArchitectAgent** para criar plano técnico
- Define arquitetura, stack tecnológica, estrutura de pastas
- Cria **Task** do tipo `PLANNING`

**Saída (Sucesso):**
```python
{
    "step": "create_plan",
    "success": True,
    "result": {
        "status": "success",
        "plan": {
            "architecture": {
                "type": str,              # "monolith" | "microservices" | "serverless"
                "components": List[dict]  # Componentes da arquitetura
            },
            "stack": {
                "backend": List[str],     # Tecnologias backend
                "frontend": List[str],    # Tecnologias frontend
                "database": List[str],    # Bancos de dados
                "infrastructure": List[str]
            },
            "structure": {
                "folders": List[str],     # Estrutura de pastas
                "key_files": List[str]    # Arquivos principais
            },
            "dependencies": List[str],    # Dependências externas
            "phases": List[dict]          # Fases de implementação
        }
    }
}
```

---

### Step 3: Validate Plan

**Objetivo:** Validar plano técnico contra regras de UX, UI e qualidade.

**Entrada:**
```python
{
    "plan": dict,  # Output do Step 2
    "project_id": int
}
```

**Processamento:**
- Usa **UXAgent** para validar regras de UX
- Usa **UIRefinementAgent** para validar critérios de UI
- Verifica conformidade com quality gates

**Saída (Sucesso):**
```python
{
    "step": "validate_plan",
    "success": True,
    "result": {
        "status": "success",
        "validation": {
            "ux_validation": {
                "passed": bool,
                "issues": List[dict],     # Issues encontrados
                "score": float            # 0.0 - 1.0
            },
            "ui_validation": {
                "passed": bool,
                "issues": List[dict],
                "score": float
            },
            "overall_score": float,
            "approved": bool
        }
    }
}
```

**Saída (Falha):**
```python
{
    "step": "validate_plan",
    "success": False,
    "error": str,
    "validation_errors": List[dict]
}
```

---

### Step 4: Generate Code

**Objetivo:** Gerar código backend e frontend baseado no plano validado.

**Entrada:**
```python
{
    "plan": dict,  # Output do Step 2 (validado)
    "project_id": int
}
```

**Processamento:**
- Usa **BackendAgent** para gerar código backend
- Usa **FrontendAgent** para gerar código frontend
- Cria estrutura de pastas e arquivos
- Gera código funcional e completo

**Saída (Sucesso):**
```python
{
    "step": "generate_code",
    "success": True,
    "result": {
        "backend": {
            "status": "success",
            "files_generated": List[str],  # Arquivos gerados
            "lines_of_code": int,
            "structure": dict                # Estrutura de pastas
        },
        "frontend": {
            "status": "success",
            "files_generated": List[str],
            "lines_of_code": int,
            "structure": dict
        }
    }
}
```

**⚠️ Estado Atual:** Implementação parcial
- ✅ Cria tasks para backend e frontend
- ❌ Não gera código real ainda
- ❌ Precisa integrar com sistema de arquivos
- ❌ Precisa usar LLM para geração de código

**🔧 Implementação Necessária:**
1. Integrar com workspace do projeto
2. Usar LLM (Ollama ou OpenAI) para gerar código
3. Criar arquivos no sistema de arquivos
4. Validar sintaxe do código gerado
5. Aplicar formatação e linting

---

### Step 5: Create Tests

**Objetivo:** Gerar testes automatizados para o código gerado.

**Entrada:**
```python
{
    "code": dict,  # Output do Step 4
    "plan": dict,  # Output do Step 2
    "project_id": int
}
```

**Processamento:**
- Usa **QAAgent** para gerar testes
- Cria testes unitários, integração e E2E
- Garante cobertura mínima de código

**Saída (Sucesso):**
```python
{
    "step": "create_tests",
    "success": True,
    "result": {
        "status": "success",
        "tests": {
            "unit_tests": {
                "files": List[str],
                "count": int
            },
            "integration_tests": {
                "files": List[str],
                "count": int
            },
            "e2e_tests": {
                "files": List[str],
                "count": int
            },
            "total_tests": int,
            "estimated_coverage": float  # 0.0 - 1.0
        }
    }
}
```

**⚠️ Estado Atual:** Implementação parcial
- ✅ Cria task para QA
- ❌ Não gera testes reais
- ❌ Precisa usar LLM para geração de testes

---

### Step 6: Run Tests

**Objetivo:** Executar testes automatizados e validar código.

**Entrada:**
```python
{
    "tests": dict,  # Output do Step 5
    "code": dict,   # Output do Step 4
    "project_id": int
}
```

**Processamento:**
- Executa testes unitários
- Executa testes de integração
- Executa testes E2E
- Coleta métricas de cobertura

**Saída (Sucesso):**
```python
{
    "step": "run_tests",
    "success": True,
    "result": {
        "status": "success",
        "test_results": {
            "total": int,
            "passed": int,
            "failed": int,
            "skipped": int,
            "duration": float,  # segundos
            "coverage": {
                "lines": float,      # 0.0 - 1.0
                "branches": float,
                "functions": float
            },
            "failures": List[dict]  # Detalhes dos testes falhados
        }
    }
}
```

**Saída (Falha):**
```python
{
    "step": "run_tests",
    "success": False,
    "error": str,
    "test_results": dict  # Resultados parciais
}
```

**⚠️ Estado Atual:** Implementação parcial
- ✅ Simula execução de testes
- ❌ Não executa testes reais
- ❌ Precisa integrar com test runners (pytest, jest, etc)

---

### Step 7: Build

**Objetivo:** Compilar/construir aplicação para produção.

**Entrada:**
```python
{
    "code": dict,        # Output do Step 4
    "tests": dict,       # Output do Step 6
    "project_id": int
}
```

**Processamento:**
- Usa **InfraAgent** para orquestrar build
- Executa build do backend
- Executa build do frontend
- Gera artefatos de produção

**Saída (Sucesso):**
```python
{
    "step": "build",
    "success": True,
    "result": {
        "status": "success",
        "build": {
            "backend": {
                "status": "success",
                "artifacts": List[str],  # Artefatos gerados
                "size": int,             # Tamanho em bytes
                "duration": float        # Tempo de build
            },
            "frontend": {
                "status": "success",
                "artifacts": List[str],
                "size": int,
                "duration": float
            },
            "docker_images": List[str]  # Imagens Docker geradas
        }
    }
}
```

**⚠️ Estado Atual:** Implementação parcial
- ✅ Cria task para infra
- ❌ Não executa build real
- ❌ Precisa integrar com Docker
- ❌ Precisa integrar com build tools (npm, poetry, etc)

---

### Step 8: Deploy

**Objetivo:** Fazer deploy da aplicação em produção.

**Entrada:**
```python
{
    "build": dict,       # Output do Step 7
    "project_id": int
}
```

**Processamento:**
- Usa **InfraAgent** para orquestrar deploy
- Faz deploy no Coolify
- Configura domínios e HTTPS
- Valida deploy com health checks

**Saída (Sucesso):**
```python
{
    "step": "deploy",
    "success": True,
    "result": {
        "status": "success",
        "deployment": {
            "environment": str,          # "production" | "staging"
            "urls": {
                "frontend": str,         # URL do frontend
                "backend": str           # URL do backend
            },
            "health_checks": {
                "frontend": bool,
                "backend": bool
            },
            "deployment_id": str,
            "deployed_at": str          # ISO timestamp
        }
    }
}
```

**⚠️ Estado Atual:** Implementação parcial
- ✅ Cria task para infra
- ❌ Não faz deploy real
- ❌ Precisa integrar com Coolify API
- ❌ Precisa configurar domínios automaticamente

---

### Step 9: Monitor

**Objetivo:** Monitorar aplicação em produção e validar funcionamento.

**Entrada:**
```python
{
    "deployment": dict,  # Output do Step 8
    "project_id": int
}
```

**Processamento:**
- Monitora health checks
- Coleta métricas de performance
- Detecta erros e anomalias
- Valida deploy gates

**Saída (Sucesso):**
```python
{
    "step": "monitor",
    "success": True,
    "result": {
        "status": "success",
        "monitoring": {
            "health": "healthy",         # "healthy" | "degraded" | "unhealthy"
            "uptime": float,             # Porcentagem
            "response_time_avg": float,  # ms
            "error_rate": float,         # Porcentagem
            "metrics": {
                "requests_total": int,
                "requests_success": int,
                "requests_error": int
            },
            "alerts": List[dict]         # Alertas ativos
        }
    }
}
```

**⚠️ Estado Atual:** Implementação parcial
- ✅ Simula monitoramento
- ❌ Não coleta métricas reais
- ❌ Precisa integrar com sistema de monitoramento

---

### Step 10: Rollback (Condicional)

**Objetivo:** Reverter deploy em caso de falha.

**Entrada:**
```python
{
    "deployment": dict,  # Deploy atual
    "reason": str,       # Motivo do rollback
    "project_id": int
}
```

**Processamento:**
- Reverte para versão anterior
- Restaura configurações
- Valida rollback

**Saída (Sucesso):**
```python
{
    "step": "rollback",
    "success": True,
    "result": {
        "status": "success",
        "rollback": {
            "previous_version": str,
            "rolled_back_at": str,
            "reason": str
        }
    }
}
```

**✅ Estado Atual:** Implementado e funcional

---

## 🔄 Fluxo de Estados

### Estados do Projeto Durante o Workflow

```
DRAFT
  ↓
PLANNING (Steps 1-3)
  ↓
IN_PROGRESS (Steps 4-5)
  ↓
TESTING (Step 6)
  ↓
DEPLOYING (Steps 7-8)
  ↓
DEPLOYED (Step 9)
  ↓
FAILED (se algum step falhar)
```

### Estados de Cada Step

```
PENDING → IN_PROGRESS → COMPLETED
                ↓
              FAILED
```

---

## 🚨 Tratamento de Erros

### Estratégia Atual

1. **Falha em qualquer step:**
   - Workflow muda para `FAILED`
   - Project muda para `FAILED`
   - Rollback automático é acionado

2. **Rollback:**
   - Reverte alterações do step atual
   - Mantém histórico de tentativas
   - Permite retry manual

### Melhorias Sugeridas

1. **Retry Automático:**
   - Tentar novamente steps que falharam (max 3x)
   - Exponential backoff entre tentativas

2. **Partial Rollback:**
   - Reverter apenas steps específicos
   - Manter progresso de steps bem-sucedidos

3. **Checkpoints:**
   - Salvar estado após cada step
   - Permitir retomar de qualquer ponto

---

## 🔧 Implementações Necessárias

### Prioridade Alta

1. **Step 4 - Generate Code:**
   - Integrar com LLM para geração de código
   - Criar arquivos no workspace
   - Validar sintaxe

2. **Step 5 - Create Tests:**
   - Integrar com LLM para geração de testes
   - Criar arquivos de teste
   - Validar estrutura

3. **Step 6 - Run Tests:**
   - Integrar com pytest (backend)
   - Integrar com jest (frontend)
   - Coletar métricas de cobertura

### Prioridade Média

4. **Step 7 - Build:**
   - Integrar com Docker
   - Executar build tools (npm, poetry)
   - Gerar imagens Docker

5. **Step 8 - Deploy:**
   - Integrar com Coolify API
   - Configurar domínios automaticamente
   - Validar health checks

### Prioridade Baixa

6. **Step 9 - Monitor:**
   - Integrar com sistema de monitoramento
   - Coletar métricas reais
   - Configurar alertas

---

## 📊 Métricas de Sucesso

| Métrica | Objetivo | Atual |
|---------|----------|-------|
| Taxa de sucesso do workflow | > 80% | N/A (não implementado) |
| Tempo médio de criação | < 30 min | N/A |
| Qualidade do código gerado | > 80/100 | N/A |
| Cobertura de testes | > 70% | N/A |
| Uptime pós-deploy | > 99% | N/A |

---

## 🚀 Próximos Passos (para Devin)

### Fase 1: Geração de Código (Steps 4-5)
1. Implementar integração com LLM (Ollama ou OpenAI)
2. Criar sistema de templates de código
3. Implementar validação de sintaxe
4. Criar testes unitários para geração

### Fase 2: Testes e Build (Steps 6-7)
1. Integrar com test runners
2. Implementar coleta de métricas
3. Integrar com Docker
4. Implementar build pipeline

### Fase 3: Deploy e Monitoramento (Steps 8-9)
1. Integrar com Coolify API
2. Implementar configuração automática de domínios
3. Integrar com sistema de monitoramento
4. Implementar alertas

---

## 📌 Decisões Técnicas

| Decisão | Justificativa |
|---------|---------------|
| Workflow sequencial | Simplicidade e rastreabilidade |
| Steps atômicos | Facilita rollback e retry |
| Estado persistente | Permite retomar workflow |
| Agentes especializados | Separação de responsabilidades |
| Validação em cada step | Fail fast, menos desperdício |

---

## ⚠️ Limitações Conhecidas

1. **Geração de Código:** Atualmente não gera código real
2. **Testes:** Não executa testes reais
3. **Build:** Não executa build real
4. **Deploy:** Não faz deploy real no Coolify
5. **Monitoramento:** Não coleta métricas reais

Todas essas limitações precisam ser resolvidas para o produto estar 100% funcional.

---

**Status:** 📋 Análise Completa - Pronto para Implementação  
**Responsável pela Implementação:** Devin  
**Data:** 03/01/2026
