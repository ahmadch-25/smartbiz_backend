from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.api_response import ApiResponse


class ClientCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=500)


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=500)


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str | None
    phone: str | None
    address: str | None
    created_at: datetime
    updated_at: datetime


ClientResponse = ApiResponse[ClientOut]
ClientListResponse = ApiResponse[list[ClientOut]]
