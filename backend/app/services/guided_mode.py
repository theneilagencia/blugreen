"""
Serviço para Modo Guiado (CAMADA 1)

Implementa a lógica de negócio do modo guiado para leigos.

Princípios:
- Linguagem 100% humana
- Máximo 3 perguntas por etapa
- Sistema infere tudo internamente
- Usuário apenas confirma ou ajusta
"""

from typing import List

from app.models.guided_session import (
    GuidedIntent,
    GuidedQuestion,
    GuidedSession,
    GuidedStep,
)


class GuidedModeService:
    """Serviço para Modo Guiado"""
    
    @staticmethod
    def get_steps_for_intent(intent: GuidedIntent) -> List[GuidedStep]:
        """
        Retorna as etapas do modo guiado para uma intenção específica.
        
        Regras:
        - Máximo 3 perguntas por etapa
        - Linguagem 100% humana
        - Sem termos técnicos (stack, branch, pipeline)
        """
        
        if intent == GuidedIntent.CREATE:
            return GuidedModeService._get_create_steps()
        elif intent == GuidedIntent.IMPROVE:
            return GuidedModeService._get_improve_steps()
        elif intent == GuidedIntent.UNDERSTAND:
            return GuidedModeService._get_understand_steps()
        
        raise ValueError(f"Intent desconhecido: {intent}")
    
    @staticmethod
    def _get_create_steps() -> List[GuidedStep]:
        """Etapas para 'Quero criar um produto'"""
        
        return [
            # ETAPA 1: O que você quer criar?
            GuidedStep(
                step_number=1,
                title="O que você quer criar?",
                description="Conte-me sobre o produto que você tem em mente.",
                questions=[
                    GuidedQuestion(
                        id="product_name",
                        text="Como você quer chamar o seu produto?",
                        placeholder="Ex: Meu App de Vendas",
                        help_text="Escolha um nome simples e descritivo.",
                        required=True,
                        field_type="text"
                    ),
                    GuidedQuestion(
                        id="product_description",
                        text="O que o seu produto faz?",
                        placeholder="Ex: Ajuda pequenas empresas a gerenciar vendas",
                        help_text="Descreva em uma frase o que o produto resolve.",
                        required=True,
                        field_type="textarea"
                    ),
                    GuidedQuestion(
                        id="target_audience",
                        text="Quem vai usar o seu produto?",
                        placeholder="Ex: Donos de pequenas lojas",
                        help_text="Pense em quem é o seu público principal.",
                        required=True,
                        field_type="text"
                    )
                ]
            ),
            
            # ETAPA 2: Como as pessoas vão usar?
            GuidedStep(
                step_number=2,
                title="Como as pessoas vão usar?",
                description="Vamos entender como o seu produto funciona.",
                questions=[
                    GuidedQuestion(
                        id="main_features",
                        text="Quais são as 3 coisas mais importantes que o produto faz?",
                        placeholder="Ex: Cadastrar clientes, registrar vendas, ver relatórios",
                        help_text="Liste as funcionalidades principais, uma por linha.",
                        required=True,
                        field_type="textarea"
                    ),
                    GuidedQuestion(
                        id="user_access",
                        text="As pessoas vão precisar fazer login?",
                        placeholder="Sim ou Não",
                        help_text="Se sim, vamos criar um sistema de login seguro.",
                        required=True,
                        field_type="select"
                    ),
                    GuidedQuestion(
                        id="data_storage",
                        text="O produto precisa guardar informações?",
                        placeholder="Sim ou Não",
                        help_text="Ex: dados de clientes, vendas, etc.",
                        required=True,
                        field_type="select"
                    )
                ]
            ),
            
            # ETAPA 3: Onde vai funcionar?
            GuidedStep(
                step_number=3,
                title="Onde vai funcionar?",
                description="Vamos definir como as pessoas vão acessar.",
                questions=[
                    GuidedQuestion(
                        id="access_type",
                        text="Como as pessoas vão acessar o produto?",
                        placeholder="Pelo navegador, celular, ou ambos",
                        help_text="Escolha a melhor opção para o seu público.",
                        required=True,
                        field_type="select"
                    ),
                    GuidedQuestion(
                        id="internet_required",
                        text="Precisa funcionar sem internet?",
                        placeholder="Sim ou Não",
                        help_text="Se sim, vamos preparar para funcionar offline.",
                        required=True,
                        field_type="select"
                    )
                ],
                can_skip=True
            )
        ]
    
    @staticmethod
    def _get_improve_steps() -> List[GuidedStep]:
        """Etapas para 'Quero melhorar um produto existente'"""
        
        return [
            # ETAPA 1: Qual produto?
            GuidedStep(
                step_number=1,
                title="Qual produto você quer melhorar?",
                description="Vamos conectar com o seu produto existente.",
                questions=[
                    GuidedQuestion(
                        id="repository_url",
                        text="Onde está o código do seu produto?",
                        placeholder="Ex: https://github.com/usuario/projeto",
                        help_text="Cole o link do GitHub, GitLab ou Bitbucket.",
                        required=True,
                        field_type="text"
                    ),
                    GuidedQuestion(
                        id="product_status",
                        text="O produto já está funcionando?",
                        placeholder="Sim, está no ar / Não, ainda está em desenvolvimento",
                        help_text="Isso nos ajuda a entender o estágio atual.",
                        required=True,
                        field_type="select"
                    )
                ]
            ),
            
            # ETAPA 2: O que você quer melhorar?
            GuidedStep(
                step_number=2,
                title="O que você quer melhorar?",
                description="Conte-me o que não está bom.",
                questions=[
                    GuidedQuestion(
                        id="improvement_type",
                        text="O que você quer melhorar?",
                        placeholder="Design, velocidade, funcionalidades, ou corrigir problemas",
                        help_text="Escolha a área principal que precisa de atenção.",
                        required=True,
                        field_type="select"
                    ),
                    GuidedQuestion(
                        id="improvement_description",
                        text="Descreva o que você quer que melhore",
                        placeholder="Ex: O site está muito lento, precisa carregar mais rápido",
                        help_text="Seja específico sobre o problema ou melhoria desejada.",
                        required=True,
                        field_type="textarea"
                    ),
                    GuidedQuestion(
                        id="priority_level",
                        text="Isso é urgente?",
                        placeholder="Urgente, importante, ou pode esperar",
                        help_text="Isso nos ajuda a priorizar as melhorias.",
                        required=True,
                        field_type="select"
                    )
                ]
            )
        ]
    
    @staticmethod
    def _get_understand_steps() -> List[GuidedStep]:
        """Etapas para 'Quero entender um repositório'"""
        
        return [
            # ETAPA 1: Qual repositório?
            GuidedStep(
                step_number=1,
                title="Qual código você quer entender?",
                description="Vamos analisar o repositório para você.",
                questions=[
                    GuidedQuestion(
                        id="repository_url",
                        text="Onde está o código?",
                        placeholder="Ex: https://github.com/usuario/projeto",
                        help_text="Cole o link do repositório.",
                        required=True,
                        field_type="text"
                    ),
                    GuidedQuestion(
                        id="understanding_goal",
                        text="O que você quer saber sobre o código?",
                        placeholder="Como funciona, o que faz, como usar, etc.",
                        help_text="Seja específico sobre o que você quer entender.",
                        required=True,
                        field_type="textarea"
                    )
                ]
            )
        ]
    
    @staticmethod
    def infer_technical_details(session: GuidedSession) -> dict:
        """
        Infere detalhes técnicos a partir das respostas do usuário.
        
        O sistema decide internamente:
        - Stack tecnológica
        - Arquitetura
        - Banco de dados
        - Deploy
        
        O usuário NUNCA vê esses termos técnicos.
        """
        
        responses = session.user_responses
        inferences = {}
        
        # Inferir stack baseado nas necessidades
        if session.intent == GuidedIntent.CREATE:
            # Se precisa de login e dados, usa stack completa
            if responses.get("user_access") == "Sim" and responses.get("data_storage") == "Sim":
                inferences["stack"] = "nextjs-postgres-auth"
                inferences["architecture"] = "full-stack"
                inferences["database"] = "postgresql"
                inferences["auth"] = "nextauth"
            
            # Se só precisa de dados, usa stack simples
            elif responses.get("data_storage") == "Sim":
                inferences["stack"] = "nextjs-postgres"
                inferences["architecture"] = "full-stack"
                inferences["database"] = "postgresql"
            
            # Se não precisa de dados, usa stack estática
            else:
                inferences["stack"] = "nextjs-static"
                inferences["architecture"] = "static"
                inferences["database"] = None
            
            # Inferir tipo de deploy
            access_type = responses.get("access_type", "")
            if "celular" in access_type.lower():
                inferences["deploy_type"] = "mobile-web"
            else:
                inferences["deploy_type"] = "web"
            
            # Inferir offline support
            if responses.get("internet_required") == "Sim":
                inferences["offline_support"] = True
                inferences["pwa"] = True
            else:
                inferences["offline_support"] = False
                inferences["pwa"] = False
        
        elif session.intent == GuidedIntent.IMPROVE:
            # Para melhorias, inferir a partir do repositório
            inferences["mode"] = "improvement"
            inferences["analysis_required"] = True
            
            improvement_type = responses.get("improvement_type", "")
            if "design" in improvement_type.lower():
                inferences["focus"] = "ui-ux"
            elif "velocidade" in improvement_type.lower():
                inferences["focus"] = "performance"
            elif "funcionalidades" in improvement_type.lower():
                inferences["focus"] = "features"
            else:
                inferences["focus"] = "bugfix"
        
        elif session.intent == GuidedIntent.UNDERSTAND:
            # Para entendimento, apenas análise
            inferences["mode"] = "analysis"
            inferences["generate_documentation"] = True
        
        return inferences
    
    @staticmethod
    def generate_human_summary(session: GuidedSession) -> str:
        """
        Gera um resumo em linguagem humana do que o sistema vai fazer.
        
        Sem termos técnicos.
        """
        
        responses = session.user_responses
        inferences = session.system_inferences
        
        if session.intent == GuidedIntent.CREATE:
            product_name = responses.get("product_name", "seu produto")
            description = responses.get("product_description", "")
            target = responses.get("target_audience", "seus usuários")
            
            summary = f"Vou criar o **{product_name}** para {target}.\n\n"
            summary += f"O produto vai {description}.\n\n"
            
            # Explicar o que vai ser criado (sem termos técnicos)
            if inferences.get("auth"):
                summary += "✅ Vou criar um sistema de login seguro\n"
            
            if inferences.get("database"):
                summary += "✅ Vou preparar para guardar informações de forma segura\n"
            
            if inferences.get("pwa"):
                summary += "✅ Vou fazer funcionar sem internet quando necessário\n"
            
            if inferences.get("deploy_type") == "mobile-web":
                summary += "✅ Vou otimizar para celular\n"
            
            summary += "\nVocê vai poder acessar o produto pelo navegador assim que estiver pronto."
        
        elif session.intent == GuidedIntent.IMPROVE:
            improvement = responses.get("improvement_description", "melhorias")
            
            summary = f"Vou analisar o seu produto e fazer as seguintes melhorias:\n\n"
            summary += f"📝 {improvement}\n\n"
            
            focus = inferences.get("focus")
            if focus == "ui-ux":
                summary += "Vou focar em deixar o design mais bonito e fácil de usar."
            elif focus == "performance":
                summary += "Vou focar em deixar tudo mais rápido."
            elif focus == "features":
                summary += "Vou adicionar as funcionalidades que você pediu."
            else:
                summary += "Vou corrigir os problemas que você mencionou."
        
        elif session.intent == GuidedIntent.UNDERSTAND:
            goal = responses.get("understanding_goal", "")
            
            summary = f"Vou analisar o código e explicar:\n\n"
            summary += f"📚 {goal}\n\n"
            summary += "Vou criar um guia em linguagem simples para você entender como tudo funciona."
        
        return summary
