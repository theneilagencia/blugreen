"""
Tests for Create Flow

Tests the step-based Create Flow implementation.
"""

import pytest
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

from app.models import (
    Product,
    ProductStatus,
    ProductStep,
    StepName,
    StepStatus,
    Project,
)
from app.services.create_flow import CreateFlowExecutor


@pytest.fixture(name="session")
def session_fixture():
    """Create a test database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="test_project")
def test_project_fixture(session: Session):
    """Create a test project."""
    project = Project(
        name="Test Project",
        description="Test project for Create Flow",
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def test_initialize_product(session: Session, test_project: Project):
    """Test product initialization."""
    executor = CreateFlowExecutor(session)
    
    product = executor.initialize_product(
        project_id=test_project.id,
        product_name="Test Product",
        stack="FastAPI, React",
        objective="Test objective",
    )
    
    assert product.id is not None
    assert product.name == "Test Product"
    assert product.stack == "FastAPI, React"
    assert product.objective == "Test objective"
    assert product.status == ProductStatus.DRAFT
    
    # Check that all steps were created
    steps = session.query(ProductStep).filter(
        ProductStep.product_id == product.id
    ).all()
    
    assert len(steps) == 5
    assert steps[0].step_name == StepName.GENERATE_CODE
    assert steps[1].step_name == StepName.CREATE_TESTS
    assert steps[2].step_name == StepName.GENERATE_DOCS
    assert steps[3].step_name == StepName.VALIDATE_STRUCTURE
    assert steps[4].step_name == StepName.FINALIZE_PRODUCT
    
    for step in steps:
        assert step.status == StepStatus.PENDING


def test_execute_step_generate_code(session: Session, test_project: Project):
    """Test generate_code step execution."""
    executor = CreateFlowExecutor(session)
    
    product = executor.initialize_product(
        project_id=test_project.id,
        product_name="Test Product",
        stack="FastAPI, React",
        objective="Test objective",
    )
    
    executor._execute_step(product.id, StepName.GENERATE_CODE)
    
    # Check step status
    step = session.query(ProductStep).filter(
        ProductStep.product_id == product.id,
        ProductStep.step_name == StepName.GENERATE_CODE,
    ).first()
    
    assert step.status == StepStatus.DONE
    assert step.started_at is not None
    assert step.completed_at is not None
    assert step.output_data is not None
    assert step.output_data["code_generated"] is True
    assert "backend_files" in step.output_data
    assert "frontend_files" in step.output_data


def test_execute_step_create_tests(session: Session, test_project: Project):
    """Test create_tests step execution."""
    executor = CreateFlowExecutor(session)
    
    product = executor.initialize_product(
        project_id=test_project.id,
        product_name="Test Product",
        stack="FastAPI, React",
        objective="Test objective",
    )
    
    # Execute generate_code first
    executor._execute_step(product.id, StepName.GENERATE_CODE)
    
    # Execute create_tests
    executor._execute_step(product.id, StepName.CREATE_TESTS)
    
    # Check step status
    step = session.query(ProductStep).filter(
        ProductStep.product_id == product.id,
        ProductStep.step_name == StepName.CREATE_TESTS,
    ).first()
    
    assert step.status == StepStatus.DONE
    assert step.started_at is not None
    assert step.completed_at is not None
    assert step.output_data is not None
    assert step.output_data["tests_created"] is True
    assert "test_files" in step.output_data


def test_execute_full_flow(session: Session, test_project: Project):
    """Test full Create Flow execution."""
    executor = CreateFlowExecutor(session)
    
    product = executor.initialize_product(
        project_id=test_project.id,
        product_name="Test Product",
        stack="FastAPI, React",
        objective="Test objective",
    )
    
    # Execute full flow
    executor.execute_flow(product.id)
    
    # Check product status
    session.refresh(product)
    assert product.status == ProductStatus.COMPLETED
    assert product.version_tag is not None
    assert product.summary is not None
    
    # Check all steps are done
    steps = session.query(ProductStep).filter(
        ProductStep.product_id == product.id
    ).all()
    
    for step in steps:
        assert step.status == StepStatus.DONE
        assert step.started_at is not None
        assert step.completed_at is not None


def test_get_product_status(session: Session, test_project: Project):
    """Test getting product status."""
    executor = CreateFlowExecutor(session)
    
    product = executor.initialize_product(
        project_id=test_project.id,
        product_name="Test Product",
        stack="FastAPI, React",
        objective="Test objective",
    )
    
    # Execute first step
    executor._execute_step(product.id, StepName.GENERATE_CODE)
    
    # Get status
    status = executor.get_product_status(product.id)
    
    assert status["product_id"] == product.id
    assert status["product_name"] == "Test Product"
    assert status["status"] == ProductStatus.DRAFT.value
    assert len(status["steps"]) == 5
    
    # Check first step is done
    assert status["steps"][0]["step_name"] == StepName.GENERATE_CODE.value
    assert status["steps"][0]["status"] == StepStatus.DONE.value
    assert status["steps"][0]["started_at"] is not None
    assert status["steps"][0]["completed_at"] is not None
    
    # Check other steps are pending
    for i in range(1, 5):
        assert status["steps"][i]["status"] == StepStatus.PENDING.value


def test_step_idempotency(session: Session, test_project: Project):
    """Test that steps are idempotent (can be re-executed)."""
    executor = CreateFlowExecutor(session)
    
    product = executor.initialize_product(
        project_id=test_project.id,
        product_name="Test Product",
        stack="FastAPI, React",
        objective="Test objective",
    )
    
    # Execute step twice
    executor._execute_step(product.id, StepName.GENERATE_CODE)
    executor._execute_step(product.id, StepName.GENERATE_CODE)
    
    # Check step was only executed once (idempotent)
    step = session.query(ProductStep).filter(
        ProductStep.product_id == product.id,
        ProductStep.step_name == StepName.GENERATE_CODE,
    ).first()
    
    assert step.status == StepStatus.DONE


def test_step_failure_handling(session: Session, test_project: Project):
    """Test step failure handling."""
    executor = CreateFlowExecutor(session)
    
    product = executor.initialize_product(
        project_id=test_project.id,
        product_name="Test Product",
        stack="FastAPI, React",
        objective="Test objective",
    )
    
    # Mock a failure by trying to execute create_tests without generate_code
    # This should fail because it depends on generate_code output
    try:
        executor._execute_step(product.id, StepName.CREATE_TESTS)
        assert False, "Expected ValueError"
    except ValueError:
        pass
    
    # Check step is marked as failed
    step = session.query(ProductStep).filter(
        ProductStep.product_id == product.id,
        ProductStep.step_name == StepName.CREATE_TESTS,
    ).first()
    
    assert step.status == StepStatus.FAILED
    assert step.error_message is not None
