"""
API para Modo Guiado (CAMADA 1)

Endpoints para o modo guiado para leigos.

Princípios:
- Linguagem 100% humana
- Sem termos técnicos
- Máximo 3 perguntas por etapa
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models.guided_session import (
    GuidedIntent,
    GuidedSession,
    GuidedSessionCreate,
    GuidedSessionRead,
    GuidedSessionStatus,
    GuidedSessionUpdate,
    GuidedStep,
)
from app.services.guided_mode import GuidedModeService

router = APIRouter(prefix="/guided", tags=["guided"])


@router.post("/start", response_model=GuidedSessionRead)
def start_guided_session(
    payload: GuidedSessionCreate,
    session: Session = Depends(get_session)
):
    """
    Inicia uma nova sessão no modo guiado.
    
    O usuário escolhe uma intenção:
    - "criar" - Quero criar um produto
    - "melhorar" - Quero melhorar um produto existente
    - "entender" - Quero entender um repositório
    """
    
    # Criar sessão
    guided_session = GuidedSession(
        intent=payload.intent,
        status=GuidedSessionStatus.COLLECTING
    )
    
    session.add(guided_session)
    session.commit()
    session.refresh(guided_session)
    
    return guided_session


@router.get("/{session_id}/steps", response_model=List[GuidedStep])
def get_guided_steps(
    session_id: int,
    session: Session = Depends(get_session)
):
    """
    Retorna as etapas do modo guiado para a sessão.
    
    Cada etapa contém no máximo 3 perguntas em linguagem humana.
    """
    
    # Buscar sessão
    guided_session = session.get(GuidedSession, session_id)
    if not guided_session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    # Retornar etapas baseadas na intenção
    steps = GuidedModeService.get_steps_for_intent(guided_session.intent)
    
    return steps


@router.patch("/{session_id}", response_model=GuidedSessionRead)
def update_guided_session(
    session_id: int,
    payload: GuidedSessionUpdate,
    session: Session = Depends(get_session)
):
    """
    Atualiza a sessão guiada com as respostas do usuário.
    
    O sistema infere detalhes técnicos internamente.
    """
    
    # Buscar sessão
    guided_session = session.get(GuidedSession, session_id)
    if not guided_session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    # Atualizar respostas
    if payload.user_responses:
        guided_session.user_responses = payload.user_responses
        
        # Inferir detalhes técnicos
        inferences = GuidedModeService.infer_technical_details(guided_session)
        guided_session.system_inferences = inferences
    
    # Atualizar status
    if payload.status:
        guided_session.status = payload.status
        
        if payload.status == GuidedSessionStatus.COMPLETED:
            guided_session.completed_at = datetime.utcnow()
    
    guided_session.updated_at = datetime.utcnow()
    
    session.add(guided_session)
    session.commit()
    session.refresh(guided_session)
    
    return guided_session


@router.get("/{session_id}/summary")
def get_guided_summary(
    session_id: int,
    session: Session = Depends(get_session)
):
    """
    Retorna um resumo em linguagem humana do que o sistema vai fazer.
    
    Sem termos técnicos.
    """
    
    # Buscar sessão
    guided_session = session.get(GuidedSession, session_id)
    if not guided_session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    # Gerar resumo
    summary = GuidedModeService.generate_human_summary(guided_session)
    
    return {
        "session_id": session_id,
        "intent": guided_session.intent,
        "summary": summary,
        "ready_to_execute": len(guided_session.user_responses) > 0
    }


@router.get("/{session_id}", response_model=GuidedSessionRead)
def get_guided_session(
    session_id: int,
    session: Session = Depends(get_session)
):
    """
    Retorna os detalhes de uma sessão guiada.
    """
    
    guided_session = session.get(GuidedSession, session_id)
    if not guided_session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    return guided_session


@router.delete("/{session_id}")
def cancel_guided_session(
    session_id: int,
    session: Session = Depends(get_session)
):
    """
    Cancela uma sessão guiada.
    """
    
    guided_session = session.get(GuidedSession, session_id)
    if not guided_session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    guided_session.status = GuidedSessionStatus.CANCELLED
    guided_session.updated_at = datetime.utcnow()
    
    session.add(guided_session)
    session.commit()
    
    return {"status": "cancelled"}
