"""
PrivacyShield - Local security and redaction filter.
Protects sensitive personal credentials, financial information, and private windows before LLM ingestion.
"""
import re
from typing import Optional


class PrivacyShield:
    """Detects and redacts sensitive data and identifies private application contexts."""

    # Sensitive apps that should never be captured or analyzed
    SENSITIVE_APPS = {
        "1password",
        "bitwarden",
        "keychain access",
        "lastpass",
        "keepass",
        "keepassxc",
        "authy",
        "authenticator",
    }

    # Sensitive window title patterns (e.g. incognito, banking, login)
    SENSITIVE_WINDOW_PATTERNS = [
        re.compile(r"incognito", re.IGNORECASE),
        re.compile(r"inprivate", re.IGNORECASE),
        re.compile(r"private browsing", re.IGNORECASE),
        re.compile(r"bank|banking|banca|sanpaolo|unicredit|poste|paypal|conto corrente", re.IGNORECASE),
        re.compile(r"password|master password|two-factor|2fa|otp|credential", re.IGNORECASE),
    ]

    # API keys, tokens, and secret patterns
    SECRET_PATTERNS = [
        (re.compile(r"(sk-[A-Za-z0-9_-]{20,})"), "[REDACTED_API_KEY]"),
        (re.compile(r"(AIza[0-9A-Za-z_-]{35})"), "[REDACTED_GEMINI_KEY]"),
        (re.compile(r"(ghp_[A-Za-z0-9]{36})"), "[REDACTED_GITHUB_TOKEN]"),
        (re.compile(r"(Bearer\s+[A-Za-z0-9_\-\.]{20,})", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
        (re.compile(r"(password[\s:=]+)[^\s,;]{4,}", re.IGNORECASE), r"\1[REDACTED_PASSWORD]"),
    ]

    # IBAN Pattern (international)
    IBAN_PATTERN = re.compile(r"\b([A-Z]{2}\d{2}[A-Z0-9]{11,30})\b")

    # Credit Card Pattern (13 to 19 digits)
    CC_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,19}\b")

    @classmethod
    def is_sensitive_context(cls, app: str, window_title: Optional[str] = None) -> bool:
        """Return True if the active app or window is strictly private."""
        app_clean = (app or "").strip().lower()
        if app_clean in cls.SENSITIVE_APPS:
            return True

        title_clean = (window_title or "").strip()
        for pattern in cls.SENSITIVE_WINDOW_PATTERNS:
            if pattern.search(title_clean):
                return True

        return False

    @classmethod
    def mask_secrets(cls, text: str) -> str:
        """Redact known API keys, tokens, and password values."""
        if not text:
            return ""
        result = text
        for pattern, replacement in cls.SECRET_PATTERNS:
            result = pattern.sub(replacement, result)
        return result

    @classmethod
    def mask_ibans(cls, text: str) -> str:
        """Redact IBAN bank account numbers."""
        if not text:
            return ""
        return cls.IBAN_PATTERN.sub("[REDACTED_IBAN]", text)

    @classmethod
    def _is_luhn_valid(cls, card_digits: str) -> bool:
        """Verify credit card number validity via Luhn algorithm."""
        digits = [int(d) for d in card_digits if d.isdigit()]
        if len(digits) < 13 or len(digits) > 19:
            return False
        total = 0
        reverse_digits = digits[::-1]
        for idx, digit in enumerate(reverse_digits):
            if idx % 2 == 1:
                doubled = digit * 2
                total += doubled - 9 if doubled > 9 else doubled
            else:
                total += digit
        return total % 10 == 0

    @classmethod
    def mask_credit_cards(cls, text: str) -> str:
        """Redact valid credit card numbers."""
        if not text:
            return ""

        def replace_cc(match):
            raw = match.group(0)
            digits = re.sub(r"\D", "", raw)
            if 13 <= len(digits) <= 19 and cls._is_luhn_valid(digits):
                return "[REDACTED_PAYMENT_CARD]"
            return raw

        return cls.CC_PATTERN.sub(replace_cc, text)

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """Run complete sanitization pipeline on any user or screen text."""
        if not text:
            return ""
        sanitized = cls.mask_secrets(text)
        sanitized = cls.mask_ibans(sanitized)
        sanitized = cls.mask_credit_cards(sanitized)
        return sanitized
