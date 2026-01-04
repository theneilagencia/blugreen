"""
Modelo para Loop Autônomo Controlado (CAMADA 4)

O loop NÃO roda infinitamente. Tem limites e pausas obrigatórias.

Princípios (conforme especificação):
- Limite de tempo (ex: 30 min)
- Limite de ações (ex: 50 ações)
- Limite de custo (ex: $5)
- Pausa obrigatória a cada X iterações
- Usuário pode cancelar a qualquer momento
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class LoopStatus(str, Enum):
    """Status do loop de execução"""
    PENDING = "pending"  # Aguardando início
    RUNNING = "running"  # Executando
    PAUSED = "paused"  # Pausado para revisão
    WAITING_APPROVAL = "waiting_approval"  # Aguardando aprovação do usuário
    COMPLETED = "completed"  # Concluído
    CANCELLED = "cancelled"  # Cancelado
    FAILED = "failed"  # Falhou
    LIMIT_REACHED = "limit_reached"  # Limite atingido


class PauseReason(str, Enum):
    """Motivo da pausa"""
    ITERATION_LIMIT = "iteration_limit"  # Limite de iterações
    TIME_LIMIT = "time_limit"  # Limite de tempo
    COST_LIMIT = "cost_limit"  # Limite de custo
    ACTION_LIMIT = "action_limit"  # Limite de ações
    USER_REQUEST = "user_request"  # Usuário solicitou
    QUALITY_GATE_FAILED = "quality_gate_failed"  # Quality gate falhou
    INTENT_VIOLATION = "intent_violation"  # Violação de intenção
    MANUAL_REVIEW_REQUIRED = "manual_review_required"  # Revisão manual necessária


class ExecutionLoop(SQLModel, table=True):
    """
    Loop Autônomo Controlado - CAMADA 4
    
    O loop NÃO roda infinitamente. Tem limites e pausas obrigatórias.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Projeto e intenção
    project_id: int = Field(foreign_key="project.id", index=True)
    intent_id: int = Field(foreign_key="projectintent.id", index=True)
    
    # Status
    status: LoopStatus = Field(default=LoopStatus.PENDING, index=True)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # LIMITES (conforme especificação)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    # Limite de tempo (em minutos)
    max_time_minutes: int = Field(default=30)
    
    # Limite de ações
    max_actions: int = Field(default=50)
    
    # Limite de custo (em dólares)
    max_cost_usd: float = Field(default=5.0)
    
    # Limite de iterações antes de pausa obrigatória
    max_iterations_before_pause: int = Field(default=10)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CONTADORES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    # Tempo decorrido (em segundos)
    elapsed_seconds: int = Field(default=0)
    
    # Ações executadas
    actions_executed: int = Field(default=0)
    
    # Custo acumulado (em dólares)
    cost_accumulated_usd: float = Field(default=0.0)
    
    # Iterações executadas
    iterations_executed: int = Field(default=0)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PAUSAS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    # Número de pausas
    pause_count: int = Field(default=0)
    
    # Última pausa
    last_pause_reason: Optional[PauseReason] = None
    last_pause_at: Optional[datetime] = None
    
    # Mensagem da última pausa
    last_pause_message: Optional[str] = None
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PROGRESSO
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    # Progresso estimado (0-100)
    progress_percentage: int = Field(default=0)
    
    # Fase atual
    current_phase: Optional[str] = None
    
    # Última ação executada
    last_action: Optional[str] = None
    last_action_at: Optional[datetime] = None
    
    # Próxima ação planejada
    next_action: Optional[str] = None
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # RESULTADOS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    # Resultado final
    result: Optional[str] = None
    
    # Artefatos gerados
    artifacts: dict = Field(default_factory=dict, sa_column_kwargs={"type_": "JSON"})
    
    # Logs de execução
    execution_log: list = Field(default_factory=list, sa_column_kwargs={"type_": "JSON"})
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TIMESTAMPS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    # Deadline calculado
    deadline: Optional[datetime] = None


class ExecutionLoopCreate(SQLModel):
    """Payload para criar loop de execução"""
    project_id: int
    intent_id: int
    max_time_minutes: int = 30
    max_actions: int = 50
    max_cost_usd: float = 5.0
    max_iterations_before_pause: int = 10


class ExecutionLoopRead(SQLModel):
    """Resposta de leitura de loop"""
    id: int
    project_id: int
    intent_id: int
    status: LoopStatus
    max_time_minutes: int
    max_actions: int
    max_cost_usd: float
    max_iterations_before_pause: int
    elapsed_seconds: int
    actions_executed: int
    cost_accumulated_usd: float
    iterations_executed: int
    pause_count: int
    last_pause_reason: Optional[PauseReason]
    last_pause_at: Optional[datetime]
    last_pause_message: Optional[str]
    progress_percentage: int
    current_phase: Optional[str]
    last_action: Optional[str]
    last_action_at: Optional[datetime]
    next_action: Optional[str]
    result: Optional[str]
    artifacts: dict
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    deadline: Optional[datetime]


class ExecutionLoopUpdate(SQLModel):
    """Payload para atualizar loop"""
    status: Optional[LoopStatus] = None
    elapsed_seconds: Optional[int] = None
    actions_executed: Optional[int] = None
    cost_accumulated_usd: Optional[float] = None
    iterations_executed: Optional[int] = None
    progress_percentage: Optional[int] = None
    current_phase: Optional[str] = None
    last_action: Optional[str] = None
    next_action: Optional[str] = None


class LoopAction(SQLModel, table=True):
    """
    Ação executada no loop
    
    Registra cada ação para auditoria e controle.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    
    loop_id: int = Field(foreign_key="executionloop.id", index=True)
    
    # Tipo de ação
    action_type: str  # code_generation, test_execution, deployment, etc.
    
    # Descrição da ação
    description: str
    
    # Agente que executou
    agent_name: Optional[str] = None
    
    # Resultado
    success: bool = Field(default=False)
    result: Optional[str] = None
    error: Optional[str] = None
    
    # Custo da ação
    cost_usd: float = Field(default=0.0)
    
    # Tempo de execução (em segundos)
    duration_seconds: int = Field(default=0)
    
    # Timestamp
    executed_at: datetime = Field(default_factory=datetime.utcnow)


class LoopPause(SQLModel, table=True):
    """
    Pausa do loop
    
    Registra cada pausa para auditoria.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    
    loop_id: int = Field(foreign_key="executionloop.id", index=True)
    
    # Motivo da pausa
    reason: PauseReason
    
    # Mensagem
    message: str
    
    # Quem pausou (system ou user)
    paused_by: str
    
    # Ação necessária
    action_required: Optional[str] = None
    
    # Timestamp
    paused_at: datetime = Field(default_factory=datetime.utcnow)
    resumed_at: Optional[datetime] = None
    
    # Resposta do usuário
    user_response: Optional[str] = None
