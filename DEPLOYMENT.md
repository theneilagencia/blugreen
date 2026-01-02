# Deploy em Produção

Deploy deve ser:

- Automático
- Repetível
- Versionado
- Com rollback

Passos:
1. Build Docker
2. Executar testes
3. Publicar via Coolify
4. Healthcheck
5. Se falhar, rollback automático

Variáveis de ambiente nunca devem ser hardcoded.
