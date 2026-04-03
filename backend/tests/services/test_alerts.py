from unittest.mock import patch

from sqlmodel import Session, select

from app.core.config import settings
from app.models import AdminSetting, AlertRecord, AlertType, User, UserLimit
from app.services.alerts import (
    _alert_already_sent,
    _current_period,
    _record_alert,
    check_and_send_alerts,
)


def _get_superuser(db: Session) -> User:
    user = db.exec(select(User).where(User.email == settings.FIRST_SUPERUSER)).first()
    assert user is not None
    return user


def _ensure_limit(db: Session, user_id, max_tokens: int) -> UserLimit:
    existing = db.exec(select(UserLimit).where(UserLimit.user_id == user_id)).first()
    if existing:
        existing.max_tokens_per_month = max_tokens
        db.add(existing)
    else:
        existing = UserLimit(user_id=user_id, max_tokens_per_month=max_tokens)
        db.add(existing)
    db.commit()
    db.refresh(existing)
    return existing


def _cleanup_alerts(db: Session) -> None:
    for record in db.exec(select(AlertRecord)).all():
        db.delete(record)
    db.commit()


def test_alert_sent_at_80_percent(db: Session) -> None:
    user = _get_superuser(db)
    _ensure_limit(db, user.id, max_tokens=1000)
    _cleanup_alerts(db)

    with patch("app.services.alerts._send_alert_email") as mock_send:
        check_and_send_alerts(db, user.id, tokens_this_month=800)
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[0][2] == AlertType.USER_80_PCT

    # Verify alert record created
    period = _current_period()
    assert _alert_already_sent(db, user.id, AlertType.USER_80_PCT, period)

    _cleanup_alerts(db)


def test_alert_sent_at_100_percent(db: Session) -> None:
    user = _get_superuser(db)
    _ensure_limit(db, user.id, max_tokens=1000)
    _cleanup_alerts(db)

    with patch("app.services.alerts._send_alert_email") as mock_send:
        check_and_send_alerts(db, user.id, tokens_this_month=1000)
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[0][2] == AlertType.USER_100_PCT

    _cleanup_alerts(db)


def test_alert_not_resent_same_period(db: Session) -> None:
    user = _get_superuser(db)
    _ensure_limit(db, user.id, max_tokens=1000)
    _cleanup_alerts(db)

    period = _current_period()
    _record_alert(db, user.id, AlertType.USER_80_PCT, period)

    with patch("app.services.alerts._send_alert_email") as mock_send:
        check_and_send_alerts(db, user.id, tokens_this_month=850)
        mock_send.assert_not_called()

    _cleanup_alerts(db)


def test_100_pct_alert_still_sent_if_only_80_exists(db: Session) -> None:
    user = _get_superuser(db)
    _ensure_limit(db, user.id, max_tokens=1000)
    _cleanup_alerts(db)

    period = _current_period()
    _record_alert(db, user.id, AlertType.USER_80_PCT, period)

    with patch("app.services.alerts._send_alert_email") as mock_send:
        check_and_send_alerts(db, user.id, tokens_this_month=1000)
        mock_send.assert_called_once()
        assert mock_send.call_args[0][2] == AlertType.USER_100_PCT

    _cleanup_alerts(db)


def test_no_alert_when_no_limit_set(db: Session) -> None:
    user = _get_superuser(db)
    # Remove any limit
    existing = db.exec(select(UserLimit).where(UserLimit.user_id == user.id)).first()
    if existing:
        db.delete(existing)
        db.commit()
    _cleanup_alerts(db)

    with patch("app.services.alerts._send_alert_email") as mock_send:
        check_and_send_alerts(db, user.id, tokens_this_month=999999)
        mock_send.assert_not_called()

    _cleanup_alerts(db)


def test_no_alert_when_below_threshold(db: Session) -> None:
    user = _get_superuser(db)
    _ensure_limit(db, user.id, max_tokens=1000)
    _cleanup_alerts(db)

    with patch("app.services.alerts._send_alert_email") as mock_send:
        check_and_send_alerts(db, user.id, tokens_this_month=500)
        mock_send.assert_not_called()

    _cleanup_alerts(db)


def test_global_spend_threshold_stored(db: Session) -> None:
    """Verify the monthly_spend_threshold admin setting can be stored and read."""
    existing = db.exec(
        select(AdminSetting).where(AdminSetting.key == "monthly_spend_threshold")
    ).first()
    if existing:
        db.delete(existing)
        db.commit()

    db.add(AdminSetting(key="monthly_spend_threshold", value="50000"))
    db.commit()

    setting = db.exec(
        select(AdminSetting).where(AdminSetting.key == "monthly_spend_threshold")
    ).first()
    assert setting is not None
    assert setting.value == "50000"

    db.delete(setting)
    db.commit()


def test_alert_email_skipped_when_not_configured(db: Session) -> None:
    """When SMTP is not configured, alerts are recorded but no email sent."""
    user = _get_superuser(db)
    _ensure_limit(db, user.id, max_tokens=1000)
    _cleanup_alerts(db)

    with patch.object(settings, "SMTP_HOST", None):
        check_and_send_alerts(db, user.id, tokens_this_month=800)

    # Alert record should still be created
    period = _current_period()
    assert _alert_already_sent(db, user.id, AlertType.USER_80_PCT, period)

    _cleanup_alerts(db)


def test_alert_history_endpoint(client, db: Session) -> None:
    user = _get_superuser(db)
    _cleanup_alerts(db)
    _record_alert(db, user.id, AlertType.USER_80_PCT, _current_period())

    # Login as admin
    r = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={
            "username": settings.FIRST_SUPERUSER,
            "password": settings.FIRST_SUPERUSER_PASSWORD,
        },
    )
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = client.get(f"{settings.API_V1_STR}/admin/alerts", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    assert any(a["alert_type"] == "user_80_pct" for a in data["data"])

    _cleanup_alerts(db)
