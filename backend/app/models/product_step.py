from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

from sqlmodel import Field, SQLModel, Column, JSON


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class StepName(str, Enum):
    GENERATE_CODE = "generate_code"
    CREATE_TESTS = "create_tests"
    GENERATE_DOCS = "generate_docs"
    VALIDATE_STRUCTURE = "validate_structure"
    FINALIZE_PRODUCT = "finalize_product"


class ProductStepBase(SQLModel):
    product_id: int = Field(foreign_key="product.id", index=True)
    step_name: StepName = Field(index=True)
    status: StepStatus = Field(default=StepStatus.PENDING)
    input_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    output_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    error_message: Optional[str] = None


class ProductStep(ProductStepBase, table=True):
    __tablename__ = "product_step"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        # Ensure unique constraint on (product_id, step_name)
        table_args = {"extend_existing": True}


class ProductStepCreate(SQLModel):
    product_id: int
    step_name: StepName
    input_data: Optional[Dict[str, Any]] = None


class ProductStepRead(ProductStepBase):
    id: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class ProductStepUpdate(SQLModel):
    status: Optional[StepStatus] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
