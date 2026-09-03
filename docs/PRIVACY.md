# Privacy Model & PrivacyShield Engine

Neural Memory handles sensitive personal context. Its privacy architecture is built around **strict local-first isolation, proactive client-side redaction, and granular user consent**.

---

## 1. Core Privacy Guarantees

- **Zero Outbound Data by Default**:
  - In base mode, no data ever leaves your computer. The API binds strictly to `127.0.0.1`.
  - In Standalone mode, all data is stored inside a local SQLite property graph at:
    `~/Library/Application Support/NeuralMemory/memory.db`.
  - Even when LLM enrichment is enabled (`LLM_ENABLED=true`), all sensitive credentials and identifiers are redacted locally *before* transmission.
- **Granular Independent Opt-Ins**:
  - Activity monitoring (app/window focus), screenshot capture, and keystroke buffer capture require separate, explicit toggles in Settings.
  - On a fresh installation, all capture engines start **disabled**.
- **Ephemeral Data Pruning (Dream Mode)**:
  - Raw keyboard, mouse, and window events are automatically pruned after 48 hours (configurable retention period).
  - Only durable semantic knowledge nodes (`Decision`, `Commitment`, `Meeting`, `Reflection`) persist in long-term memory.

---

## 2. PrivacyShield Redaction Pipeline

Every interaction bundle ingested by Neural Memory is processed by the local **`PrivacyShield`** service (`server/src/kg_mcp/services/privacy_shield.py`) before storage or LLM vision processing.

### 2.1 Application & Window Deny-List
Neural Memory instantly drops and suppresses any capture originating from sensitive contexts:
- **Password Managers & Vaults**: `1Password`, `Bitwarden`, `Apple Keychain Access`, `KeePassXC`, `Enpass`.
- **Private Browsing**: Window titles containing `"Incognito"`, `"InPrivate"`, or `"Private Browsing"`.
- **Financial Applications**: Banking portals, payment processors, and crypto wallets.

### 2.2 Proactive In-Memory Redaction
Typed text and contextual strings are scrubbed via dedicated heuristic and cryptographic validators:

| Sensitive Pattern | Validation Method | Replacement Mask |
| :--- | :--- | :--- |
| **Credit Card Numbers** | Regex pattern matching + **Luhn Algorithm** mathematical checksum validation | `[REDACTED_CREDIT_CARD]` |
| **IBAN Numbers** | ISO 13616 international standard validation | `[REDACTED_IBAN]` |
| **OpenAI API Keys** | `sk-[a-zA-Z0-9]{32,64}` | `[REDACTED_API_KEY]` |
| **Google Gemini API Keys** | `AIza[0-9A-Za-z-_]{30,45}` | `[REDACTED_API_KEY]` |
| **GitHub Tokens** | `gh[pousr]_[0-9A-Za-z]{36}` | `[REDACTED_API_KEY]` |
| **Generic Bearer Tokens** | `Bearer [A-Za-z0-9_-]{20,}` | `Bearer [REDACTED]` |
| **Passwords / PINs** | Contextual field heuristics (`password=...`, `pin=...`) | `[REDACTED_CREDENTIAL]` |

---

## 3. Storage & Cryptographic Tokens

- **Loopback Isolation**: The HTTP API binds only to `127.0.0.1:8765`. It cannot be reached across local network subnets or Wi-Fi.
- **Bearer Token**: Access to all mutation and private query endpoints requires a 256-bit cryptographically secure token.
  - In Standalone mode: Persisted in `~/Library/Application Support/NeuralMemory/token.txt` with `0600` permissions.
  - In macOS UI app: Stored in the secure system **macOS Keychain**.
- **Screenshot Transient Storage**: Raw screenshot bitmap pixels are never persisted into the graph database. They are processed in memory for perceptual visual hashing (`dhash`) to eliminate duplicates and immediately discarded.

---

## 4. User Controls & Best Practices

1. **Pause / Private Mode**: Available directly from the macOS Menu Bar. One click pauses all contextual observation while you handle personal matters.
2. **Database Wipe**:
   - To completely erase the standalone database:
     ```bash
     rm -f ~/Library/Application\ Support/NeuralMemory/memory.db*
     ```
   - To erase the Docker database:
     ```bash
     docker compose down -v
     ```
3. **Never Share Your Token**: Treat `token.txt` and `.env` as sensitive credentials. Do not commit them to version control.
