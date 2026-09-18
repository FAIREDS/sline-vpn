from fastapi import APIRouter, Depends
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import Settings, get_settings
from web.dependencies import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/config")
async def get_config(
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    from core.services.payment_provider_settings import public_provider_options

    web_providers = await public_provider_options(db, settings, web_only=True)
    all_providers = await public_provider_options(db, settings, web_only=False)
    return {
        "available_providers": [provider["key"] for provider in web_providers],
        "payment_providers": web_providers,
        "stars_enabled": any(provider["key"] == "stars" for provider in all_providers),
    }
