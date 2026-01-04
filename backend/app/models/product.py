from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class ProductStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ProductBase(SQLModel):
    project_id: int = Field(foreign_key="project.id", index=True)
    name: str = Field(index=True)
    stack: Optional[str] = None
    objective: Optional[str] = None
    status: ProductStatus = Field(default=ProductStatus.DRAFT)
    version_tag: Optional[str] = None
    summary: Optional[str] = None


class Product(ProductBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProductCreate(SQLModel):
    product_name: str
    stack: str
    objective: str


class ProductRead(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime


class ProductUpdate(SQLModel):
    name: Optional[str] = None
    stack: Optional[str] = None
    objective: Optional[str] = None
    status: Optional[ProductStatus] = None
    version_tag: Optional[str] = None
    summary: Optional[str] = None
