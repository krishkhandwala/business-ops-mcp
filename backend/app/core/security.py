import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings

_fernet = Fernet(settings.get_fernet_key())

SENSITIVE_KEYS = {
    "password",
    "secret",
    "api_key",
    "apikey",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "private_key",
    "client_secret",
    "connection_string",
    "credentials",
}

PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*prompt\s*override", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.IGNORECASE),
    re.compile(r"drop\s+table\s+", re.IGNORECASE),
    re.compile(r";\s*delete\s+from\s+", re.IGNORECASE),
]


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def create_access_token(
    subject: str,
    organization_id: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": str(subject),
        "org_id": str(organization_id),
        "role": role,
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str, organization_id: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(subject),
        "org_id": str(organization_id),
        "role": role,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )


def encrypt_secret(data: Dict[str, Any] | str) -> str:
    """Encrypt secret configuration or API credentials using Fernet AES-128-CBC + HMAC."""
    raw_str = json.dumps(data) if isinstance(data, dict) else str(data)
    return _fernet.encrypt(raw_str.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> Dict[str, Any] | str:
    """Decrypt Fernet-encrypted credentials stored at rest."""
    if not ciphertext:
        return {}
    try:
        decrypted = _fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        try:
            return json.loads(decrypted)
        except json.JSONDecodeError:
            return decrypted
    except InvalidToken:
        return {}


def redact_sensitive_data(data: Any) -> Any:
    """Recursively redact sensitive keys from dictionaries or lists before logging/returning."""
    if isinstance(data, dict):
        redacted = {}
        for k, v in data.items():
            if any(s in k.lower() for s in SENSITIVE_KEYS):
                redacted[k] = "***REDACTED***"
            else:
                redacted[k] = redact_sensitive_data(v)
        return redacted
    elif isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]
    return data


def detect_prompt_injection(text: str) -> Optional[str]:
    """Check user input or tool output for known prompt injection / destructive SQL patterns."""
    if not text:
        return None
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(text):
            return f"Blocked potential prompt/command injection matching pattern: {pattern.pattern}"
    return None


def sanitize_untrusted_tool_output(output: Any) -> Any:
    """Wrap and sanitize untrusted MCP tool outputs so embedded instructions are neutralized."""
    if isinstance(output, str):
        cleaned = re.sub(
            r"(?i)(ignore\s+previous\s+instructions|system\s+override)",
            "[SANITIZED_UNTRUSTED_TEXT]",
            output,
        )
        return cleaned
    if isinstance(output, dict):
        return {k: sanitize_untrusted_tool_output(v) for k, v in output.items()}
    if isinstance(output, list):
        return [sanitize_untrusted_tool_output(v) for v in output]
    return output

