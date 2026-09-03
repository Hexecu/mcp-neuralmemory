# Privacy model

Neural Memory can handle unusually sensitive data. Its defaults are intentionally conservative.

## Default behavior

- Fresh macOS and browser installs do not capture activity.
- Screenshot capture and typed-text capture require separate opt-in on macOS.
- LLM enrichment is disabled.
- The API, Neo4j Browser and Neo4j Bolt ports bind to `127.0.0.1`.
- Private API routes reject requests without the generated bearer token.
- The macOS client stores that token in the user's Keychain, not in UserDefaults.
- Request and field size limits are enforced before storage or enrichment.

## What is stored

Enabled clients may store application names, window titles, browser page titles, sanitized browser URLs and opted-in typed text as graph events. Screenshot pixels are not persisted by the ingestion API. A perceptual hash may be stored to suppress duplicate captures.

Neo4j data is held in the `neo4j_data` Docker volume. `docker compose down` preserves it.

## What may leave the machine

Nothing is sent to an LLM while `LLM_ENABLED=false`. When you enable enrichment, opted-in text and screenshots may be sent to the provider configured in `.env`. That provider's retention and training policies then apply.

The enrichment prompt instructs the model to omit credentials, form values, personal messages and email addresses. This is a defense in depth measure, not a guarantee. Do not enable capture in apps or sessions that contain secrets.

## Practical controls

- Keep capture disabled until the local server and token are configured.
- Use Private Mode or Pause Capture before opening sensitive material.
- Leave typed text and screenshots disabled unless they add clear value.
- Never commit `.env` or share its API token.
- Treat exported graph data as sensitive and encrypt backups.

Future releases should add application deny lists, retention rules and first-class graph deletion/export controls before the clients are described as stable.
