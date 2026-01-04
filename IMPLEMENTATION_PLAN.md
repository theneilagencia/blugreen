# Plano de Implementação - 12 Camadas do Blugreen

## Objetivo Global
Transformar o Blugreen em um **TIME SÊNIOR COMPLETO DE SOFTWARE** que opera de forma:
- Extremamente simples para LEIGOS
- Extremamente poderoso para produtos COMPLEXOS
- Totalmente autônomo, mas GOVERNADO
- Determinístico, auditável e confiável

---

## Análise da Arquitetura Atual

### ✅ O que já existe:
1. **Orquestrador Central** (`backend/app/orchestrator/`)
   - `central.py` - Orquestração básica
   - `planner.py` - Planejamento
   - `state_manager.py` - Gerenciamento de estado

2. **Agentes Especializados** (`backend/app/agents/`)
   - Arquiteto, Backend, Frontend, Infra, QA, UX, UI Refinement

3. **Workflows** (`backend/app/workflows/`)
   - `main_workflow.py`
   - `ux_ui_refinement.py`

4. **Quality Gates** (`backend/app/quality/`)
   - `deploy_gate.py`
   - `ui_quality.py`
   - `ux_quality.py`

5. **Services** (`backend/app/services/`)
   - `create_flow.py`
   - `project_assumption.py`
   - `safe_evolution.py`

### ❌ O que falta (conforme especificação):
1. **Modo Guiado para Leigos** - Interface simplificada
2. **Captura de Intenção Estruturada** - Contrato imutável
3. **Pré-visualização do Plano** - Confirmação explícita
4. **Loop Autônomo com Limites** - Devin-mode governado
5. **Avaliação Objetiva Anti-Alucinação** - Regras, não criatividade
6. **Visualização em Tempo Real** - Narrativa humana
7. **Modo Seguro** - "Não estrague nada"
8. **Enablement** - Ensinar o usuário
9. **QA Guiado** - Além de testes automatizados
10. **Observabilidade Completa** - Auditoria end-to-end

---

## Plano de Implementação por Fase

### FASE 1: CAMADA 1 - Modo Guiado para Leigos (CRÍTICO)

**Backend:**
- [ ] Criar endpoint `/api/guided/start` - Inicia modo guiado
- [ ] Criar modelo `GuidedSession` - Armazena sessão guiada
- [ ] Criar enum `GuidedIntent` - "criar", "melhorar", "entender"

**Frontend:**
- [ ] Criar página `/guided` - Interface simplificada
- [ ] Criar componente `GuidedWizard` - Wizard de 3 passos
- [ ] Criar componente `IntentSelector` - Seletor de intenção
- [ ] Esconder termos técnicos (stack, branch, pipeline)

**Regras:**
- Linguagem 100% humana
- Máximo 3 perguntas por etapa
- Sistema infere tudo internamente
- Usuário apenas confirma ou ajusta

---

### FASE 2: CAMADA 2 - Captura de Intenção (OBRIGATÓRIA)

**Backend:**
- [ ] Criar modelo `ProjectIntent` - Contrato imutável
- [ ] Criar serviço `IntentCapture` - Extrai e valida intenção
- [ ] Adicionar campos obrigatórios:
  - `product_name` - Qual é o produto?
  - `business_goal` - Qual o objetivo de negócio?
  - `target_audience` - Para quem é?
  - `success_criteria` - O que define sucesso?
  - `constraints` - O que NÃO pode ser alterado?
  - `risk_level` - Qual o nível de risco aceitável?

**Validação:**
- [ ] IA NÃO pode agir sem intenção validada
- [ ] Intenção vira contrato imutável durante execução
- [ ] Persistir intenção no banco de dados

---

### FASE 3: CAMADA 3 - Pré-visualização do Plano

**Backend:**
- [ ] Modificar `Planner` para gerar plano ANTES de executar
- [ ] Criar endpoint `/api/plan/preview` - Retorna plano
- [ ] Criar endpoint `/api/plan/confirm` - Confirma execução

**Frontend:**
- [ ] Criar componente `PlanPreview` - Mostra plano
- [ ] Criar modal de confirmação explícita
- [ ] Mostrar:
  - Etapas em linguagem humana
  - Tempo estimado
  - Riscos identificados
  - Botão "Deseja continuar?"

**Regra:**
- Sem confirmação explícita → NÃO EXECUTAR

---

### FASE 4: CAMADA 4 - Loop Autônomo Controlado (DEVIN-MODE)

**Backend:**
- [ ] Criar `AutonomousLoop` - Loop governado
- [ ] Implementar ciclo:
  1. Planejar
  2. Executar
  3. Avaliar
  4. Corrigir (com limite)
  5. Encerrar

**Limites:**
- [ ] `max_iterations` - Limite de iterações (padrão: 5)
- [ ] `max_time_seconds` - Limite de tempo (padrão: 300s)
- [ ] `max_impact_score` - Limite de impacto (padrão: 7/10)
- [ ] Estratégia de retry inteligente (não brute force)
- [ ] Cada ciclo justifica continuidade

---

### FASE 5: CAMADA 5 - Orquestração (O CÉREBRO)

**Backend:**
- [ ] Refatorar `CentralOrchestrator` para:
  - Manter visão global do produto
  - Definir contratos entre módulos
  - Validar coerência entre partes
  - Criar checkpoints de consistência

**Regra:**
- Ordem e dependências NÃO são decididas pela IA
- Sistema decide, IA executa

---

### FASE 6: CAMADA 6 - Avaliação Objetiva (ANTI-ALUCINAÇÃO)

**Backend:**
- [ ] Criar `ObjectiveEvaluator` - Avaliação por regras
- [ ] Implementar checks:
  - [ ] Testes passando?
  - [ ] Breaking changes?
  - [ ] Performance piorou?
  - [ ] Segurança violada?
  - [ ] Custo aumentou?

**Regra:**
- Sem passar na avaliação → não avança
- Avaliação por REGRAS, não criatividade

---

### FASE 7: CAMADA 7 - Governança de Agentes

**Backend:**
- [ ] Criar `AgentGovernor` - Governança de agentes
- [ ] Implementar:
  - [ ] Allowlist de ferramentas por agente
  - [ ] Timeout por operação
  - [ ] Blast radius limitado
  - [ ] Pausar/Suspender/Abortar

**Segurança:**
- Agentes só usam ferramentas permitidas
- Tudo com timeout
- Tudo auditável

---

### FASE 8: CAMADA 8 - Visualização em Tempo Real (UX CRÍTICO)

**Frontend:**
- [ ] Criar componente `RealTimeNarrative` - Narrativa humana
- [ ] Mostrar:
  - O que está sendo feito
  - Em que etapa está
  - Por que isso está acontecendo
  - Quanto falta

**Exemplos de narrativa:**
- "Estou criando a base do seu produto…"
- "Agora estou validando se tudo funciona…"
- "Encontrei um problema, vou corrigir…"

**Regra:**
- Mostrar NARRATIVA, não logs técnicos

---

### FASE 9: CAMADA 9 - Modo Seguro ("NÃO ESTRAGUE NADA")

**Backend:**
- [ ] Criar flag `safe_mode` em `Project`
- [ ] Implementar modo seguro:
  - Não sobrescreve código
  - Não faz deploy
  - Apenas sugere mudanças

**Frontend:**
- [ ] Criar toggle "✅ Modo Seguro Ativado"
- [ ] Mostrar claramente o que o modo seguro faz
- [ ] Linguagem emocionalmente clara para leigos

---

### FASE 10: CAMADA 10 - Enablement (ENSINAR O USUÁRIO)

**Backend:**
- [ ] Criar serviço `EnablementGenerator` - Gera guias
- [ ] Para cada produto criado, gerar:
  - Guia de uso em linguagem humana
  - Explicação dos fluxos
  - Exemplos práticos
  - Limitações
  - Boas práticas de operação

**Frontend:**
- [ ] Criar página `/projects/[id]/guide` - Guia do produto
- [ ] Formato: Markdown renderizado

---

### FASE 11: CAMADA 11 - QA Guiado (NÃO SÓ TESTES)

**Backend:**
- [ ] Criar serviço `GuidedQA` - QA guiado
- [ ] Gerar:
  - Testes funcionais
  - Testes de fluxo
  - Casos de erro
  - Critérios de aceite baseados na intenção

**Frontend:**
- [ ] Criar página `/projects/[id]/qa` - QA guiado
- [ ] Checklist interativo
- [ ] Pergunta final: "Isso resolve o meu problema?"

---

### FASE 12: CAMADA 12 - Observabilidade e Auditoria

**Backend:**
- [ ] Criar modelo `AuditLog` - Log de auditoria
- [ ] Persistir:
  - Intenção
  - Plano
  - Decisões
  - Branch detectada
  - Tempo por etapa
  - Erros descritivos
  - Ações de agentes

**Segurança:**
- Nunca logar credenciais
- Logs estruturados (JSON)
- Retenção configurável

**Frontend:**
- [ ] Criar página `/projects/[id]/audit` - Auditoria
- [ ] Timeline de eventos
- [ ] Filtros por tipo de evento

---

## Ordem de Implementação

### Sprint 1 (CRÍTICO):
1. CAMADA 1 - Modo Guiado
2. CAMADA 2 - Captura de Intenção
3. CAMADA 3 - Pré-visualização do Plano

### Sprint 2 (CORE):
4. CAMADA 4 - Loop Autônomo
5. CAMADA 5 - Orquestração
6. CAMADA 6 - Avaliação Objetiva

### Sprint 3 (GOVERNANÇA):
7. CAMADA 7 - Governança de Agentes
8. CAMADA 9 - Modo Seguro
9. CAMADA 12 - Observabilidade

### Sprint 4 (UX):
10. CAMADA 8 - Visualização em Tempo Real
11. CAMADA 10 - Enablement
12. CAMADA 11 - QA Guiado

---

## Critério de Sucesso

O Blugreen deve:
- ✅ Ser utilizável por um completo leigo SEM MEDO
- ✅ Desenvolver plataformas complexas de ponta a ponta
- ✅ Explicar tudo o que faz
- ✅ Nunca quebrar silenciosamente
- ✅ Operar como um TIME SÊNIOR GLOBAL DE SOFTWARE

---

## Próximos Passos

1. Validar este plano com stakeholders
2. Começar implementação pela CAMADA 1 (CRÍTICO)
3. Implementar em sprints de 1 semana
4. Validar cada camada antes de avançar

---

**Status:** 📋 Plano criado - Aguardando aprovação para iniciar implementação
