# Infraestrutura - Blugreen

**Data da última atualização:** 2026-01-03

## Visão Geral

Este diretório contém toda a documentação relacionada à infraestrutura, deploy e configuração do projeto **Blugreen**.

O objetivo é manter um registro claro, transparente e versionado de todas as decisões, configurações e ativos de infraestrutura, garantindo que qualquer membro da equipe possa entender o ambiente e, se necessário, reconstruí-lo.

## Estrutura da Documentação

| Arquivo | Descrição |
| :--- | :--- |
| `README.md` | Visão geral da documentação de infraestrutura (este arquivo). |
| `SERVERS.md` | Detalhes sobre os servidores provisionados, incluindo especificações, provedor, IP, e sistema operacional. |
| `DOMAINS.md` | Documentação sobre os domínios e subdomínios utilizados, incluindo provedor de DNS e configurações. |
| `USERS_AND_ACCESS.md` | Informações sobre usuários, grupos e permissões de acesso aos sistemas e serviços. |
| `TOKENS.md` | Registro de todos os tokens de API gerados, seus escopos, usos e identificadores. **Valores reais de tokens NUNCA são armazenados aqui.** |
| `DEPLOYMENT_SETUP.md` | Guia passo-a-passo da configuração do deploy, incluindo a plataforma utilizada (Coolify), configuração das aplicações e processo de deploy automático. |
| `SECURITY_NOTES.md` | Notas importantes sobre segurança, incluindo configuração de firewall, políticas de acesso e outras decisões de segurança. |

## Filosofia

- **Infraestrutura como Código (IaC) e Documentação:** Embora não estejamos usando ferramentas de IaC como Terraform neste momento, a documentação serve como uma forma de "Infraestrutura como Documentação", permitindo a reprodutibilidade do ambiente.
- **Transparência:** Todas as ações e configurações devem ser documentadas.
- **Segurança:** Segredos e informações sensíveis (como senhas e valores de tokens) NUNCA devem ser commitados neste repositório. A documentação deve referenciar apenas os identificadores e o propósito desses segredos.

## Como Manter a Documentação

Qualquer alteração na infraestrutura, seja uma mudança de configuração no servidor, uma nova regra de firewall, a criação de um novo token ou uma alteração no processo de deploy, **DEVE** ser refletida na documentação correspondente neste diretório.

O processo é:
1. Realizar a alteração na infraestrutura.
2. Atualizar o arquivo Markdown correspondente com os novos detalhes.
3. Fazer o commit da alteração na documentação com uma mensagem clara e descritiva.
