import pytest
from types import SimpleNamespace

from config.settings import Settings
from core.services.payment_provider_settings import (
    decrypt_config,
    encrypt_config,
    merge_and_validate_config,
    missing_required_fields,
    apply_provider_configs_to_settings,
    bootstrap_provider_configs_from_env,
)


def make_settings(**overrides) -> Settings:
    values = {
        "BOT_TOKEN": "123456:abcdefghijklmnopqrstuvwxyzABCDEFG",
        "WEB_JWT_SECRET": "test-secret-that-is-long-enough-for-provider-config",
    }
    values.update(overrides)
    return Settings(**values)


def test_provider_config_encryption_round_trip_does_not_expose_secret():
    settings = make_settings()
    config = {"YOOKASSA_SHOP_ID": "shop", "YOOKASSA_SECRET_KEY": "top-secret"}

    encrypted = encrypt_config(settings, config)

    assert "top-secret" not in encrypted
    assert decrypt_config(settings, encrypted) == config


def test_provider_config_requires_same_application_secret():
    encrypted = encrypt_config(make_settings(), {"CRYPTOPAY_TOKEN": "token"})

    assert decrypt_config(make_settings(WEB_JWT_SECRET="another-stable-secret-value"), encrypted) == {}


def test_merge_validates_numeric_ranges_and_can_clear_secrets():
    current = {"SEVERPAY_MID": 42, "SEVERPAY_TOKEN": "secret"}

    updated = merge_and_validate_config("severpay", current, {"SEVERPAY_TOKEN": None})
    assert "SEVERPAY_TOKEN" not in updated

    with pytest.raises(ValueError, match="не меньше 30"):
        merge_and_validate_config("severpay", current, {"SEVERPAY_LIFETIME_MINUTES": 5})


def test_stars_needs_no_provider_token_but_yookassa_needs_credentials():
    assert missing_required_fields("stars", {}) == []
    assert missing_required_fields("yookassa", {})[:2] == [
        "YOOKASSA_SHOP_ID",
        "YOOKASSA_SECRET_KEY",
    ]


@pytest.mark.asyncio
async def test_database_config_replaces_legacy_environment_values(monkeypatch):
    settings = make_settings(
        YOOKASSA_ENABLED=True,
        YOOKASSA_SHOP_ID="legacy-shop",
        YOOKASSA_SECRET_KEY="legacy-secret",
    )
    stored = {
        "YOOKASSA_SHOP_ID": "database-shop",
        "YOOKASSA_SECRET_KEY": "database-secret",
    }
    rows = [
        SimpleNamespace(
            provider_key="yookassa",
            is_enabled=False,
            config_encrypted=encrypt_config(settings, stored),
        )
    ]

    async def fake_get_all_providers(_db):
        return rows

    monkeypatch.setattr(
        "core.dal.payment_provider_config_dal.get_all_providers",
        fake_get_all_providers,
    )

    await apply_provider_configs_to_settings(SimpleNamespace(), settings)

    assert settings.YOOKASSA_ENABLED is False
    assert settings.YOOKASSA_SHOP_ID == "database-shop"
    assert settings.YOOKASSA_SECRET_KEY == "database-secret"
    assert settings.STARS_ENABLED is False


@pytest.mark.asyncio
async def test_env_import_preserves_existing_admin_enabled_state(monkeypatch):
    settings = make_settings(CRYPTOPAY_ENABLED=True, CRYPTOPAY_TOKEN="legacy-token")
    row = SimpleNamespace(
        provider_key="cryptopay",
        is_enabled=False,
        config_encrypted=None,
    )

    async def fake_get_all_providers(_db):
        return [row]

    monkeypatch.setattr(
        "core.dal.payment_provider_config_dal.get_all_providers",
        fake_get_all_providers,
    )
    db = SimpleNamespace(flush=lambda: None)

    async def flush():
        return None

    db.flush = flush
    await bootstrap_provider_configs_from_env(db, settings)

    assert row.is_enabled is False
    assert decrypt_config(settings, row.config_encrypted)["CRYPTOPAY_TOKEN"] == "legacy-token"
