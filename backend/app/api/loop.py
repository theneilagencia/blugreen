"""
API para Loop Autônomo Controlado (CAMADA 4)

Endpoints para gerenciar loops de execução.

Princípios:
- Loop NÃO inicia automaticamente
- Requer confirmação explícita
- Tem limites e pausas obrigatórias
- Usuário pode cancelar a qualquer momento
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models.execution_loop import (
    ExecutionLoop,
    ExecutionLoopCreate,
    ExecutionLoopRead,
    ExecutionLoopUpdate,
    LoopAction,
    LoopPause,
    LoopStatus,
    PauseReason,
)
from app.services.autonomous_loop import AutonomousLoopService

router = APIRouter(prefix="/loop", tags=["loop"])


@router.post("/", response_model=ExecutionLoopRead)
def create_loop(
    payload: ExecutionLoopCreate,
    session: Session = Depends(get_session)
):
    """
    Cria um novo loop de execução.
    
    O loop NÃO inicia automaticamente. Requer confirmação explícita via /start.
    
    MODO SEGURO: Não executar sem confirmação.
    """
    
    try:
        loop = AutonomousLoopService.create_loop(
            session,
            project_id=payload.project_id,
            intent_id=payload.intent_id,
            max_time_minutes=payload.max_time_minutes,
            max_actions=payload.max_actions,
            max_cost_usd=payload.max_cost_usd,
            max_iterations_before_pause=payload.max_iterations_before_pause
        )
        return loop
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{loop_id}/start", response_model=ExecutionLoopRead)
def start_loop(
    loop_id: int,
    session: Session = Depends(get_session)
):
    """
    Inicia o loop de execução.
    
    Calcula o deadline baseado no limite de tempo.
    
    CONFIRMAÇÃO EXPLÍCITA: Este endpoint só deve ser chamado após
    o usuário confirmar explicitamente que quer iniciar a execução.
    """
    
    loop = session.get(ExecutionLoop, loop_id)
    if not loop:
        raise HTTPException(status_code=404, detail="Loop não encontrado")
    
    try:
        loop = AutonomousLoopService.start_loop(session, loop)
        return loop
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{loop_id}/pause", response_model=ExecutionLoopRead)
def pause_loop(
    loop_id: int,
    reason: PauseReason,
    message: str,
    paused_by: str = "user",
    action_required: str = None,
    session: Session = Depends(get_session)
):
    """
    Pausa o loop de execução.
    
    Pode ser pausado pelo sistema (limites) ou pelo usuário.
    """
    
    loop = session.get(ExecutionLoop, loop_id)
    if not loop:
        raise HTTPException(status_code=404, detail="Loop não encontrado")
    
    try:
        loop = AutonomousLoopService.pause_loop(
            session,
            loop,
            reason,
            message,
            paused_by,
            action_required
        )
        return loop
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{loop_id}/resume", response_model=ExecutionLoopRead)
def resume_loop(
    loop_id: int,
    user_response: str = None,
    session: Session = Depends(get_session)
):
    """
    Resume o loop de execução após pausa.
    
    Requer resposta do usuário se a pausa foi por motivo que exige ação.
    """
    
    loop = session.get(ExecutionLoop, loop_id)
    if not loop:
        raise HTTPException(status_code=404, detail="Loop não encontrado")
    
    try:
        loop = AutonomousLoopService.resume_loop(session, loop, user_response)
        return loop
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{loop_id}/action", response_model=LoopAction)
def record_action(
    loop_id: int,
    action_type: str,
    description: str,
    agent_name: str = None,
    success: bool = False,
    result: str = None,
    error: str = None,
    cost_usd: float = 0.0,
    duration_seconds: int = 0,
    session: Session = Depends(get_session)
):
    """
    Registra uma ação executada no loop.
    
    Atualiza contadores e verifica limites.
    
    Este endpoint deve ser chamado por cada agente após executar uma ação.
    """
    
    loop = session.get(ExecutionLoop, loop_id)
    if not loop:
        raise HTTPException(status_code=404, detail="Loop não encontrado")
    
    action = AutonomousLoopService.record_action(
        session,
        loop,
        action_type,
        description,
        agent_name,
        success,
        result,
        error,
        cost_usd,
        duration_seconds
    )
    
    return action


@router.post("/{loop_id}/check-action")
def check_action(
    loop_id: int,
    action_description: str,
    attempted_by: str,
    session: Session = Depends(get_session)
):
    """
    Verifica se uma ação viola a intenção do projeto.
    
    Integra com CAMADA 2 (Captura de Intenção).
    
    Este endpoint deve ser chamado ANTES de executar qualquer ação.
    """
    
    loop = session.get(ExecutionLoop, loop_id)
    if not loop:
        raise HTTPException(status_code=404, detail="Loop não encontrado")
    
    is_allowed, violation_reason = AutonomousLoopService.check_action_against_intent(
        session,
        loop,
        action_description,
        attempted_by
    )
    
    return {
        "is_allowed": is_allowed,
        "violation_reason": violation_reason
    }


@router.get("/{loop_id}/check-limits")
def check_limits(
    loop_id: int,
    session: Session = Depends(get_session)
):
    """
    Verifica se algum limite foi atingido.
    
    Retorna se o loop deve ser pausado e o motivo.
    
    Este endpoint deve ser chamado periodicamente durante a execução.
    """
    
    loop = session.get(ExecutionLoop, loop_id)
    if not loop:
        raise HTTPException(status_code=404, detail="Loop não encontrado")
    
    should_pause, reason, message = AutonomousLoopService.check_limits(session, loop)
    
    return {
        "should_pause": should_pause,
        "reason": reason,
        "message": message,
        "current_status": {
            "elapsed_seconds": loop.elapsed_seconds,
            "actions_executed": loop.actions_executed,
            "cost_accumulated_usd": loop.cost_accumulated_usd,
            "iterations_executed": loop.iterations_executed
        },
        "limits": {
            "max_time_minutes": loop.max_time_minutes,
            "max_actions": loop.max_actions,
            "max_cost_usd": loop.max_cost_usd,
            "max_iterations_before_pause": loop.max_iterations_before_pause
        }
    }


@router.post("/{loop_id}/complete", response_model=ExecutionLoopRead)
def complete_loop(
    loop_id: int,
    result: str,
    artifacts: dict = None,
    session: Session = Depends(get_session)
):
    """
    Completa o loop de execução.
    
    Marca o loop como concluído e registra o resultado.
    """
    
    loop = session.get(ExecutionLoop, loop_id)
    if not loop:
        raise HTTPException(status_code=404, detail="Loop não encontrado")
    
    try:
        loop = AutonomousLoopService.complete_loop(session, loop, result, artifacts)
        return loop
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{loop_id}/cancel", response_model=ExecutionLoopRead)
def cancel_loop(
    loop_id: int,
    reason: str,
    session: Session = Depends(get_session)
):
    """
    Cancela o loop de execução.
    
    Pode ser cancelado pelo usuário a qualquer momento.
    """
    
    loop = session.get(ExecutionLoop, loop_id)
    if not loop:
        raise HTTPException(status_code=404, detail="Loop não encontrado")
    
    try:
        loop = AutonomousLoopService.cancel_loop(session, loop, reason)
        return loop
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{loop_id}", response_model=ExecutionLoopRead)
def get_loop(
    loop_id: int,
    session: Session = Depends(get_session)
):
    """
    Retorna os detalhes de um loop de execução.
    """
    
    loop = session.get(ExecutionLoop, loop_id)
    if not loop:
        raise HTTPException(status_code=404, detail="Loop não encontrado")
    
    return loop


@router.get("/{loop_id}/actions", response_model=List[LoopAction])
def get_actions(
    loop_id: int,
    session: Session = Depends(get_session)
):
    """
    Retorna todas as ações executadas no loop.
    
    Útil para auditoria e visualização de progresso.
    """
    
    loop = session.get(ExecutionLoop, loop_id)
    if not loop:
        raise HTTPException(status_code=404, detail="Loop não encontrado")
    
    actions = session.exec(
        select(LoopAction).where(LoopAction.loop_id == loop_id)
    ).all()
    
    return actions


@router.get("/{loop_id}/pauses", response_model=List[LoopPause])
def get_pauses(
    loop_id: int,
    session: Session = Depends(get_session)
):
    """
    Retorna todas as pausas do loop.
    
    Útil para auditoria.
    """
    
    loop = session.get(ExecutionLoop, loop_id)
    if not loop:
        raise HTTPException(status_code=404, detail="Loop não encontrado")
    
    pauses = session.exec(
        select(LoopPause).where(LoopPause.loop_id == loop_id)
    ).all()
    
    return pauses


@router.get("/project/{project_id}", response_model=List[ExecutionLoopRead])
def get_loops_by_project(
    project_id: int,
    session: Session = Depends(get_session)
):
    """
    Retorna todos os loops de um projeto.
    """
    
    loops = session.exec(
        select(ExecutionLoop).where(ExecutionLoop.project_id == project_id)
    ).all()
    
    return loops
