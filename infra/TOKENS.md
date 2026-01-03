# Tokens de API - Blugreen

**Data da última atualização:** 2026-01-03

Este documento registra todos os tokens de API criados para automação e integração de serviços no projeto Blugreen. **Os valores reais dos tokens NUNCA devem ser armazenados neste arquivo.**

## Coolify API Token

| Atributo | Valor |
| :--- | :--- |
| **Identificador** | `blugreen-deploy-token` |
| **Serviço** | Coolify |
| **Descrição** | Token para permitir o acionamento de deploys via API. |
| **Permissões (Escopo)** | `deploy` |
| **Data de Criação** | 2026-01-03 |
| **Status** | Ativo |

### Detalhes de Uso

Este token possui o escopo mínimo necessário para acionar um deploy. Ele pode ser usado em scripts de CI/CD ou outras automações para iniciar um novo build e deploy da aplicação no Coolify.

**Exemplo de Requisição:**

```bash
curl -H "Authorization: Bearer <VALOR_DO_TOKEN>" \
     -X POST https://coolify.blugreen.com.br/api/v1/deploy?uuid=<APP_UUID>&force=false
```

### Notas de Segurança

- O valor real do token foi exibido apenas no momento da sua criação e não pode ser recuperado.
- Se o token for perdido, ele deve ser revogado e um novo deve ser gerado.
- O token deve ser armazenado como um segredo em qualquer ferramenta de CI/CD (ex: GitHub Secrets, GitLab CI/CD Variables).
- O acesso à API do Coolify está configurado para permitir requisições de qualquer endereço IP. Para um ambiente de produção mais restrito, recomenda-se limitar os IPs permitidos nas configurações do Coolify (`Settings > Advanced > Allowed IPs for API Access`).
