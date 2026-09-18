import inspect
from types import NoneType
from typing import get_args, get_type_hints

import bot.handlers.admin.sync_admin as sync_admin
import bot.handlers.admin.user_management as user_management
import bot.middlewares.profile_sync as profile_sync
import bot.services.referral_service as referral_service
import bot.services.subscription_service as subscription_service

MODULES = (
    subscription_service,
    sync_admin,
    user_management,
    profile_sync,
    referral_service,
)


def test_no_bot_module_reads_panel_user_uuid():
    for module in MODULES:
        source = inspect.getsource(module)
        assert "panel_user_uuid" not in source, module.__name__


def test_no_bot_module_calls_removed_panel_methods():
    for module in MODULES:
        source = inspect.getsource(module)
        assert "get_user_by_uuid" not in source, module.__name__
        assert "get_user_by_panel_uuid" not in source, module.__name__
        # Обращение к полю, а не упоминание в комментарии.
        assert '"subscriptionUuid"' not in source, module.__name__


def test_link_details_helper_returns_numeric_id():
    method = subscription_service.SubscriptionService._get_or_create_panel_user_link_details
    hint = get_type_hints(method)["return"]
    link_details = get_args(hint)
    numeric_id = link_details[0]
    assert set(get_args(numeric_id)) == {int, NoneType}
