"""
Modelo para Sessão Guiada (CAMADA 1)

Uma sessão guiada captura a intenção do usuário de forma simplificada,
sem expor termos técnicos. O sistema infere tudo internamente.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class GuidedIntent(str, Enum):
    """
    Intenções disponíveis no modo guiado.
    
    Linguagem 100% humana, sem termos técnicos.
    """
    CREATE = "criar"  # "Quero criar um produto"
    IMPROVE = "melhorar"  # "Quero melhorar um produto existente"
    UNDERSTAND = "entender"  # "Quero entender um repositório"


class GuidedSessionStatus(str, Enum):
    """Status da sessão guiada"""
    STARTED = "started"  # Sessão iniciada
    COLLECTING = "collecting"  # Coletando informações
    CONFIRMING = "confirming"  # Aguardando confirmação
    EXECUTING = "executing"  # Executando
    COMPLETED = "completed"  # Concluída
    CANCELLED = "cancelled"  # Cancelada


class GuidedSession(SQLModel, table=True):
    """
    Sessão Guiada - CAMADA 1
    
    Armazena o estado de uma sessão no modo guiado para leigos.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Intenção do usuário (linguagem humana)
    intent: GuidedIntent = Field(index=True)
    
    # Status da sessão
    status: GuidedSessionStatus = Field(default=GuidedSessionStatus.STARTED, index=True)
    
    # Respostas do usuário (JSON)
    # Exemplo: {"product_name": "Meu App", "target_audience": "Pequenas empresas"}
    user_responses: dict = Field(default_factory=dict, sa_column_kwargs={"type_": "JSON"})
    
    # Inferências do sistema (JSON)
    # Exemplo: {"stack": "nextjs", "database": "postgresql"}
    system_inferences: dict = Field(default_factory=dict, sa_column_kwargs={"type_": "JSON"})
    
    # ID do projeto criado (se aplicável)
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Metadados
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None


class GuidedSessionCreate(SQLModel):
    """Payload para criar sessão guiada"""
    intent: GuidedIntent


class GuidedSessionUpdate(SQLModel):
    """Payload para atualizar sessão guiada"""
    user_responses: Optional[dict] = None
    status: Optional[GuidedSessionStatus] = None


class GuidedSessionRead(SQLModel):
    """Resposta de leitura de sessão guiada"""
    id: int
    intent: GuidedIntent
    status: GuidedSessionStatus
    user_responses: dict
    system_inferences: dict
    project_id: Optional[int]
    created_at: datetime
    updated_at: datetime


class GuidedQuestion(SQLModel):
    """
    Pergunta do modo guiado.
    
    Linguagem 100% humana, máximo 3 perguntas por etapa.
    """
    id: str  # Identificador único da pergunta
    text: str  # Texto da pergunta em linguagem humana
    placeholder: str  # Placeholder para o input
    help_text: Optional[str] = None  # Texto de ajuda (opcional)
    required: bool = True  # Se é obrigatória
    field_type: str = "text"  # Tipo do campo: text, textarea, select


class GuidedStep(SQLModel):
    """
    Etapa do modo guiado.
    
    Cada etapa contém no máximo 3 perguntas.
    """
    step_number: int
    title: str  # Título da etapa em linguagem humana
    description: str  # Descrição da etapa
    questions: list[GuidedQuestion]
    can_skip: bool = False  # Se pode pular esta etapa
