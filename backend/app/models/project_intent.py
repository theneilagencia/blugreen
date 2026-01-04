"""
Modelo para Intenção do Projeto (CAMADA 2)

A intenção é um CONTRATO IMUTÁVEL que governa toda a execução.

Princípios:
- A IA NÃO pode agir sem essa intenção validada
- A intenção vira contrato imutável durante a execução
- Nenhuma ação sem intenção explícita
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel, Relationship


class IntentType(str, Enum):
    """Tipo de intenção"""
    CREATE = "create"  # Criar produto do zero
    IMPROVE = "improve"  # Melhorar produto existente
    UNDERSTAND = "understand"  # Entender repositório


class RiskLevel(str, Enum):
    """Nível de risco aceitável"""
    MINIMAL = "minimal"  # Apenas mudanças seguras
    LOW = "low"  # Mudanças com impacto limitado
    MEDIUM = "medium"  # Mudanças moderadas
    HIGH = "high"  # Mudanças significativas


class IntentStatus(str, Enum):
    """Status da intenção"""
    DRAFT = "draft"  # Rascunho
    VALIDATED = "validated"  # Validada
    FROZEN = "frozen"  # Congelada (imutável)
    COMPLETED = "completed"  # Concluída
    CANCELLED = "cancelled"  # Cancelada


class ProjectIntent(SQLModel, table=True):
    """
    Intenção do Projeto - CAMADA 2
    
    Contrato imutável que governa toda a execução.
    
    Campos obrigatórios (conforme especificação):
    - Qual é o produto?
    - Qual o objetivo de negócio?
    - Para quem é?
    - O que define sucesso?
    - O que NÃO pode ser alterado?
    - Qual o nível de risco aceitável?
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Tipo de intenção
    intent_type: IntentType = Field(index=True)
    
    # Status da intenção
    status: IntentStatus = Field(default=IntentStatus.DRAFT, index=True)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CAMPOS OBRIGATÓRIOS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    # 1. Qual é o produto?
    product_name: str = Field(index=True)
    product_description: str  # O que o produto faz?
    
    # 2. Qual o objetivo de negócio?
    business_goal: str  # Por que este produto existe?
    
    # 3. Para quem é?
    target_audience: str  # Quem vai usar?
    
    # 4. O que define sucesso?
    success_criteria: str  # Como saber se deu certo?
    
    # 5. O que NÃO pode ser alterado?
    constraints: str  # Restrições e limitações
    
    # 6. Qual o nível de risco aceitável?
    risk_level: RiskLevel = Field(default=RiskLevel.LOW)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CAMPOS ADICIONAIS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    # Funcionalidades principais
    main_features: Optional[str] = None  # Lista de features
    
    # Requisitos técnicos inferidos
    technical_requirements: dict = Field(default_factory=dict, sa_column_kwargs={"type_": "JSON"})
    
    # Contexto adicional
    additional_context: Optional[str] = None
    
    # Repositório (para improve/understand)
    repository_url: Optional[str] = None
    repository_branch: Optional[str] = None
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # RELACIONAMENTOS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    # Projeto associado
    project_id: Optional[int] = Field(default=None, foreign_key="project.id", index=True)
    
    # Sessão guiada que originou esta intenção
    guided_session_id: Optional[int] = Field(default=None, foreign_key="guidedsession.id")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # AUDITORIA
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    validated_at: Optional[datetime] = None
    frozen_at: Optional[datetime] = None  # Quando virou imutável
    completed_at: Optional[datetime] = None
    
    # Quem validou (usuário ou sistema)
    validated_by: Optional[str] = None
    
    # Hash da intenção (para garantir imutabilidade)
    intent_hash: Optional[str] = None


class ProjectIntentCreate(SQLModel):
    """Payload para criar intenção"""
    intent_type: IntentType
    product_name: str
    product_description: str
    business_goal: str
    target_audience: str
    success_criteria: str
    constraints: str
    risk_level: RiskLevel = RiskLevel.LOW
    main_features: Optional[str] = None
    additional_context: Optional[str] = None
    repository_url: Optional[str] = None
    repository_branch: Optional[str] = None


class ProjectIntentRead(SQLModel):
    """Resposta de leitura de intenção"""
    id: int
    intent_type: IntentType
    status: IntentStatus
    product_name: str
    product_description: str
    business_goal: str
    target_audience: str
    success_criteria: str
    constraints: str
    risk_level: RiskLevel
    main_features: Optional[str]
    technical_requirements: dict
    additional_context: Optional[str]
    repository_url: Optional[str]
    project_id: Optional[int]
    guided_session_id: Optional[int]
    created_at: datetime
    validated_at: Optional[datetime]
    frozen_at: Optional[datetime]
    intent_hash: Optional[str]


class ProjectIntentValidate(SQLModel):
    """Payload para validar intenção"""
    validated_by: str  # Quem está validando


class IntentViolation(SQLModel):
    """
    Violação de Intenção
    
    Registra quando uma ação tenta violar o contrato imutável.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    
    intent_id: int = Field(foreign_key="projectintent.id", index=True)
    
    # O que foi tentado
    attempted_action: str
    
    # Qual constraint foi violada
    violated_constraint: str
    
    # Detalhes da violação
    violation_details: str
    
    # Quem tentou (agente ou usuário)
    attempted_by: str
    
    # Ação tomada
    action_taken: str  # blocked, warned, escalated
    
    # Timestamp
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
