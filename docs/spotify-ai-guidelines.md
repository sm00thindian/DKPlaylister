# Spotify Web API + AI Development Guidelines

This document follows Spotify's official recommendations for building with AI (as of 2026).

Source: https://developer.spotify.com/documentation/web-api/tutorials/building-with-ai

## Official OpenAPI Specification

Always refer to the official machine-readable spec when working with endpoints:

**https://developer.spotify.com/reference/web-api/open-api-schema.yaml**

## Recommended System Prompt for AI Assistants

When asking Grok (or any LLM) to generate Spotify-related code, use the following prompt (adapted from Spotify's official guidance):

---

You are helping me build an application using the Spotify Web API. Follow these rules:

- OpenAPI spec: Refer to the Spotify OpenAPI specification at https://developer.spotify.com/reference/web-api/open-api-schema.yaml for all endpoint paths, parameters, and response schemas. Do not guess endpoints or field names.

- Authorization: Use the Authorization Code with PKCE flow for any user-specific data. If the app has a secure backend, the Authorization Code flow is also acceptable. Only use Client Credentials for public, non-user data. Never use the Implicit Grant flow (it is deprecated).

- Redirect URIs: Always use HTTPS redirect URIs (except http://127.0.0.1 for local development). Never use http://localhost or wildcard URIs.

- Scopes: Request only the minimum scopes needed for the features being built. Do not request broad scopes preemptively.

- Token management: Store tokens securely. Never expose the Client Secret in client-side code. Implement token refresh logic so the app does not break when access tokens expire.

- Rate limits: Implement exponential backoff and respect the Retry-After header when receiving HTTP 429 responses. Do not retry immediately or in tight loops.

- Deprecated endpoints: Do not use deprecated endpoints. Prefer `/playlists/{id}/items` over `/playlists/{id}/tracks`, and use `/me/library` over the type-specific library endpoints.

- Error handling: Handle all HTTP error codes documented in the OpenAPI schema. Read the returned error message and use it to provide meaningful feedback to the user.

- Developer Terms of Service: Comply with the Spotify Developer Terms. In particular: do not cache Spotify content beyond what is needed for immediate use, always attribute content to Spotify, and do not use the API to train machine learning models on Spotify data.

---

## Current DKPlaylister Usage (as of now)

- We are primarily using **Client Credentials** flow (correct for public playlist data).
- Main endpoint in use: `GET /playlists/{id}` (still supported).
- Authorization Code Flow is now active via `get_user_client()` / `get_oauth_client()`.
- Use `dkplaylister auth spotify` (or `dkplaylister auth spotify --status`) to manage login.
- Registered redirect URI: `http://127.0.0.1:8888/callback`
- Recommended way to get an authenticated client: `from dkplaylister.spotify import get_user_client`

## Review Checklist (from Spotify)

Before shipping Spotify-related code, verify:

- [x] Using the correct OAuth flow (Authorization Code Flow available via `get_user_client()`)
- [ ] Redirect URIs are correct (HTTPS or 127.0.0.1)
- [ ] Minimum necessary scopes
- [ ] Proper token storage & refresh
- [ ] Rate limit handling with exponential backoff
- [ ] No deprecated endpoints
- [ ] Good error handling
- [ ] Compliance with Developer Terms

## Next Steps

- When generating new Spotify code, paste the recommended prompt above.
- For complex features, feed the OpenAPI schema URL to the model.
- Regularly check the [February 2026 Migration Guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide) for breaking changes.
