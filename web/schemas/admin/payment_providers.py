from pydantic import BaseModel, Field, field_validator
from typing import Any, Optional
from web.schemas.types import UTCDatetime


class PaymentProviderFieldOption(BaseModel):
    value: str
    label: str


class PaymentProviderFieldResponse(BaseModel):
    key: str
    label: str
    kind: str
    required: bool
    secret: bool
    help: Optional[str] = None
    options: list[PaymentProviderFieldOption] = Field(default_factory=list)
    minimum: Optional[int] = None
    maximum: Optional[int] = None
    value: Any = None
    is_set: bool = False


class PaymentProviderResponse(BaseModel):
    id: int
    provider_key: str
    display_name: str
    is_enabled: bool
    sort_order: int
    is_configured: bool
    missing_fields: list[str]
    fields: list[PaymentProviderFieldResponse]
    updated_at: Optional[UTCDatetime]


class PaymentProviderUpdateRequest(BaseModel):
    is_enabled: Optional[bool] = None
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    config: Optional[dict[str, Any]] = None

    @field_validator("display_name")
    @classmethod
    def normalise_display_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Название способа оплаты не может быть пустым")
        return value


class PaymentProvidersReorderRequest(BaseModel):
    provider_ids: list[int] = Field(min_length=1)


class PaymentProvidersListResponse(BaseModel):
    items: list[PaymentProviderResponse]
