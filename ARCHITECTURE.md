# Arquitetura do Sistema

Arquitetura em camadas:

1. Interface do Usuário
   - Web (Next.js)
   - Chat orientado a tarefas

2. Orquestrador Central
   - Planejamento
   - Gerenciamento de estado
   - Governança MCP (Model, Context, Policy)

3. Agentes Especializados
   - Arquiteto
   - Backend
   - Frontend
   - Infra
   - QA

4. Executor
   - Execução de código
   - Testes
   - Build
   - Sandbox

5. CI/CD
   - Build
   - Testes
   - Deploy
   - Rollback

Nenhuma camada deve acessar outra diretamente sem contrato explícito.
