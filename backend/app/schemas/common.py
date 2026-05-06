"""Shared Pydantic response schemas."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

DataT = TypeVar("DataT")


class ApiResponse(BaseModel, Generic[DataT]):
    """Standard API response wrapper used across endpoints."""

    success: bool
    message: str
    data: DataT


class ErrorResponse(BaseModel):
    """Documented shape for controlled API errors."""

    success: bool = False
    message: str
    data: None = None


class ORMBaseModel(BaseModel):
    """Base model that can be created from SQLAlchemy objects when needed."""

    model_config = ConfigDict(from_attributes=True)
