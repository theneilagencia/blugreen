"""
Serviço de Captura de Intenção (CAMADA 2)

Extrai e valida a intenção do usuário, transformando-a em um contrato imutável.

Princípios:
- A IA NÃO pode agir sem essa intenção validada
- A intenção vira contrato imutável durante a execução
- Nenhuma ação sem intenção explícita
"""

import hashlib
import json
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.models.guided_session import GuidedSession
from app.models.project_intent import (
    IntentStatus,
    IntentType,
    IntentViolation,
    ProjectIntent,
    RiskLevel,
)


class IntentCaptureService:
    """Serviço para captura e validação de intenção"""
    
    @staticmethod
    def create_intent_from_guided_session(
        session: Session,
        guided_session: GuidedSession
    ) -> ProjectIntent:
        """
        Cria uma intenção a partir de uma sessão guiada.
        
        Extrai os campos obrigatórios das respostas do usuário.
        """
        
        responses = guided_session.user_responses
        inferences = guided_session.system_inferences
        
        # Mapear intent
        intent_type_map = {
            "criar": IntentType.CREATE,
            "melhorar": IntentType.IMPROVE,
            "entender": IntentType.UNDERSTAND
        }
        intent_type = intent_type_map.get(guided_session.intent, IntentType.CREATE)
        
        # Extrair campos obrigatórios
        product_name = responses.get("product_name", "Produto sem nome")
        product_description = responses.get("product_description", "")
        
        # Inferir business_goal a partir da descrição
        business_goal = IntentCaptureService._infer_business_goal(
            product_description,
            responses.get("target_audience", "")
        )
        
        target_audience = responses.get("target_audience", "Público geral")
        
        # Inferir success_criteria
        success_criteria = IntentCaptureService._infer_success_criteria(
            intent_type,
            responses
        )
        
        # Inferir constraints
        constraints = IntentCaptureService._infer_constraints(
            responses,
            inferences
        )
        
        # Inferir risk_level
        risk_level = IntentCaptureService._infer_risk_level(
            intent_type,
            responses
        )
        
        # Criar intenção
        intent = ProjectIntent(
            intent_type=intent_type,
            status=IntentStatus.DRAFT,
            product_name=product_name,
            product_description=product_description,
            business_goal=business_goal,
            target_audience=target_audience,
            success_criteria=success_criteria,
            constraints=constraints,
            risk_level=risk_level,
            main_features=responses.get("main_features"),
            technical_requirements=inferences,
            additional_context=responses.get("improvement_description") or responses.get("understanding_goal"),
            repository_url=responses.get("repository_url"),
            guided_session_id=guided_session.id
        )
        
        session.add(intent)
        session.commit()
        session.refresh(intent)
        
        return intent
    
    @staticmethod
    def validate_intent(
        session: Session,
        intent: ProjectIntent,
        validated_by: str
    ) -> ProjectIntent:
        """
        Valida uma intenção.
        
        Verifica se todos os campos obrigatórios estão preenchidos.
        """
        
        # Verificar campos obrigatórios
        required_fields = [
            "product_name",
            "product_description",
            "business_goal",
            "target_audience",
            "success_criteria",
            "constraints"
        ]
        
        missing_fields = []
        for field in required_fields:
            if not getattr(intent, field):
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Campos obrigatórios faltando: {', '.join(missing_fields)}")
        
        # Atualizar status
        intent.status = IntentStatus.VALIDATED
        intent.validated_at = datetime.utcnow()
        intent.validated_by = validated_by
        
        session.add(intent)
        session.commit()
        session.refresh(intent)
        
        return intent
    
    @staticmethod
    def freeze_intent(
        session: Session,
        intent: ProjectIntent
    ) -> ProjectIntent:
        """
        Congela uma intenção, tornando-a IMUTÁVEL.
        
        Após congelada, a intenção não pode mais ser alterada.
        Qualquer tentativa de violação será registrada.
        """
        
        if intent.status != IntentStatus.VALIDATED:
            raise ValueError("Só é possível congelar intenções validadas")
        
        # Gerar hash da intenção
        intent_data = {
            "product_name": intent.product_name,
            "product_description": intent.product_description,
            "business_goal": intent.business_goal,
            "target_audience": intent.target_audience,
            "success_criteria": intent.success_criteria,
            "constraints": intent.constraints,
            "risk_level": intent.risk_level,
            "main_features": intent.main_features
        }
        
        intent_json = json.dumps(intent_data, sort_keys=True)
        intent_hash = hashlib.sha256(intent_json.encode()).hexdigest()
        
        # Congelar
        intent.status = IntentStatus.FROZEN
        intent.frozen_at = datetime.utcnow()
        intent.intent_hash = intent_hash
        
        session.add(intent)
        session.commit()
        session.refresh(intent)
        
        return intent
    
    @staticmethod
    def check_action_against_intent(
        session: Session,
        intent: ProjectIntent,
        action_description: str,
        attempted_by: str
    ) -> tuple[bool, Optional[str]]:
        """
        Verifica se uma ação viola o contrato de intenção.
        
        Retorna (is_allowed, violation_reason)
        """
        
        if intent.status != IntentStatus.FROZEN:
            return True, None  # Intenção não congelada, permitir
        
        # Verificar constraints
        constraints_lower = intent.constraints.lower()
        action_lower = action_description.lower()
        
        # Regras de violação
        violations = []
        
        # 1. Não alterar contratos públicos existentes
        if "não alterar" in constraints_lower and any(word in action_lower for word in ["alterar", "modificar", "mudar"]):
            violations.append("Tentativa de alterar algo que não pode ser alterado")
        
        # 2. Não remover funcionalidades
        if "não remover" in constraints_lower and any(word in action_lower for word in ["remover", "deletar", "excluir"]):
            violations.append("Tentativa de remover algo que não pode ser removido")
        
        # 3. Verificar risk_level
        high_risk_actions = ["deploy", "produção", "publicar", "deletar banco"]
        if intent.risk_level == RiskLevel.MINIMAL and any(word in action_lower for word in high_risk_actions):
            violations.append(f"Ação de alto risco não permitida (risk_level={intent.risk_level})")
        
        if violations:
            # Registrar violação
            violation = IntentViolation(
                intent_id=intent.id,
                attempted_action=action_description,
                violated_constraint=intent.constraints,
                violation_details="; ".join(violations),
                attempted_by=attempted_by,
                action_taken="blocked"
            )
            session.add(violation)
            session.commit()
            
            return False, violations[0]
        
        return True, None
    
    @staticmethod
    def _infer_business_goal(description: str, target: str) -> str:
        """Infere o objetivo de negócio"""
        if not description:
            return "Resolver um problema para os usuários"
        
        return f"Ajudar {target} a {description.lower()}"
    
    @staticmethod
    def _infer_success_criteria(intent_type: IntentType, responses: dict) -> str:
        """Infere critérios de sucesso"""
        if intent_type == IntentType.CREATE:
            return "O produto está funcionando e os usuários conseguem usar as funcionalidades principais"
        elif intent_type == IntentType.IMPROVE:
            improvement = responses.get("improvement_description", "melhorias")
            return f"As melhorias foram aplicadas: {improvement}"
        else:  # UNDERSTAND
            return "O código foi analisado e documentado de forma clara"
    
    @staticmethod
    def _infer_constraints(responses: dict, inferences: dict) -> str:
        """Infere restrições"""
        constraints = []
        
        # Constraints baseadas nas respostas
        if responses.get("user_access") == "Sim":
            constraints.append("Não comprometer a segurança dos dados de usuários")
        
        if responses.get("data_storage") == "Sim":
            constraints.append("Não perder dados armazenados")
        
        if responses.get("internet_required") == "Sim":
            constraints.append("Manter funcionalidade offline")
        
        # Constraints baseadas no tipo
        if inferences.get("mode") == "improvement":
            constraints.append("Não quebrar funcionalidades existentes")
            constraints.append("Não alterar contratos públicos da API")
        
        if not constraints:
            constraints.append("Seguir melhores práticas de engenharia de software")
        
        return "; ".join(constraints)
    
    @staticmethod
    def _infer_risk_level(intent_type: IntentType, responses: dict) -> RiskLevel:
        """Infere nível de risco"""
        if intent_type == IntentType.CREATE:
            # Criar do zero = risco baixo
            return RiskLevel.LOW
        
        elif intent_type == IntentType.IMPROVE:
            # Melhorar existente = risco depende da urgência
            priority = responses.get("priority_level", "").lower()
            if "urgente" in priority:
                return RiskLevel.MEDIUM
            else:
                return RiskLevel.LOW
        
        else:  # UNDERSTAND
            # Apenas analisar = risco mínimo
            return RiskLevel.MINIMAL
