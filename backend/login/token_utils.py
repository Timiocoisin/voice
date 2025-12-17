import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional

from backend.config.config import SECRET_KEY


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    s = data.encode("ascii")
    s += b"=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s)


def _sign(message: bytes, secret: bytes) -> str:
    sig = hmac.new(secret, message, hashlib.sha256).digest()
    return _b64url_encode(sig)


def generate_token(email: str) -> str:
    """生成包含用户邮箱和过期时间的令牌（JWT HS256 兼容实现，避免第三方 jwt 包冲突）"""
    exp = int(time.time()) + 7 * 24 * 60 * 60  # 7 天
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"email": email, "exp": exp}

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    secret = SECRET_KEY.encode("utf-8") if isinstance(SECRET_KEY, str) else SECRET_KEY
    signature_b64 = _sign(signing_input, secret)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """验证令牌有效性，成功返回 payload dict，失败返回 None"""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts

        secret = SECRET_KEY.encode("utf-8") if isinstance(SECRET_KEY, str) else SECRET_KEY
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = _sign(signing_input, secret)
        if not hmac.compare_digest(expected_sig, sig_b64):
            return None

        header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
        if header.get("alg") != "HS256":
            return None

        payload: Dict[str, Any] = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        exp = payload.get("exp")
        if not isinstance(exp, int):
            return None
        if exp < int(time.time()):
            return None
        return payload
    except Exception:
        return None