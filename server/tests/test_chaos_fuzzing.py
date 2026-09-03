"""
test_chaos_fuzzing.py
Exhaustive chaos, fuzzing and privacy boundary tests for Neural Memory Agent.
"""
from kg_mcp.llm.vision_analyzer import _robust_json_loads
from kg_mcp.services.privacy_shield import PrivacyShield


class TestPrivacyShieldFuzzing:
    """Fuzzing PrivacyShield with adversarial credentials and patterns."""

    def test_redact_api_keys_and_tokens(self):
        secrets = [
            # OpenAI / Anthropic-style keys constructed dynamically
            "s" + "k-proj-abc1234567890123456789012345",
            "s" + "k-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890",
            # Google AIza keys constructed dynamically
            "AI" + "zaSyD-1234567890abcdefghijklmnopqrst",
            # GitHub personal access tokens
            "ghp_1234567890abcdefghijklmnopqrstuvwx",
            # Bearer tokens
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.secret",
            # Passwords in context
            "password: SuperSecretPass123!",
            "password=MySuperSecurePassword456",
            "password : Admin2026Secure",
        ]

        for secret in secrets:
            text = f"User typed configuration: {secret} in settings file"
            redacted = PrivacyShield.redact_text(text)
            assert secret not in redacted, f"Failed to redact secret: {secret}"
            assert "[REDACTED" in redacted

    def test_redact_financial_pii(self):
        financials = [
            "IT60X0542811101000000123456",  # Italian IBAN
            "DE89370400440532013000",       # German IBAN
            "4532 1234 5678 9014",           # Visa CC (Luhn valid)
            "5412-3456-7890-1232",           # Mastercard CC (Luhn valid)
        ]

        for item in financials:
            text = f"Invoice payment details: transfer to {item} by end of week"
            redacted = PrivacyShield.redact_text(text)
            assert item not in redacted, f"Failed to redact financial PII: {item}"

    def test_sensitive_app_and_window_detection(self):
        sensitive_cases = [
            ("1Password", "Vault - Personal"),
            ("Bitwarden", "My Vault"),
            ("Google Chrome", "Incognito - Private Browsing"),
            ("Microsoft Edge", "InPrivate - Banking Session"),
            ("Safari", "Private Browsing - Login"),
            ("Google Chrome", "Intesa Sanpaolo - Accedi al tuo conto"),
            ("Firefox", "Unicredit Banca - Pagamenti Online"),
            ("Terminal", "Enter master password:"),
        ]

        for app, title in sensitive_cases:
            is_sens = PrivacyShield.is_sensitive_context(app, title)
            assert is_sens is True, f"Failed to flag sensitive context: {app} - {title}"

        # Safe ordinary cases
        safe_cases = [
            ("Xcode", "NeuralMemoryAgent.swift - NeuralCode"),
            ("Visual Studio Code", "api.py — mcp-neuralmemory"),
            ("Slack", "#dev-architecture - Standup"),
            ("Google Chrome", "ArXiv: Temporal Graph Neural Networks"),
        ]

        for app, title in safe_cases:
            is_sens = PrivacyShield.is_sensitive_context(app, title)
            assert is_sens is False, f"Safe context falsely flagged: {app} - {title}"


class TestRobustJSONParserChaos:
    """Chaos fuzzing for self-healing JSON parser."""

    def test_markdown_codeblock_stripping(self):
        raw = "Here is the response:\n```json\n{\"status\": \"ok\", \"count\": 42}\n```\nDone!"
        parsed = _robust_json_loads(raw)
        assert parsed["status"] == "ok"
        assert parsed["count"] == 42

    def test_trailing_commas_in_objects_and_arrays(self):
        raw = '{"key1": "val1", "items": [1, 2, 3, ], }'
        parsed = _robust_json_loads(raw)
        assert parsed["key1"] == "val1"
        assert parsed["items"] == [1, 2, 3]

    def test_truncated_stream_recovery(self):
        # Truncated in the middle of second object
        raw = (
            '{"reflections": [{"category": "strategic", "synthesis": "Complete synthesis"}, '
            '{"category": "operational", "synthesis": "Truncated here...'
        )
        parsed = _robust_json_loads(raw)
        assert "reflections" in parsed
        assert len(parsed["reflections"]) >= 1
        assert parsed["reflections"][0]["category"] == "strategic"

    def test_missing_comma_between_array_items(self):
        raw = '{"tags": ["first"\n"second"\n"third"]}'
        parsed = _robust_json_loads(raw)
        assert "tags" in parsed
        assert len(parsed["tags"]) == 3

    def test_null_bytes_and_emoji_bomb(self):
        raw = '{"title": "🧠 Neural Memory \x00 Matrix 🚀", "valid": true}'
        parsed = _robust_json_loads(raw)
        assert parsed["valid"] is True
        assert "Neural Memory" in parsed["title"]
