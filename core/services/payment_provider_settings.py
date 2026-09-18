"""Database-backed configuration for payment providers.

Provider credentials are encrypted with a key derived from ``WEB_JWT_SECRET``.
The environment values are used once, only to import an existing installation;
after that the database is the sole source of truth.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Iterable

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import Settings
from db.models import PaymentProviderConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderField:
    key: str
    label: str
    kind: str = "text"
    required: bool = False
    secret: bool = False
    help: str | None = None
    options: tuple[tuple[str, str], ...] = ()
    minimum: int | None = None
    maximum: int | None = None


@dataclass(frozen=True)
class ProviderDefinition:
    key: str
    default_name: str
    enabled_attr: str
    fields: tuple[ProviderField, ...]
    web_supported: bool = True
    user_selectable: bool = True


def _field(
    key: str,
    label: str,
    *,
    kind: str = "text",
    required: bool = False,
    secret: bool = False,
    help: str | None = None,
    options: tuple[tuple[str, str], ...] = (),
    minimum: int | None = None,
    maximum: int | None = None,
) -> ProviderField:
    return ProviderField(key, label, kind, required, secret, help, options, minimum, maximum)


PROVIDER_DEFINITIONS: dict[str, ProviderDefinition] = {
    "yookassa": ProviderDefinition(
        "yookassa",
        "Картой или СБП",
        "YOOKASSA_ENABLED",
        (
            _field("YOOKASSA_SHOP_ID", "Shop ID", required=True),
            _field("YOOKASSA_SECRET_KEY", "Секретный ключ", required=True, secret=True),
            _field("YOOKASSA_RETURN_URL", "URL возврата", kind="url"),
            _field("YOOKASSA_DEFAULT_RECEIPT_EMAIL", "Email для чеков", kind="email"),
            _field("YOOKASSA_VAT_CODE", "Ставка НДС", kind="number", required=True, minimum=1, maximum=6),
            _field("YOOKASSA_TAX_SYSTEM_CODE", "Система налогообложения", kind="number", minimum=1, maximum=6),
            _field(
                "YOOKASSA_PAYMENT_MODE",
                "Признак способа расчёта",
                kind="select",
                options=(("full_payment", "Полный расчёт"), ("full_prepayment", "Полная предоплата")),
            ),
            _field(
                "YOOKASSA_PAYMENT_SUBJECT",
                "Предмет расчёта",
                kind="select",
                options=(("service", "Услуга"), ("payment", "Платёж")),
            ),
            _field("YOOKASSA_AUTOPAYMENTS_ENABLED", "Автопродление", kind="boolean"),
            _field(
                "YOOKASSA_AUTOPAYMENTS_REQUIRE_CARD_BINDING",
                "Обязательно сохранять карту",
                kind="boolean",
            ),
        ),
    ),
    "freekassa": ProviderDefinition(
        "freekassa",
        "СБП",
        "FREEKASSA_ENABLED",
        (
            _field("FREEKASSA_MERCHANT_ID", "ID магазина", required=True),
            _field("FREEKASSA_API_KEY", "API-ключ", required=True, secret=True),
            _field("FREEKASSA_FIRST_SECRET", "Секретное слово №1", required=True, secret=True),
            _field("FREEKASSA_SECOND_SECRET", "Секретное слово №2", required=True, secret=True),
            _field("FREEKASSA_PAYMENT_IP", "Публичный IP сервера"),
            _field("FREEKASSA_PAYMENT_METHOD_ID", "ID способа оплаты", kind="number", minimum=1),
            _field("FREEKASSA_PAYMENT_URL", "URL платёжной формы", kind="url"),
        ),
    ),
    "platega": ProviderDefinition(
        "platega",
        "Картой или СБП",
        "PLATEGA_ENABLED",
        (
            _field("PLATEGA_MERCHANT_ID", "Merchant ID", required=True),
            _field("PLATEGA_SECRET", "Секретный ключ", required=True, secret=True),
            _field("PLATEGA_PAYMENT_METHOD", "Способ оплаты", kind="number", required=True, minimum=1),
            _field("PLATEGA_BASE_URL", "URL API", kind="url", required=True),
            _field("PLATEGA_RETURN_URL", "URL возврата", kind="url"),
            _field("PLATEGA_FAILED_URL", "URL при ошибке", kind="url"),
        ),
    ),
    "severpay": ProviderDefinition(
        "severpay",
        "Картой или СБП",
        "SEVERPAY_ENABLED",
        (
            _field("SEVERPAY_MID", "MID", kind="number", required=True, minimum=1),
            _field("SEVERPAY_TOKEN", "Токен подписи", required=True, secret=True),
            _field("SEVERPAY_BASE_URL", "URL API", kind="url", required=True),
            _field("SEVERPAY_RETURN_URL", "URL возврата", kind="url"),
            _field("SEVERPAY_LIFETIME_MINUTES", "Срок ссылки, минут", kind="number", minimum=30, maximum=4320),
        ),
    ),
    "lavapay": ProviderDefinition(
        "lavapay",
        "Картой или СБП",
        "LAVAPAY_ENABLED",
        (
            _field("LAVAPAY_SHOP_ID", "Shop ID", required=True),
            _field("LAVAPAY_SECRET_KEY", "Секретный ключ", required=True, secret=True),
            _field("LAVAPAY_WEBHOOK_SECRET", "Секрет вебхука", required=True, secret=True),
            _field("LAVAPAY_BASE_URL", "URL API", kind="url", required=True),
            _field("LAVAPAY_RETURN_URL", "URL успешной оплаты", kind="url"),
            _field("LAVAPAY_FAIL_URL", "URL неуспешной оплаты", kind="url"),
            _field("LAVAPAY_EXPIRE_MINUTES", "Срок счёта, минут", kind="number", minimum=1, maximum=7200),
        ),
    ),
    "cryptopay": ProviderDefinition(
        "cryptopay",
        "Криптовалютой",
        "CRYPTOPAY_ENABLED",
        (
            _field("CRYPTOPAY_TOKEN", "API-токен", required=True, secret=True),
            _field(
                "CRYPTOPAY_NETWORK",
                "Сеть",
                kind="select",
                required=True,
                options=(("mainnet", "Основная"), ("testnet", "Тестовая")),
            ),
            _field(
                "CRYPTOPAY_CURRENCY_TYPE",
                "Тип цены",
                kind="select",
                required=True,
                options=(("fiat", "Фиат"), ("crypto", "Криптовалюта")),
            ),
            _field("CRYPTOPAY_ASSET", "Валюта цены", required=True, help="Например: RUB или USDT"),
        ),
    ),
    "stars": ProviderDefinition(
        "stars",
        "Telegram Stars",
        "STARS_ENABLED",
        (
            _field(
                "STARS_PROVIDER_TOKEN",
                "Provider token",
                secret=True,
                help="Для Telegram Stars поле обычно оставляют пустым.",
            ),
        ),
        web_supported=False,
    ),
    "nalogo": ProviderDefinition(
        "nalogo",
        "Чеки для самозанятого",
        "LKNPD_ENABLED",
        (
            _field("LKNPD_INN", "ИНН", required=True),
            _field("LKNPD_PASSWORD", "Пароль", required=True, secret=True),
            _field("LKNPD_API_URL", "URL API", kind="url", required=True),
            _field(
                "LKNPD_RECEIPT_NAME_SUBSCRIPTION",
                "Название услуги подписки",
                required=True,
                help="Используйте {months} для количества месяцев.",
            ),
            _field(
                "LKNPD_RECEIPT_NAME_TRAFFIC",
                "Название услуги трафика",
                required=True,
                help="Используйте {gb} для объёма трафика.",
            ),
        ),
        web_supported=False,
        user_selectable=False,
    ),
}


def _fernet(settings: Settings) -> Fernet:
    source = (settings.WEB_JWT_SECRET or "").strip()
    if not source:
        raise RuntimeError("WEB_JWT_SECRET is required to encrypt payment provider settings")
    digest = hashlib.sha256(("sline-payment-settings-v1:" + source).encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_config(settings: Settings, config: dict[str, Any]) -> str:
    raw = json.dumps(config, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return _fernet(settings).encrypt(raw).decode("ascii")


def decrypt_config(settings: Settings, encrypted: str | None) -> dict[str, Any]:
    if not encrypted:
        return {}
    try:
        raw = _fernet(settings).decrypt(encrypted.encode("ascii"))
        value = json.loads(raw.decode("utf-8"))
    except (InvalidToken, ValueError, TypeError, json.JSONDecodeError) as exc:
        logger.error("Unable to decrypt payment provider configuration: %s", exc)
        return {}
    return value if isinstance(value, dict) else {}


def _normalise_field_value(field: ProviderField, value: Any) -> Any:
    if value is None:
        return None
    if field.kind == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes", "on"}:
                return True
            if lowered in {"false", "0", "no", "off"}:
                return False
        raise ValueError(f"Поле «{field.label}» должно быть переключателем")
    if field.kind == "number":
        if value == "":
            return None
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Поле «{field.label}» должно быть целым числом") from exc
        if field.minimum is not None and number < field.minimum:
            raise ValueError(f"Поле «{field.label}» должно быть не меньше {field.minimum}")
        if field.maximum is not None and number > field.maximum:
            raise ValueError(f"Поле «{field.label}» должно быть не больше {field.maximum}")
        return number
    text = str(value).strip()
    if not text:
        return None
    if len(text) > 1000:
        raise ValueError(f"Поле «{field.label}» слишком длинное")
    if field.options and text not in {option[0] for option in field.options}:
        raise ValueError(f"Недопустимое значение поля «{field.label}»")
    if field.kind == "email" and ("@" not in text or text.startswith("@") or text.endswith("@")):
        raise ValueError(f"Поле «{field.label}» должно содержать корректный email")
    if field.kind == "url" and not text.lower().startswith(("https://", "http://")):
        raise ValueError(f"Поле «{field.label}» должно содержать URL с http:// или https://")
    return text


def merge_and_validate_config(
    provider_key: str,
    current: dict[str, Any],
    updates: dict[str, Any],
) -> dict[str, Any]:
    definition = PROVIDER_DEFINITIONS.get(provider_key)
    if definition is None:
        raise ValueError("Неизвестный платёжный провайдер")
    allowed = {field.key: field for field in definition.fields}
    unknown = set(updates) - set(allowed)
    if unknown:
        raise ValueError(f"Неизвестные поля настройки: {', '.join(sorted(unknown))}")
    merged = {key: value for key, value in current.items() if key in allowed}
    for key, value in updates.items():
        normalised = _normalise_field_value(allowed[key], value)
        if normalised is None:
            merged.pop(key, None)
        else:
            merged[key] = normalised
    return merged


def missing_required_fields(provider_key: str, config: dict[str, Any]) -> list[str]:
    definition = PROVIDER_DEFINITIONS.get(provider_key)
    if definition is None:
        return ["provider"]
    return [field.key for field in definition.fields if field.required and config.get(field.key) in (None, "")]


def provider_is_configured(provider_key: str, config: dict[str, Any]) -> bool:
    return not missing_required_fields(provider_key, config)


async def bootstrap_provider_configs_from_env(db: AsyncSession, settings: Settings) -> int:
    """One-time import for installations that previously used payment env vars."""
    from core.dal.payment_provider_config_dal import get_all_providers

    imported = 0
    for row in await get_all_providers(db):
        definition = PROVIDER_DEFINITIONS.get(row.provider_key)
        if definition is None or row.config_encrypted is not None:
            continue
        config: dict[str, Any] = {}
        for field in definition.fields:
            value = getattr(settings, field.key, None)
            if value not in (None, ""):
                config[field.key] = value
        row.config_encrypted = encrypt_config(settings, config)
        # Existing rows may already have been changed through the old admin
        # toggle.  Preserve that state: env credentials are imported once, but
        # the database remains authoritative for what users can actually see.
        legacy_enabled = bool(row.is_enabled)
        if row.provider_key == "nalogo" and config.get("LKNPD_INN") and config.get("LKNPD_PASSWORD"):
            legacy_enabled = True
        row.is_enabled = legacy_enabled
        imported += 1
    if imported:
        await db.flush()
        logger.info("Imported legacy environment settings for %d payment providers", imported)
    return imported


async def apply_provider_configs_to_settings(
    db: AsyncSession,
    settings: Settings,
) -> Settings:
    """Mutate and return ``settings`` with database-backed provider values."""
    from core.dal.payment_provider_config_dal import get_all_providers

    rows = await get_all_providers(db)
    for definition in PROVIDER_DEFINITIONS.values():
        setattr(settings, definition.enabled_attr, False)
        for field in definition.fields:
            model_field = Settings.model_fields.get(field.key)
            default = model_field.get_default(call_default_factory=True) if model_field else None
            setattr(settings, field.key, default)
    order: list[str] = []
    for row in rows:
        definition = PROVIDER_DEFINITIONS.get(row.provider_key)
        if definition is None:
            continue
        config = decrypt_config(settings, row.config_encrypted)
        setattr(settings, definition.enabled_attr, bool(row.is_enabled))
        for field in definition.fields:
            if field.key in config:
                setattr(settings, field.key, config[field.key])
        if definition.user_selectable:
            order.append(row.provider_key)
    settings.PAYMENT_METHODS_ORDER = ",".join(order)
    return settings


async def runtime_settings(db: AsyncSession, base: Settings) -> Settings:
    copy = base.model_copy(deep=True)
    return await apply_provider_configs_to_settings(db, copy)


async def public_provider_options(
    db: AsyncSession,
    settings: Settings,
    *,
    web_only: bool,
) -> list[dict[str, str]]:
    from core.dal.payment_provider_config_dal import get_all_providers

    options: list[dict[str, str]] = []
    for row in await get_all_providers(db):
        definition = PROVIDER_DEFINITIONS.get(row.provider_key)
        if (
            definition is None
            or not definition.user_selectable
            or (web_only and not definition.web_supported)
            or not row.is_enabled
        ):
            continue
        config = decrypt_config(settings, row.config_encrypted)
        if provider_is_configured(row.provider_key, config):
            options.append({"key": row.provider_key, "display_name": row.display_name})
    return options


def admin_field_payload(
    field: ProviderField,
    config: dict[str, Any],
) -> dict[str, Any]:
    is_set = config.get(field.key) not in (None, "")
    return {
        "key": field.key,
        "label": field.label,
        "kind": field.kind,
        "required": field.required,
        "secret": field.secret,
        "help": field.help,
        "options": [{"value": value, "label": label} for value, label in field.options],
        "minimum": field.minimum,
        "maximum": field.maximum,
        "value": None if field.secret else config.get(field.key),
        "is_set": is_set,
    }


def provider_config_from_env(settings: Settings, provider_key: str) -> dict[str, Any]:
    """Small test/debug helper used by the one-time import."""
    definition = PROVIDER_DEFINITIONS[provider_key]
    return {
        field.key: getattr(settings, field.key)
        for field in definition.fields
        if getattr(settings, field.key, None) not in (None, "")
    }


def known_provider_keys() -> Iterable[str]:
    return PROVIDER_DEFINITIONS.keys()
