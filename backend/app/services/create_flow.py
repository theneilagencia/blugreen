"""
Create Flow Executor

Implements the step-based Create Flow for autonomous product creation.
Follows the contract defined in docs/contracts/create_flow_step_based.md
"""

from datetime import datetime
from typing import Dict, Any, Optional
from sqlmodel import Session, select

from app.models import (
    Product,
    ProductStatus,
    ProductStep,
    StepName,
    StepStatus,
)


class CreateFlowExecutor:
    """
    Executes the Create Flow steps sequentially.
    
    Steps (in order):
    1. generate_code
    2. create_tests
    3. generate_docs
    4. validate_structure
    5. finalize_product
    """
    
    # Define step order
    STEP_ORDER = [
        StepName.GENERATE_CODE,
        StepName.CREATE_TESTS,
        StepName.GENERATE_DOCS,
        StepName.VALIDATE_STRUCTURE,
        StepName.FINALIZE_PRODUCT,
    ]
    
    def __init__(self, session: Session):
        self.session = session
    
    def initialize_product(
        self,
        project_id: int,
        product_name: str,
        stack: str,
        objective: str,
    ) -> Product:
        """
        Initialize a new product and create all step records.
        
        Args:
            project_id: ID of the project
            product_name: Name of the product
            stack: Technology stack
            objective: Product objective
            
        Returns:
            Created Product instance
        """
        # Create product
        product = Product(
            project_id=project_id,
            name=product_name,
            stack=stack,
            objective=objective,
            status=ProductStatus.DRAFT,
        )
        self.session.add(product)
        self.session.commit()
        self.session.refresh(product)
        
        # Create step records
        for step_name in self.STEP_ORDER:
            step = ProductStep(
                product_id=product.id,
                step_name=step_name,
                status=StepStatus.PENDING,
            )
            self.session.add(step)
        
        self.session.commit()
        
        return product
    
    def execute_flow(self, product_id: int) -> None:
        """
        Execute the Create Flow for a product.
        
        Args:
            product_id: ID of the product
        """
        # Update product status to running
        product = self.session.get(Product, product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")
        
        product.status = ProductStatus.RUNNING
        product.updated_at = datetime.utcnow()
        self.session.add(product)
        self.session.commit()
        
        # Execute steps in order
        for step_name in self.STEP_ORDER:
            try:
                self._execute_step(product_id, step_name)
            except Exception as e:
                # Mark product as failed
                product.status = ProductStatus.FAILED
                product.updated_at = datetime.utcnow()
                self.session.add(product)
                self.session.commit()
                raise
        
        # Mark product as completed
        product.status = ProductStatus.COMPLETED
        product.updated_at = datetime.utcnow()
        self.session.add(product)
        self.session.commit()
    
    def _execute_step(self, product_id: int, step_name: StepName) -> None:
        """
        Execute a single step.
        
        Args:
            product_id: ID of the product
            step_name: Name of the step to execute
        """
        # Get step record
        statement = select(ProductStep).where(
            ProductStep.product_id == product_id,
            ProductStep.step_name == step_name,
        )
        step = self.session.exec(statement).first()
        
        if not step:
            raise ValueError(f"Step {step_name} not found for product {product_id}")
        
        # Skip if already done
        if step.status == StepStatus.DONE:
            return
        
        # Mark as running
        step.status = StepStatus.RUNNING
        step.started_at = datetime.utcnow()
        self.session.add(step)
        self.session.commit()
        
        try:
            # Execute step logic
            output_data = self._execute_step_logic(product_id, step_name, step.input_data)
            
            # Mark as done
            step.status = StepStatus.DONE
            step.completed_at = datetime.utcnow()
            step.output_data = output_data
            step.error_message = None
            
        except Exception as e:
            # Mark as failed
            step.status = StepStatus.FAILED
            step.completed_at = datetime.utcnow()
            step.error_message = str(e)
            raise
        
        finally:
            self.session.add(step)
            self.session.commit()
    
    def _execute_step_logic(
        self,
        product_id: int,
        step_name: StepName,
        input_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Execute the actual logic for a step.
        
        This is a placeholder that will be replaced with actual agent calls.
        
        Args:
            product_id: ID of the product
            step_name: Name of the step
            input_data: Input data for the step
            
        Returns:
            Output data from the step
        """
        # Get product
        product = self.session.get(Product, product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")
        
        # Execute step-specific logic
        if step_name == StepName.GENERATE_CODE:
            return self._step_generate_code(product, input_data)
        elif step_name == StepName.CREATE_TESTS:
            return self._step_create_tests(product, input_data)
        elif step_name == StepName.GENERATE_DOCS:
            return self._step_generate_docs(product, input_data)
        elif step_name == StepName.VALIDATE_STRUCTURE:
            return self._step_validate_structure(product, input_data)
        elif step_name == StepName.FINALIZE_PRODUCT:
            return self._step_finalize_product(product, input_data)
        else:
            raise ValueError(f"Unknown step: {step_name}")
    
    def _step_generate_code(
        self,
        product: Product,
        input_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Step 1: Generate code
        
        TODO: Implement actual code generation using agents
        """
        # Placeholder implementation
        return {
            "code_generated": True,
            "backend_files": [
                "backend/main.py",
                "backend/models.py",
                "backend/api.py",
            ],
            "frontend_files": [
                "frontend/src/App.tsx",
                "frontend/src/components/TaskList.tsx",
            ],
        }
    
    def _step_create_tests(
        self,
        product: Product,
        input_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Step 2: Create tests
        
        TODO: Implement actual test generation using agents
        """
        # Get code files from previous step
        statement = select(ProductStep).where(
            ProductStep.product_id == product.id,
            ProductStep.step_name == StepName.GENERATE_CODE,
        )
        code_step = self.session.exec(statement).first()
        
        if not code_step or not code_step.output_data:
            raise ValueError("Code generation step output not found")
        
        # Placeholder implementation
        return {
            "tests_created": True,
            "test_files": [
                "backend/tests/test_main.py",
                "backend/tests/test_api.py",
                "frontend/src/__tests__/App.test.tsx",
            ],
        }
    
    def _step_generate_docs(
        self,
        product: Product,
        input_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Step 3: Generate documentation
        
        TODO: Implement actual documentation generation using agents
        """
        # Placeholder implementation
        return {
            "docs_generated": True,
            "readme_path": "README.md",
            "api_docs_path": "docs/api.md",
        }
    
    def _step_validate_structure(
        self,
        product: Product,
        input_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Step 4: Validate structure
        
        TODO: Implement actual validation using agents
        """
        # Placeholder implementation
        return {
            "validation_passed": True,
            "validation_errors": [],
        }
    
    def _step_finalize_product(
        self,
        product: Product,
        input_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Step 5: Finalize product
        
        TODO: Implement actual finalization using agents
        """
        # Update product with version and summary
        product.version_tag = "v1.0.0"
        product.summary = f"Product '{product.name}' created successfully with stack: {product.stack}"
        product.updated_at = datetime.utcnow()
        self.session.add(product)
        self.session.commit()
        
        return {
            "version_tag": product.version_tag,
            "summary": product.summary,
        }
    
    def get_product_status(self, product_id: int) -> Dict[str, Any]:
        """
        Get the status of a product and its steps.
        
        Args:
            product_id: ID of the product
            
        Returns:
            Status information
        """
        # Get product
        product = self.session.get(Product, product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")
        
        # Get steps
        statement = select(ProductStep).where(
            ProductStep.product_id == product_id
        ).order_by(ProductStep.id)
        steps = self.session.exec(statement).all()
        
        return {
            "product_id": product.id,
            "product_name": product.name,
            "status": product.status.value,
            "steps": [
                {
                    "step_name": step.step_name.value,
                    "status": step.status.value,
                    "started_at": step.started_at.isoformat() if step.started_at else None,
                    "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                    "error": step.error_message,
                }
                for step in steps
            ],
        }
