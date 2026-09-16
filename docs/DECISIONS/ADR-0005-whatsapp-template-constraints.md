# ADR 0005: WhatsApp Template Constraints

## Status
Accepted

## Context
Sending gallery links via Meta's WhatsApp Cloud API requires using pre-approved template messages for outbound, user-initiated communications (utility templates). The URL button in these templates must be a fixed base URL with a variable suffix.

## Decision
Magic links will be formatted as `https://snaptracer.devs.surf/g/{token}` to comply with Meta's template constraints. We will treat template rejection as a first-class failure state and fall back to email, and we will properly store user consent.
