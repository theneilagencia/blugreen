"""
API para Intenções (CAMADA 2)

Endpoints para gerenciar intenções de projeto.

Princípios:
- A IA NÃO pode agir sem intenção validada
- Intenção congelada é IMUTÁVEL
- Violações são registradas e bloqueadas
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models.guided_session import GuidedSession
from app.models.project_intent import (
    IntentViolation,
    ProjectIntent,
    ProjectIntentCreate,
    ProjectIntentRead,
    ProjectIntentValidate,
)
from app.services.intent_capture import IntentCaptureService

router = APIRouter(prefix="/intent", tags=["intent"])


@router.post("/from-guided/{session_id}", response_model=ProjectIntentRead)
def create_intent_from_guided(
    session_id: int,
    session: Session = Depends(get_session)
):
    """
    Cria uma intenção a partir de uma sessão guiada.
    
    Extrai os campos obrigatórios das respostas do usuário.
    """
    
    # Buscar sessão guiada
    guided_session = session.get(GuidedSession, session_id)
    if not guided_session:
        raise HTTPException(status_code=404, detail="Sessão guiada não encontrada")
    
    # Verificar se já existe intenção para esta sessão
    existing = session.exec(
        select(ProjectIntent).where(ProjectIntent.guided_session_id == session_id)
    ).first()
    
    if existing:
        return existing
    
    # Criar intenção
    intent = IntentCaptureService.create_intent_from_guided_session(
        session,
        guided_session
    )
    
    return intent


@router.post("/", response_model=ProjectIntentRead)
def create_intent(
    payload: ProjectIntentCreate,
    session: Session = Depends(get_session)
):
    """
    Cria uma intenção manualmente.
    
    Útil para casos onde não há sessão guiada.
    """
    
    intent = ProjectIntent(**payload.model_dump())
    
    session.add(intent)
    session.commit()
    session.refresh(intent)
    
    return intent


@router.post("/{intent_id}/validate", response_model=ProjectIntentRead)
def validate_intent(
    intent_id: int,
    payload: ProjectIntentValidate,
    session: Session = Depends(get_session)
):
    """
    Valida uma intenção.
    
    Verifica se todos os campos obrigatórios estão preenchidos.
    """
    
    intent = session.get(ProjectIntent, intent_id)
    if not intent:
        raise HTTPException(status_code=404, detail="Intenção não encontrada")
    
    try:
        intent = IntentCaptureService.validate_intent(
            session,
            intent,
            payload.validated_by
        )
        return intent
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{intent_id}/freeze", response_model=ProjectIntentRead)
def freeze_intent(
    intent_id: int,
    session: Session = Depends(get_session)
):
    """
    Congela uma intenção, tornando-a IMUTÁVEL.
    
    Após congelada, a intenção não pode mais ser alterada.
    Qualquer tentativa de violação será registrada.
    
    REGRA: Só é possível congelar intenções validadas.
    """
    
    intent = session.get(ProjectIntent, intent_id)
    if not intent:
        raise HTTPException(status_code=404, detail="Intenção não encontrada")
    
    try:
        intent = IntentCaptureService.freeze_intent(session, intent)
        return intent
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{intent_id}/check-action")
def check_action(
    intent_id: int,
    action_description: str,
    attempted_by: str,
    session: Session = Depends(get_session)
):
    """
    Verifica se uma ação viola o contrato de intenção.
    
    Retorna se a ação é permitida e o motivo caso não seja.
    
    Este endpoint deve ser chamado ANTES de executar qualquer ação
    que possa violar a intenção.
    """
    
    intent = session.get(ProjectIntent, intent_id)
    if not intent:
        raise HTTPException(status_code=404, detail="Intenção não encontrada")
    
    is_allowed, violation_reason = IntentCaptureService.check_action_against_intent(
        session,
        intent,
        action_description,
        attempted_by
    )
    
    return {
        "is_allowed": is_allowed,
        "violation_reason": violation_reason,
        "intent_status": intent.status,
        "risk_level": intent.risk_level
    }


@router.get("/{intent_id}", response_model=ProjectIntentRead)
def get_intent(
    intent_id: int,
    session: Session = Depends(get_session)
):
    """
    Retorna os detalhes de uma intenção.
    """
    
    intent = session.get(ProjectIntent, intent_id)
    if not intent:
        raise HTTPException(status_code=404, detail="Intenção não encontrada")
    
    return intent


@router.get("/{intent_id}/violations", response_model=List[IntentViolation])
def get_violations(
    intent_id: int,
    session: Session = Depends(get_session)
):
    """
    Retorna todas as violações registradas para uma intenção.
    
    Útil para auditoria.
    """
    
    intent = session.get(ProjectIntent, intent_id)
    if not intent:
        raise HTTPException(status_code=404, detail="Intenção não encontrada")
    
    violations = session.exec(
        select(IntentViolation).where(IntentViolation.intent_id == intent_id)
    ).all()
    
    return violations


@router.get("/project/{project_id}", response_model=ProjectIntentRead)
def get_intent_by_project(
    project_id: int,
    session: Session = Depends(get_session)
):
    """
    Retorna a intenção de um projeto.
    """
    
    intent = session.exec(
        select(ProjectIntent).where(ProjectIntent.project_id == project_id)
    ).first()
    
    if not intent:
        raise HTTPException(status_code=404, detail="Intenção não encontrada para este projeto")
    
    return intent
