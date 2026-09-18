from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Account
from web.dependencies import get_db, get_current_admin
from web.schemas.admin.payment_providers import (
    PaymentProviderResponse,
    PaymentProviderUpdateRequest,
    PaymentProvidersListResponse,
    PaymentProvidersReorderRequest,
)
from core.dal.payment_provider_config_dal import get_all_providers, update_provider, reorder_providers
from config.settings import Settings
from web.dependencies import get_settings_dep
from core.services.payment_provider_settings import (
    PROVIDER_DEFINITIONS,
    admin_field_payload,
    decrypt_config,
    encrypt_config,
    merge_and_validate_config,
    missing_required_fields,
)
from web.middleware.rate_limit import admin_action_limit
from web.routers.admin.audit import add_admin_audit_log

router = APIRouter()


def _provider_response(provider, settings: Settings) -> PaymentProviderResponse:
    definition = PROVIDER_DEFINITIONS.get(provider.provider_key)
    config = decrypt_config(settings, provider.config_encrypted)
    missing = missing_required_fields(provider.provider_key, config)
    return PaymentProviderResponse(
        id=provider.id,
        provider_key=provider.provider_key,
        display_name=provider.display_name,
        is_enabled=provider.is_enabled,
        sort_order=provider.sort_order,
        is_configured=not missing,
        missing_fields=missing,
        fields=[admin_field_payload(field, config) for field in definition.fields] if definition else [],
        updated_at=provider.updated_at,
    )


@router.get("/payment-providers", response_model=PaymentProvidersListResponse)
async def list_payment_providers(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    _admin: Account = Depends(get_current_admin),
):
    providers = await get_all_providers(db)
    return PaymentProvidersListResponse(
        items=[_provider_response(provider, settings) for provider in providers]
    )


@router.patch("/payment-providers/{provider_id}", response_model=PaymentProviderResponse, dependencies=[Depends(admin_action_limit)])
async def update_payment_provider(
    provider_id: int,
    body: PaymentProviderUpdateRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    admin: Account = Depends(get_current_admin),
):
    current = next((p for p in await get_all_providers(db) if p.id == provider_id), None)
    if current is None:
        raise HTTPException(status_code=404, detail="Provider not found")

    updates = body.model_dump(exclude_none=True, exclude={"config"})
    config = decrypt_config(settings, current.config_encrypted)
    if body.config is not None:
        try:
            config = merge_and_validate_config(current.provider_key, config, body.config)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        updates["config_encrypted"] = encrypt_config(settings, config)
    if body.is_enabled:
        missing = missing_required_fields(current.provider_key, config)
        if missing:
            definition = PROVIDER_DEFINITIONS[current.provider_key]
            labels = {field.key: field.label for field in definition.fields}
            readable = ", ".join(labels.get(key, key) for key in missing)
            raise HTTPException(
                status_code=422,
                detail=f"Сначала заполните обязательные поля: {readable}",
            )
    provider = await update_provider(db, provider_id, **updates)
    await add_admin_audit_log(
        db,
        admin,
        "admin_payment_provider_update",
        details={
            "provider_id": provider_id,
            "updated_fields": [key for key in updates if key != "config_encrypted"],
            "config_fields": sorted((body.config or {}).keys()),
        },
    )
    await db.commit()
    return _provider_response(provider, settings)


@router.put(
    "/payment-providers/order",
    response_model=PaymentProvidersListResponse,
    dependencies=[Depends(admin_action_limit)],
)
async def update_payment_provider_order(
    body: PaymentProvidersReorderRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    admin: Account = Depends(get_current_admin),
):
    try:
        providers = await reorder_providers(db, body.provider_ids)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await add_admin_audit_log(
        db,
        admin,
        "admin_payment_providers_reorder",
        details={"provider_ids": body.provider_ids},
    )
    await db.commit()
    return PaymentProvidersListResponse(
        items=[_provider_response(provider, settings) for provider in providers]
    )
