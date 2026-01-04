"""
Serviço de Loop Autônomo Controlado (CAMADA 4)

O loop NÃO roda infinitamente. Tem limites e pausas obrigatórias.

Princípios:
- Limite de tempo, ações e custo
- Pausa obrigatória a cada X iterações
- Usuário pode cancelar a qualquer momento
- Modo seguro: não executar sem confirmação
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlmodel import Session, select

from app.models.execution_loop import (
    ExecutionLoop,
    LoopAction,
    LoopPause,
    LoopStatus,
    PauseReason,
)
from app.models.project_intent import ProjectIntent
from app.services.intent_capture import IntentCaptureService


class AutonomousLoopService:
    """Serviço para loop autônomo controlado"""
    
    @staticmethod
    def create_loop(
        session: Session,
        project_id: int,
        intent_id: int,
        max_time_minutes: int = 30,
        max_actions: int = 50,
        max_cost_usd: float = 5.0,
        max_iterations_before_pause: int = 10
    ) -> ExecutionLoop:
        """
        Cria um novo loop de execução.
        
        O loop NÃO inicia automaticamente. Requer confirmação explícita.
        """
        
        # Verificar se intenção existe e está congelada
        intent = session.get(ProjectIntent, intent_id)
        if not intent:
            raise ValueError("Intenção não encontrada")
        
        if intent.status != "frozen":
            raise ValueError("Intenção deve estar congelada antes de criar loop")
        
        # Criar loop
        loop = ExecutionLoop(
            project_id=project_id,
            intent_id=intent_id,
            max_time_minutes=max_time_minutes,
            max_actions=max_actions,
            max_cost_usd=max_cost_usd,
            max_iterations_before_pause=max_iterations_before_pause,
            status=LoopStatus.PENDING
        )
        
        session.add(loop)
        session.commit()
        session.refresh(loop)
        
        return loop
    
    @staticmethod
    def start_loop(
        session: Session,
        loop: ExecutionLoop
    ) -> ExecutionLoop:
        """
        Inicia o loop de execução.
        
        Calcula o deadline baseado no limite de tempo.
        """
        
        if loop.status != LoopStatus.PENDING:
            raise ValueError(f"Loop deve estar PENDING para iniciar (status atual: {loop.status})")
        
        # Iniciar
        loop.status = LoopStatus.RUNNING
        loop.started_at = datetime.utcnow()
        loop.deadline = loop.started_at + timedelta(minutes=loop.max_time_minutes)
        
        # Log
        loop.execution_log.append({
            "timestamp": loop.started_at.isoformat(),
            "event": "loop_started",
            "message": f"Loop iniciado com limites: {loop.max_time_minutes}min, {loop.max_actions} ações, ${loop.max_cost_usd}"
        })
        
        session.add(loop)
        session.commit()
        session.refresh(loop)
        
        return loop
    
    @staticmethod
    def check_limits(
        session: Session,
        loop: ExecutionLoop
    ) -> Tuple[bool, Optional[PauseReason], Optional[str]]:
        """
        Verifica se algum limite foi atingido.
        
        Retorna (should_pause, reason, message)
        """
        
        # 1. Verificar limite de tempo
        if loop.started_at and loop.deadline:
            if datetime.utcnow() >= loop.deadline:
                return True, PauseReason.TIME_LIMIT, f"Limite de tempo atingido ({loop.max_time_minutes} minutos)"
        
        # 2. Verificar limite de ações
        if loop.actions_executed >= loop.max_actions:
            return True, PauseReason.ACTION_LIMIT, f"Limite de ações atingido ({loop.max_actions} ações)"
        
        # 3. Verificar limite de custo
        if loop.cost_accumulated_usd >= loop.max_cost_usd:
            return True, PauseReason.COST_LIMIT, f"Limite de custo atingido (${loop.max_cost_usd})"
        
        # 4. Verificar limite de iterações antes de pausa
        if loop.iterations_executed > 0 and loop.iterations_executed % loop.max_iterations_before_pause == 0:
            return True, PauseReason.ITERATION_LIMIT, f"Pausa obrigatória após {loop.max_iterations_before_pause} iterações"
        
        return False, None, None
    
    @staticmethod
    def pause_loop(
        session: Session,
        loop: ExecutionLoop,
        reason: PauseReason,
        message: str,
        paused_by: str = "system",
        action_required: Optional[str] = None
    ) -> ExecutionLoop:
        """
        Pausa o loop de execução.
        
        Registra a pausa para auditoria.
        """
        
        if loop.status != LoopStatus.RUNNING:
            raise ValueError(f"Loop deve estar RUNNING para pausar (status atual: {loop.status})")
        
        # Pausar
        loop.status = LoopStatus.PAUSED
        loop.pause_count += 1
        loop.last_pause_reason = reason
        loop.last_pause_at = datetime.utcnow()
        loop.last_pause_message = message
        
        # Registrar pausa
        pause = LoopPause(
            loop_id=loop.id,
            reason=reason,
            message=message,
            paused_by=paused_by,
            action_required=action_required
        )
        session.add(pause)
        
        # Log
        loop.execution_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event": "loop_paused",
            "reason": reason,
            "message": message,
            "paused_by": paused_by
        })
        
        session.add(loop)
        session.commit()
        session.refresh(loop)
        
        return loop
    
    @staticmethod
    def resume_loop(
        session: Session,
        loop: ExecutionLoop,
        user_response: Optional[str] = None
    ) -> ExecutionLoop:
        """
        Resume o loop de execução após pausa.
        """
        
        if loop.status != LoopStatus.PAUSED:
            raise ValueError(f"Loop deve estar PAUSED para resumir (status atual: {loop.status})")
        
        # Atualizar última pausa com resposta do usuário
        if user_response and loop.last_pause_at:
            last_pause = session.exec(
                select(LoopPause)
                .where(LoopPause.loop_id == loop.id)
                .where(LoopPause.paused_at == loop.last_pause_at)
            ).first()
            
            if last_pause:
                last_pause.resumed_at = datetime.utcnow()
                last_pause.user_response = user_response
                session.add(last_pause)
        
        # Resumir
        loop.status = LoopStatus.RUNNING
        
        # Log
        loop.execution_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event": "loop_resumed",
            "user_response": user_response
        })
        
        session.add(loop)
        session.commit()
        session.refresh(loop)
        
        return loop
    
    @staticmethod
    def record_action(
        session: Session,
        loop: ExecutionLoop,
        action_type: str,
        description: str,
        agent_name: Optional[str] = None,
        success: bool = False,
        result: Optional[str] = None,
        error: Optional[str] = None,
        cost_usd: float = 0.0,
        duration_seconds: int = 0
    ) -> LoopAction:
        """
        Registra uma ação executada no loop.
        
        Atualiza contadores e verifica limites.
        """
        
        # Registrar ação
        action = LoopAction(
            loop_id=loop.id,
            action_type=action_type,
            description=description,
            agent_name=agent_name,
            success=success,
            result=result,
            error=error,
            cost_usd=cost_usd,
            duration_seconds=duration_seconds
        )
        session.add(action)
        
        # Atualizar contadores
        loop.actions_executed += 1
        loop.cost_accumulated_usd += cost_usd
        loop.elapsed_seconds += duration_seconds
        loop.last_action = description
        loop.last_action_at = datetime.utcnow()
        
        # Log
        loop.execution_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event": "action_executed",
            "action_type": action_type,
            "description": description,
            "success": success,
            "cost_usd": cost_usd
        })
        
        session.add(loop)
        session.commit()
        session.refresh(loop)
        session.refresh(action)
        
        return action
    
    @staticmethod
    def check_action_against_intent(
        session: Session,
        loop: ExecutionLoop,
        action_description: str,
        attempted_by: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Verifica se uma ação viola a intenção do projeto.
        
        Integra com CAMADA 2 (Captura de Intenção).
        """
        
        intent = session.get(ProjectIntent, loop.intent_id)
        if not intent:
            return True, None  # Sem intenção, permitir
        
        return IntentCaptureService.check_action_against_intent(
            session,
            intent,
            action_description,
            attempted_by
        )
    
    @staticmethod
    def complete_loop(
        session: Session,
        loop: ExecutionLoop,
        result: str,
        artifacts: dict = None
    ) -> ExecutionLoop:
        """
        Completa o loop de execução.
        """
        
        if loop.status not in [LoopStatus.RUNNING, LoopStatus.PAUSED]:
            raise ValueError(f"Loop deve estar RUNNING ou PAUSED para completar (status atual: {loop.status})")
        
        # Completar
        loop.status = LoopStatus.COMPLETED
        loop.completed_at = datetime.utcnow()
        loop.result = result
        loop.progress_percentage = 100
        
        if artifacts:
            loop.artifacts = artifacts
        
        # Log
        loop.execution_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event": "loop_completed",
            "result": result
        })
        
        session.add(loop)
        session.commit()
        session.refresh(loop)
        
        return loop
    
    @staticmethod
    def cancel_loop(
        session: Session,
        loop: ExecutionLoop,
        reason: str
    ) -> ExecutionLoop:
        """
        Cancela o loop de execução.
        """
        
        if loop.status in [LoopStatus.COMPLETED, LoopStatus.CANCELLED]:
            raise ValueError(f"Loop já está finalizado (status: {loop.status})")
        
        # Cancelar
        loop.status = LoopStatus.CANCELLED
        loop.cancelled_at = datetime.utcnow()
        loop.result = f"Cancelado: {reason}"
        
        # Log
        loop.execution_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event": "loop_cancelled",
            "reason": reason
        })
        
        session.add(loop)
        session.commit()
        session.refresh(loop)
        
        return loop
