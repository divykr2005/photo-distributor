# ADR 0004: httpOnly Cookies for Authentication

## Status
Accepted

## Context
localStorage was originally used for JWTs. Since the API (`api.snaptracer.devs.surf`) and the frontend (`snaptracer.devs.surf`) share a parent domain, using localStorage offers no CORS benefits and exposes tokens to XSS attacks.

## Decision
We will use httpOnly cookies scoped to `Domain=.snaptracer.devs.surf; Secure; SameSite=Lax`. This provides immunity to XSS while requiring zero CORS gymnastics. We accept the tradeoff of needing CSRF protection (double-submit token) for state-changing routes.
