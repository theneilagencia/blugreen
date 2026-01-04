"""
Create Flow API

Implements REST API for the Create Flow.
Follows the contract defined in docs/contracts/create_flow_step_based.md
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session

from app.database import get_session
from app.models import ProductCreate
from app.services.create_flow import CreateFlowExecutor


router = APIRouter(tags=["create"])


@router.post("/projects/{project_id}/products", status_code=202)
async def create_product(
    project_id: int,
    product_data: ProductCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """
    Create a new product and start the Create Flow.
    
    **Request Body:**
    ```json
    {
      "product_name": "Task Manager API",
      "stack": "FastAPI, PostgreSQL, React",
      "objective": "Create a REST API for task management"
    }
    ```
    
    **Response (202 Accepted):**
    ```json
    {
      "product_id": 123,
      "status": "running",
      "message": "Product creation started in background",
      "monitor_url": "/products/123/status"
    }
    ```
    """
    try:
        # Initialize executor
        executor = CreateFlowExecutor(session)
        
        # Create product and initialize steps
        product = executor.initialize_product(
            project_id=project_id,
            product_name=product_data.product_name,
            stack=product_data.stack,
            objective=product_data.objective,
        )
        
        # Execute flow in background
        background_tasks.add_task(executor.execute_flow, product.id)
        
        return {
            "product_id": product.id,
            "status": "running",
            "message": "Product creation started in background",
            "monitor_url": f"/products/{product.id}/status",
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/products/{product_id}/status")
async def get_product_status(
    product_id: int,
    session: Session = Depends(get_session),
):
    """
    Get the status of a product and its steps.
    
    **Response:**
    ```json
    {
      "product_id": 123,
      "product_name": "Task Manager API",
      "status": "running",
      "steps": [
        {
          "step_name": "generate_code",
          "status": "done",
          "started_at": "2026-01-03T10:00:00Z",
          "completed_at": "2026-01-03T10:05:00Z",
          "error": null
        }
      ]
    }
    ```
    """
    try:
        executor = CreateFlowExecutor(session)
        status = executor.get_product_status(product_id)
        return status
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
