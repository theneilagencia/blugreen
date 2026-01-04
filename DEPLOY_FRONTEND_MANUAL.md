# Deploy Manual do Frontend - Guia Passo a Passo

## 📋 Contexto

O código do frontend foi corrigido e commitado (`0bea241`), mas o build Docker está demorando. Este guia permite que você faça o deploy manualmente.

---

## 🔑 Credenciais

**Servidor:** 161.97.156.108  
**Usuário:** root  
**Senha:** Zc3TWx2zbhb3T7

---

## 🚀 Opção 1: Via Coolify (Recomendado)

### Passo 1: Acessar Coolify

1. Abra o navegador
2. Acesse: `https://vmi1836594.contaboserver.net` (ou o endereço correto do Coolify)
3. Faça login

### Passo 2: Acionar Deploy

1. Navegue até o projeto **blugreen**
2. Localize o serviço **frontend**
3. Clique em **"Deploy"** ou **"Redeploy"**
4. Aguarde o deploy concluir (pode levar 5-10 minutos)

### Passo 3: Validar

1. Acesse: `https://app.blugreen.com.br`
2. Navegue até a lista de projetos
3. Tente deletar um projeto
4. Verifique se as mensagens estão corretas (sem "Failed to delete project")

---

## 🔧 Opção 2: Via SSH (Manual)

Se o Coolify não estiver acessível, você pode fazer o deploy manualmente via SSH.

### Passo 1: Conectar no Servidor

```bash
ssh root@161.97.156.108
# Senha: Zc3TWx2zbhb3T7
```

### Passo 2: Atualizar Código

```bash
cd /tmp/blugreen
git pull origin main
```

### Passo 3: Build da Imagem

```bash
docker build -t lwgogcgw0ogw4s0cokowkwco_frontend:0bea241 \
  --build-arg NEXT_PUBLIC_API_URL=https://api.blugreen.com.br \
  -f frontend/Dockerfile \
  frontend/
```

**Nota:** Este passo pode levar 5-10 minutos.

### Passo 4: Verificar Imagem

```bash
docker images | grep lwgogcgw0ogw4s0cokowkwco_frontend | grep 0bea241
```

Você deve ver algo como:
```
lwgogcgw0ogw4s0cokowkwco_frontend:0bea241    abc123def456    1.2GB    500MB
```

### Passo 5: Atualizar docker-compose.yaml

```bash
cd /data/coolify/applications/lwgogcgw0ogw4s0cokowkwco

# Backup do arquivo atual
cp docker-compose.yaml docker-compose.yaml.bak

# Atualizar tag da imagem
sed -i 's/c4b07cdc18e0dda6eafd13ced9c262aa73cfad8b/0bea241/g' docker-compose.yaml

# Verificar mudança
grep 'image:.*frontend' docker-compose.yaml | head -1
```

Deve exibir:
```
        image: 'lwgogcgw0ogw4s0cokowkwco_frontend:0bea241'
```

### Passo 6: Parar Container Antigo

```bash
docker stop frontend-lwgogcgw0ogw4s0cokowkwco-103919570320
docker rm frontend-lwgogcgw0ogw4s0cokowkwco-103919570320
```

### Passo 7: Iniciar Novo Container

```bash
cd /data/coolify/applications/lwgogcgw0ogw4s0cokowkwco
docker compose up -d frontend
```

### Passo 8: Verificar Container

```bash
docker ps | grep frontend
```

Deve exibir:
```
abc123def456   lwgogcgw0ogw4s0cokowkwco_frontend:0bea241   ...   Up X seconds   3000/tcp   frontend-lwgogcgw0ogw4s0cokowkwco-103919570320
```

### Passo 9: Verificar Logs

```bash
docker logs frontend-lwgogcgw0ogw4s0cokowkwco-103919570320
```

Deve exibir:
```
ready - started server on 0.0.0.0:3000, url: http://localhost:3000
```

---

## ✅ Validação

### 1. Acessar Frontend

Abra o navegador e acesse: `https://app.blugreen.com.br`

### 2. Testar DELETE

#### Teste 1: Projeto inexistente (404)
1. Abra o DevTools (F12)
2. Execute no Console:
```javascript
fetch('https://api.blugreen.com.br/projects/99999', {
  method: 'DELETE',
  credentials: 'include'
}).then(r => r.json()).then(console.log)
```

**Esperado:**
```json
{
  "error_code": "PROJECT_NOT_FOUND",
  "message": "Projeto não encontrado."
}
```

#### Teste 2: Deletar projeto via UI
1. Navegue até a lista de projetos
2. Clique no botão de deletar de um projeto
3. Confirme a exclusão

**Esperado:**
- ✅ Se projeto for DRAFT/TERMINATED: sucesso, projeto desaparece
- ✅ Se projeto for ACTIVE: mensagem "Este projeto está ativo. Encerre-o antes de excluir."
- ✅ Se projeto tiver vínculos: mensagem "O projeto ainda possui vínculos internos."

**NÃO deve aparecer:**
- ❌ "Failed to delete project"
- ❌ Erro de CORS
- ❌ Erro técnico

---

## 🐛 Troubleshooting

### Problema: Build demora muito

**Solução:** O build do Next.js pode levar 5-10 minutos. Seja paciente.

### Problema: Container não inicia

**Verificar logs:**
```bash
docker logs frontend-lwgogcgw0ogw4s0cokowkwco-103919570320
```

**Possíveis causas:**
- Porta 3000 já em uso
- Erro no build
- Falta de memória

### Problema: 503 no frontend

**Causa:** Traefik não está roteando para o container.

**Solução:** Verificar labels do container:
```bash
docker inspect frontend-lwgogcgw0ogw4s0cokowkwco-103919570320 | grep -A 20 Labels
```

Deve ter labels do Traefik. Se não tiver, o container foi iniciado sem docker-compose.

**Corrigir:**
```bash
cd /data/coolify/applications/lwgogcgw0ogw4s0cokowkwco
docker compose up -d frontend
```

### Problema: Frontend mostra versão antiga

**Causa:** Cache do navegador.

**Solução:**
1. Abra DevTools (F12)
2. Clique com botão direito no botão de reload
3. Selecione "Empty Cache and Hard Reload"

---

## 📞 Suporte

Se encontrar problemas:

1. Verifique os logs do container
2. Verifique se a imagem foi criada corretamente
3. Verifique se o docker-compose.yaml foi atualizado
4. Reinicie o container via docker compose

---

## ✅ Checklist Final

- [ ] Código atualizado (`git pull`)
- [ ] Imagem Docker criada (`docker build`)
- [ ] docker-compose.yaml atualizado
- [ ] Container antigo parado e removido
- [ ] Novo container iniciado via docker compose
- [ ] Container está rodando (`docker ps`)
- [ ] Frontend acessível em https://app.blugreen.com.br
- [ ] DELETE funciona sem "Failed to delete project"
- [ ] Mensagens corretas exibidas

---

**Data:** 04 de Janeiro de 2026  
**Commit:** 0bea241  
**Backend:** ✅ Operacional  
**Frontend:** ⏳ Aguardando deploy manual
