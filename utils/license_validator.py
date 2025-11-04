"""라이선스 검증 모듈 (Autobomber API 연동)."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict

import requests

from utils.device_identifier import get_device_id

logger = logging.getLogger("license_validator")

API_BASE_URL = "https://www.autobomber.com/api/activation/{code}"
REQUEST_TIMEOUT = 10  # seconds


def _parse_iso_datetime(value: str | None) -> datetime | None:
    """Parse ISO8601 timestamps returned by the activation API."""
    if not value:
        return None

    try:
        # API는 UTC일 때 'Z' 접미사를 사용하므로 표준 형태로 치환한다.
        normalised = value.replace("Z", "+00:00") if value.endswith("Z") else value
        return datetime.fromisoformat(normalised)
    except ValueError:
        logger.warning("라이선스 만료일 파싱 실패: %s", value)
        return None


def _calculate_days_remaining(activation: Dict[str, Any]) -> int:
    """Convert activation payload into remaining days."""
    expires_at = _parse_iso_datetime(activation.get("expiresAt"))
    if expires_at is not None:
        now = datetime.now(timezone.utc)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        delta = expires_at - now
        remaining_days = math.ceil(delta.total_seconds() / (24 * 60 * 60))
        return max(0, remaining_days)

    remaining_ms = activation.get("remainingTimeMs")
    if isinstance(remaining_ms, (int, float)):
        # 이전 Firebase 로직과 유사하게 일(day) 단위로 내림 처리
        millis_per_day = 24 * 60 * 60 * 1000
        remaining_days = math.ceil(remaining_ms / millis_per_day)
        return max(0, int(remaining_days))

    return 0


def _success_message(activation: Dict[str, Any], days_remaining: int) -> str:
    """Build a human friendly success message for the UI."""
    if activation.get("isExpired"):
        return "라이선스가 만료되었습니다."

    if days_remaining > 0:
        return f"라이선스가 유효합니다. (남은 일수: {days_remaining}일)"

    return "라이선스가 유효합니다."


def _format_error_message(payload: Dict[str, Any]) -> str:
    """Extract error message from API failure responses."""
    message = payload.get("error")
    if message:
        return message
    return "라이선스 검증에 실패했습니다."


def _call_activation_api(license_key: str, device_id: str) -> Dict[str, Any]:
    """Call activation API and return parsed JSON payload."""
    url = API_BASE_URL.format(code=license_key)
    payload = {
        "code": license_key,
        "deviceId": device_id,
    }

    try:
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        logger.error("라이선스 서버 요청 실패: %s", exc)
        return {
            "success": False,
            "error": "라이선스 서버에 연결할 수 없습니다.",
        }

    try:
        data = response.json()
    except ValueError:
        logger.error("라이선스 서버 응답이 JSON 형식이 아님: %s", response.text[:200])
        return {
            "success": False,
            "error": "라이선스 서버 응답을 해석할 수 없습니다.",
        }

    if not response.ok and "error" not in data:
        # HTTP 오류지만 에러 메시지가 없는 경우 기본 메시지 제공
        logger.error("라이선스 서버에서 오류 상태 %s 반환", response.status_code)
        data.setdefault("error", "라이선스 검증 요청이 거부되었습니다.")

    return data


def validate_license(license_key: str) -> Dict[str, Any]:
    """Autobomber API를 이용해 라이선스를 검증한다."""
    cleaned_key = (license_key or "").strip().upper()
    if not cleaned_key:
        return {
            "valid": False,
            "message": "라이선스 키가 입력되지 않았습니다.",
            "expiry_date": None,
            "days_remaining": 0,
            "device_registered": False,
        }

    device_id = get_device_id()
    api_response = _call_activation_api(cleaned_key, device_id)

    if api_response.get("success"):
        activation = api_response.get("activation", {})
        days_remaining = _calculate_days_remaining(activation)
        message = _success_message(activation, days_remaining)
        return {
            "valid": not activation.get("isExpired", False),
            "message": message,
            "expiry_date": activation.get("expiresAt"),
            "days_remaining": days_remaining,
            "device_registered": activation.get("isDeviceRegistered", False),
        }

    activation_info = api_response.get("activation") or {}
    days_remaining = _calculate_days_remaining(activation_info)

    return {
        "valid": False,
        "message": _format_error_message(api_response),
        "expiry_date": activation_info.get("expiresAt"),
        "days_remaining": days_remaining,
        "device_registered": activation_info.get("isDeviceRegistered", False),
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        key = sys.argv[1]
        result = validate_license(key)
        print(result)
    else:
        print("사용법: python license_validator.py <license_key>")
