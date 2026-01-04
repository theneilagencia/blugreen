"""
Create Flow Executor

Implements the step-based Create Flow for autonomous product creation.
Follows the contract defined in docs/contracts/create_flow_step_based.md
"""

from datetime import datetime
from typing import Dict, Any, Optional
import asyncio
import os
from pathlib import Path
from sqlmodel import Session, select

from app.models import (
    Product,
    ProductStatus,
    ProductStep,
    StepName,
    StepStatus,
)
from app.services.agent_runner import AgentRunner
from app.config import get_settings


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
        # Run async flow in sync context
        asyncio.run(self._execute_flow_async(product_id))
    
    async def _execute_flow_async(self, product_id: int) -> None:
        """
        Execute the Create Flow for a product (async).
        
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
                await self._execute_step_async(product_id, step_name)
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
    
    async def _execute_step_async(self, product_id: int, step_name: StepName) -> None:
        """
        Execute a single step (async).
        
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
            output_data = await self._execute_step_logic_async(product_id, step_name, step.input_data)
            
            # Mark as done
            step.status = StepStatus.DONE
            step.completed_at = datetime.utcnow()
            step.output_data = output_data
            step.error_message = None
            
            # Update product if this is finalize step
            if step_name == StepName.FINALIZE_PRODUCT and output_data:
                product = self.session.get(Product, product_id)
                if product:
                    product.version_tag = output_data.get("version_tag")
                    product.summary = output_data.get("summary")
                    product.updated_at = datetime.utcnow()
                    self.session.add(product)
                    self.session.commit()
            
        except Exception as e:
            # Mark as failed
            step.status = StepStatus.FAILED
            step.completed_at = datetime.utcnow()
            step.error_message = str(e)
            raise
        
        finally:
            self.session.add(step)
            self.session.commit()
    
    async def _execute_step_logic_async(
        self,
        product_id: int,
        step_name: StepName,
        input_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Execute the actual logic for a step using AgentRunner.
        
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
        
        # Create workspace for product
        workspace_root = self._get_workspace_root(product_id)
        
        # Initialize agent runner
        agent_runner = AgentRunner(workspace_root)
        
        # Build context for agent
        context = {
            "product_id": product.id,
            "product_name": product.name,
            "stack": product.stack,
            "objective": product.objective,
            "input_data": input_data,
        }
        
        # Add previous step outputs to context
        if step_name != StepName.GENERATE_CODE:
            context["previous_outputs"] = self._get_previous_outputs(product_id, step_name)
        
        # Run agent
        output = await agent_runner.run(step_name.value, context)
        
        return output
    
    def _get_workspace_root(self, product_id: int) -> str:
        """
        Get workspace root directory for a product.
        
        Args:
            product_id: ID of the product
        
        Returns:
            Absolute path to workspace root
        """
        settings = get_settings()
        workspace_base = settings.workspace_root
        workspace_root = Path(workspace_base) / f"product_{product_id}"
        workspace_root.mkdir(parents=True, exist_ok=True)
        return str(workspace_root)
    
    def _get_previous_outputs(self, product_id: int, current_step: StepName) -> Dict[str, Any]:
        """
        Get outputs from previous steps.
        
        Args:
            product_id: ID of the product
            current_step: Current step name
        
        Returns:
            Dict mapping step names to their outputs
        """
        # Get all steps before current step
        current_index = self.STEP_ORDER.index(current_step)
        previous_steps = self.STEP_ORDER[:current_index]
        
        previous_outputs = {}
        for step_name in previous_steps:
            statement = select(ProductStep).where(
                ProductStep.product_id == product_id,
                ProductStep.step_name == step_name,
            )
            step = self.session.exec(statement).first()
            
            if step and step.output_data:
                previous_outputs[step_name.value] = step.output_data
        
        return previous_outputs
    

    
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
