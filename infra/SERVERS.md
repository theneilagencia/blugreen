# Servidores - Blugreen

**Data da última atualização:** 2026-01-03

Este documento detalha todos os servidores provisionados para o projeto Blugreen.

## Servidor de Produção/Staging

| Atributo | Valor |
| :--- | :--- |
| **Identificador** | `prod-server-01` |
| **Provedor** | Contabo |
| **Plano** | VPS S |
| **Localização** | Germany |
| **Hostname** | `vmi1836594.contaboserver.net` |
| **IP Público** | `161.97.156.108` |
| **Sistema Operacional** | Ubuntu 22.04 LTS (atualizado para 24.04.3 LTS) |
| **CPU** | 4 vCores (AMD EPYC) |
| **RAM** | 8 GB |
| **Armazenamento** | 200 GB NVMe |

### Acesso

- **Método:** SSH
- **Porta:** 22
- **Usuário:** `root`
- **Autenticação:** Senha (o ideal é migrar para autenticação por chave SSH no futuro)

### Software Instalado

- **Docker:** Versão 29.1.3
- **Docker Compose:** Versão v5.0.1
- **Coolify:** Versão v4.0.0-beta.460
- **UFW (Firewall):** Ativo

### Configuração de Rede

- **Firewall (UFW):**
  - Porta `22/tcp` (SSH): Permitido
  - Porta `80/tcp` (HTTP): Permitido
  - Porta `443/tcp` (HTTPS): Permitido

### Observações

- Este servidor hospeda a instância do Coolify, que por sua vez gerencia o deploy e a execução das aplicações (frontend e backend).
- O servidor foi atualizado para a versão mais recente do Ubuntu LTS no momento da configuração.
- A senha de acesso root foi fornecida inicialmente e deve ser trocada e gerenciada de forma segura. Recomenda-se fortemente a desativação do login root com senha e a utilização de chaves SSH com chaves SSH para maior segurança.
