from __future__ import annotations

from klyuchnik.config import AppSettings


def test_app_settings_accepts_single_excluded_user_id_as_int() -> None:
    settings = AppSettings(
        bot_token="123456:REPLACE_ME",
        chat_id=-100123,
        rate_limit_excluded_user_ids=1,
    )

    assert settings.rate_limit_excluded_user_ids == {1}


def test_app_settings_accepts_excluded_user_ids_as_comma_separated_string() -> None:
    settings = AppSettings(
        bot_token="123456:REPLACE_ME",
        chat_id=-100123,
        rate_limit_excluded_user_ids="1, 2",
    )

    assert settings.rate_limit_excluded_user_ids == {1, 2}
