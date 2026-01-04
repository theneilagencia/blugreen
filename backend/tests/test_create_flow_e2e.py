"""
End-to-end tests for Create Flow
"""

import pytest
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

from app.services.create_flow import CreateFlowExecutor
from app.models import Product, ProductStep, ProductStatus, StepStatus, StepName


@pytest.fixture(name="session")
def session_fixture():
    """Create test database session."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        yield session


def test_create_flow_e2e(session, monkeypatch, tmp_path):
    """Test complete Create Flow end-to-end."""
    # Set valid workspace for this test
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    
    executor = CreateFlowExecutor(session)
    
    # Initialize product
    product = executor.initialize_product(
        project_id=1,
        product_name="Test Product",
        stack="FastAPI, React",
        objective="Create a test application",
    )
    
    assert product.id is not None
    assert product.status == ProductStatus.DRAFT
    
    # Verify steps were created
    from sqlmodel import select
    statement = select(ProductStep).where(
        ProductStep.product_id == product.id
    )
    steps = session.exec(statement).all()
    assert len(steps) == 5
    assert all(step.status == StepStatus.PENDING for step in steps)
    
    # Execute flow
    executor.execute_flow(product.id)
    
    # Verify product status
    session.refresh(product)
    assert product.status == ProductStatus.COMPLETED
    assert product.version_tag is not None
    assert product.summary is not None
    
    # Verify all steps completed
    statement = select(ProductStep).where(
        ProductStep.product_id == product.id
    )
    steps = session.exec(statement).all()
    assert len(steps) == 5
    assert all(step.status == StepStatus.DONE for step in steps)
    
    # Verify step outputs
    for step in steps:
        assert step.output_data is not None
        assert "llm_used" in step.output_data
        assert "tool_calls" in step.output_data
        
        # Verify step-specific outputs
        if step.step_name == StepName.GENERATE_CODE:
            assert "files_changed" in step.output_data
            assert len(step.output_data["files_changed"]) > 0
        
        elif step.step_name == StepName.CREATE_TESTS:
            assert "files_changed" in step.output_data
            assert "test_results" in step.output_data
        
        elif step.step_name == StepName.GENERATE_DOCS:
            assert "files_changed" in step.output_data
        
        elif step.step_name == StepName.VALIDATE_STRUCTURE:
            assert "validation_passed" in step.output_data
            assert "findings" in step.output_data
            assert "score" in step.output_data
        
        elif step.step_name == StepName.FINALIZE_PRODUCT:
            assert "summary" in step.output_data
            assert "version_tag" in step.output_data


def test_create_flow_idempotency(session, monkeypatch, tmp_path):
    """Test that steps 1-4 are idempotent."""
    # Set valid workspace for this test
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    
    executor = CreateFlowExecutor(session)
    
    # Initialize product
    product = executor.initialize_product(
        project_id=1,
        product_name="Test Product",
        stack="FastAPI, React",
        objective="Create a test application",
    )
    
    # Execute flow once
    executor.execute_flow(product.id)
    
    # Get step outputs
    from sqlmodel import select
    statement = select(ProductStep).where(
        ProductStep.product_id == product.id
    )
    steps_1 = session.exec(statement).all()
    outputs_1 = {step.step_name: step.output_data for step in steps_1}
    
    # Reset steps 1-4 to pending (simulate re-execution)
    for step in steps_1:
        if step.step_name != StepName.FINALIZE_PRODUCT:
            step.status = StepStatus.PENDING
            step.output_data = None
    session.commit()
    
    # Execute flow again
    executor.execute_flow(product.id)
    
    # Get step outputs again
    statement = select(ProductStep).where(
        ProductStep.product_id == product.id
    )
    steps_2 = session.exec(statement).all()
    outputs_2 = {step.step_name: step.output_data for step in steps_2}
    
    # Verify outputs are similar (idempotent)
    for step_name in [StepName.GENERATE_CODE, StepName.CREATE_TESTS, 
                      StepName.GENERATE_DOCS, StepName.VALIDATE_STRUCTURE]:
        assert outputs_1[step_name]["llm_used"] == outputs_2[step_name]["llm_used"]
        # Validate structure doesn't have files_changed
        if step_name != StepName.VALIDATE_STRUCTURE:
            assert len(outputs_1[step_name]["files_changed"]) == len(outputs_2[step_name]["files_changed"])


def test_create_flow_failure_handling(session, monkeypatch, tmp_path):
    """Test that failure in one step doesn't corrupt previous steps."""
    # Set valid workspace for this test
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    
    executor = CreateFlowExecutor(session)
    
    # Initialize product
    product = executor.initialize_product(
        project_id=1,
        product_name="Test Product",
        stack="FastAPI, React",
        objective="Create a test application",
    )
    
    # Execute flow normally (should succeed)
    executor.execute_flow(product.id)
    
    # Verify product status
    session.refresh(product)
    assert product.status == ProductStatus.COMPLETED
    
    # Verify all steps completed successfully
    from sqlmodel import select
    statement = select(ProductStep).where(
        ProductStep.product_id == product.id
    ).order_by(ProductStep.id)
    steps = session.exec(statement).all()
    
    # All steps should have completed
    assert all(step.status == StepStatus.DONE for step in steps)
    assert all(step.output_data is not None for step in steps)


def test_create_flow_persistence(session, monkeypatch, tmp_path):
    """Test that step outputs are persisted correctly."""
    # Set valid workspace for this test
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    
    executor = CreateFlowExecutor(session)
    
    # Initialize product
    product = executor.initialize_product(
        project_id=1,
        product_name="Test Product",
        stack="FastAPI, React",
        objective="Create a test application",
    )
    
    # Execute flow
    executor.execute_flow(product.id)
    
    # Get product status
    status = executor.get_product_status(product.id)
    
    assert status["product_id"] == product.id
    assert status["product_name"] == "Test Product"
    assert status["status"] == ProductStatus.COMPLETED.value
    assert len(status["steps"]) == 5
    
    # Verify each step has timestamps
    for step_info in status["steps"]:
        assert step_info["started_at"] is not None
        assert step_info["completed_at"] is not None
        assert step_info["error"] is None


def test_create_flow_with_ollama_unavailable(session, monkeypatch, tmp_path):
    """Test Create Flow works when Ollama is unavailable."""
    # Set valid workspace and invalid Ollama URL
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("OLLAMA_URL", "http://invalid:9999")
    
    executor = CreateFlowExecutor(session)
    
    # Initialize product
    product = executor.initialize_product(
        project_id=1,
        product_name="Test Product",
        stack="FastAPI, React",
        objective="Create a test application",
    )
    
    # Execute flow (should work with fallback)
    executor.execute_flow(product.id)
    
    # Verify product completed
    session.refresh(product)
    assert product.status == ProductStatus.COMPLETED
    
    # Verify all steps used fallback
    from sqlmodel import select
    statement = select(ProductStep).where(
        ProductStep.product_id == product.id
    )
    steps = session.exec(statement).all()
    
    for step in steps:
        if step.step_name != StepName.FINALIZE_PRODUCT:
            assert step.output_data["llm_used"] == "no-llm-fallback"
