## Verdict first

Four decisions, made:

**Reverse proxy → Caddy.** You already have a Caddyfile, you have exactly two hostnames, and your bottleneck is your own time, not proxy expressiveness. Traefik's advantage is label-driven discovery for fleets of dynamic services; you have six static containers. Caddy gets you correct TLS, HTTP/2+3, and sane defaults in about fifteen lines. The one thing Caddy doesn't ship in-tree is rate limiting — and that's fine, because your abuse surfaces (magic-link issuance, selfie upload) need per-identity limits that belong in FastAPI anyway, not at the edge. The tiebreaker: if you ever sell vanity gallery domains to organisers, Caddy's `on_demand_tls` does that in three lines and Traefik makes it a project.

**Session persistence → httpOnly cookies, single origin.** Not localStorage, and not two origins. Serve the Next.js app *from the VM behind Caddy* and proxy `/api/*` to FastAPI, so cookies are host-only and CORS disappears entirely. This is a bigger simplification than it sounds and it kills a whole category of bugs you'd otherwise debug at 2am.

**Delivery channels → email + WhatsApp only, behind one provider protocol.** Delete the console/webhook/SMS stubs rather than flag them; unlike the AI tools, they have no product option value.

**14-day purge → yes, but build it *last*, after you can restore.** An auto-deleter you ship before a tested restore path is a data-loss incident with a cron schedule.

And one correction to your own plan: the AI-tools flag call is right, keep it. But "dark glass" is itself the single most AI-generated-looking aesthetic on the internet right now. Section 7 below is about how to use it without landing in that valley.

---

## Phase ordering and why

```
P0  Agent scaffolding ─┐
P1  Config / URL truth ─┼─→ prerequisites for everything
P2  Deploy topology (Caddy, local broker, host hardening)
                        │
P3  Persistent sessions ┤ depends on P1 (URL truth) + P2 (single origin)
P4  Notification abstraction → WhatsApp   depends on P1 (token path format)
P5  ZIP delivery hardening                depends on P4 (send channel)
P6  UI cleanup behind flags               independent, cheap, do while P4 template is in Meta review
P7  Design system pass                    depends on P6
P8  Operability + restore drill           depends on P2
P9  Retention, auto-purge, consent        depends on P8 (never before)
P10 Matching path consolidation           independent, defer
```

The non-obvious edge: **P1 must precede P4**, because the WhatsApp template's URL button registers a fixed base with one variable suffix. Your magic link has to be `https://snaptracer.devs.surf/g/{token}` *before* you submit the template, or you'll submit twice and wait through review twice.

---

## Phase 0 — Agent scaffolding

Half a day, zero product change, and it makes every later phase two to three times more reliable. Your current document fails as an agent input for five mechanical reasons: no file paths, no acceptance criteria, current state interleaved with target state, alphabetical rather than dependency ordering, and no invariants. This phase fixes the substrate.

Create `CLAUDE.md` at repo root containing the repo map, the exact dev/test/deploy commands, and an invariant list. The invariants are the highest-leverage 200 words in the project:

```markdown
## Invariants — violating any of these fails review

- NEVER edit `.env`, `.env.production`, or anything in `secrets/`. Edit `.env.example` only.
- Every SQLAlchemy model change REQUIRES an Alembic revision in the same commit.
  `alembic revision --autogenerate` then hand-review the generated file.
- NEVER widen a Caddy site block or add a new published port without an explicit task.
- NEVER add a third notification channel. Email and WhatsApp only.
- NEVER construct a URL from a literal `http://` or `localhost`. Use `settings.FRONTEND_URL`.
- Data-destructive code (DELETE, purge, migration DROP) must be gated by a
  `DRY_RUN` default of True and covered by a test using freezegun.
- No task may touch both `backend/` and `frontend/` unless it is an OpenAPI
  contract change, in which case the schema is a separate prior task.
- Tests never touch Neon. Use `docker compose -f docker-compose.test.yml`.
```

Then `docs/ARCHITECTURE.md` with present-tense truth only and no plans in it; one ADR file per decision in `docs/DECISIONS/` (start with the four at the top of this document — proxy choice, cookie auth, channel restriction, retention model); `docs/plan/ROADMAP.md` as the phase index; and `docs/plan/tasks.yaml` as the machine-readable manifest.

Ship the tooling that makes verification possible: a `Makefile` with `up`, `down`, `logs`, `test`, `migrate`, `deploy`; `pre-commit` running ruff and mypy on `backend/` plus eslint and `tsc --noEmit` on `frontend/`; and `docker-compose.test.yml` spinning `pgvector/pgvector:pg16` and `redis:7-alpine` locally.

Exit gate: `make test` passes on a clean clone with no external credentials present.

---

## Phase 1 — Configuration contract and one source of URL truth

Your `localhost:3000` in production magic links is not an SSL problem. It's a config problem: URLs are being built from defaults instead of validated settings, so the failure is silent. Make it loud.

```python
# backend/app/core/config.py
from typing import Literal
from pydantic import AnyHttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="forbid")

    ENVIRONMENT: Literal["dev", "staging", "prod"]
    PUBLIC_BASE_URL: AnyHttpUrl          # no default. e.g. https://snaptracer.devs.surf
    MAGIC_LINK_TTL_MINUTES: int = 60
    GUEST_LINK_PATH: str = "/g"          # must match the approved WhatsApp template
    DEFAULT_RETENTION_DAYS: int = 14

    @model_validator(mode="after")
    def _no_localhost_in_prod(self):
        if self.ENVIRONMENT == "prod" and any(
            h in str(self.PUBLIC_BASE_URL) for h in ("localhost", "127.0.0.1", "0.0.0.0")
        ):
            raise ValueError(f"localhost URL in prod: {self.PUBLIC_BASE_URL}")
        return self

settings = Settings()  # fails fast at import
```

Note there's now *one* URL, not a frontend and an API URL, because Phase 2 collapses you to a single origin. Then grep for every hardcoded scheme and route it through settings:

```bash
rg -n "http://|https://|localhost" backend/app --glob '!**/tests/**'
```

The second half of this phase is the token refactor that unblocks WhatsApp. Magic links must become path tokens, not query strings, because a WhatsApp template URL button is a fixed base plus one variable suffix — you cannot pass `?token=x&event=y`.

```
### T-0103 · Path-safe guest tokens
Files:
  backend/app/services/magic_link.py        (modify)
  backend/app/api/v1/guest.py               (modify)
  frontend/app/g/[token]/page.tsx           (create)
  frontend/app/gallery/page.tsx             (delete after redirect shim)
Do:
  1. Token = secrets.token_urlsafe(32), stored as SHA-256 hash, never plaintext.
  2. Builder returns f"{settings.PUBLIC_BASE_URL}{settings.GUEST_LINK_PATH}/{token}".
  3. Single-use-optional: allow N views within TTL, record last_viewed_at.
  4. Keep a 30-day redirect shim from any old query-string form.
Verify:
  $ pytest backend/tests/test_magic_link.py -k path_format
  Expect: asserts regex ^https://snaptracer\.devs\.surf/g/[A-Za-z0-9_-]{43}$
```

Add a startup log line printing the resolved public URL so a misconfiguration is visible in the first ten lines of `docker compose logs`.

Exit gate: booting with `ENVIRONMENT=prod` and a localhost base URL crashes at import; a test asserts the emitted link matches the production regex above.

---

## Phase 2 — Deployment topology: Caddy, single origin, local broker, host hardening

This is the phase that turns "localhost only" into "live on snaptracer.devs.surf."

**Topology decision.** Drop the Cloudflare Pages target for now and serve Next.js from the VM. One origin means host-only cookies, no CORS config, no preflight latency, and no `allow_credentials` footguns. You can still put Cloudflare in front as a proxying CDN later — but if you do, know that the free plan caps request bodies at 100 MB, which will silently break bulk photo upload. The right answer regardless is presigned direct-to-R2 uploads, which sidesteps both your proxy and Cloudflare's limit.

**Caddyfile.** Keep it boring:

```caddy
{
    email you@example.com
    # first run only — avoids burning LE rate limits on a misconfig
    # acme_ca https://acme-staging-v02.api.letsencrypt.org/directory
}

snaptracer.devs.surf {
    encode zstd gzip

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options    "nosniff"
        Referrer-Policy           "strict-origin-when-cross-origin"
        X-Frame-Options           "DENY"
        -Server
    }

    # API — no compression on already-compressed archives, stream immediately
    handle /api/* {
        reverse_proxy api:8000 {
            flush_interval -1
            header_up X-Forwarded-Proto {scheme}
        }
    }

    handle /healthz { reverse_proxy api:8000 }

    handle {
        reverse_proxy web:3000
    }
}
```

`flush_interval -1` disables response buffering, which matters for SSE/progress streams on your ZIP jobs. Do not add a `:8080` dashboard equivalent; Caddy has an admin API on `localhost:2019` — leave it unpublished and reach it over `ssh -L`.

**Move the Celery broker onto the box.** Upstash as a Celery broker is the largest operational risk in your current design. Celery's Redis transport does blocking `BRPOP` long-polls plus mingle/gossip/heartbeat chatter, so a mostly-idle system still generates millions of per-request-billed commands, and serverless Redis closes idle TCP connections, which surfaces as phantom `ConnectionResetError` and lost tasks. Your broker traffic never leaves the VM — there's no reason to pay for it to make a round trip. A local `redis:7-alpine` is roughly 40 MB RSS. Keep Upstash only if you want a cache that survives VM rebuilds.

If you insist on staying remote, the minimum viable config is:

```python
broker_transport_options = {
    "visibility_timeout": 3600,       # must exceed your longest task or tasks duplicate
    "socket_keepalive": True,
    "health_check_interval": 30,
}
broker_connection_retry_on_startup = True
worker_send_task_events = False
```

plus `--without-gossip --without-mingle --without-heartbeat` on every worker. Watch connection count too: a prefork worker at concurrency N holds roughly N+2 connections, and three workers plus Flower plus the API will blow a free-tier cap.

**Split Beat out of the worker container** now, at single replica. The moment anyone sets `replicas: 2` on a worker that also runs Beat, every maintenance task fires twice — and in Phase 9 one of those maintenance tasks deletes customer data.

**Pin ONNX threads.** Each prefork child loads its own `buffalo_l` sessions (~330 MB), and ONNX Runtime defaults to one thread per core per session, so 4 OCPUs × 2 forks is pure thrash on ARM:

```yaml
face-worker:
  environment:
    OMP_NUM_THREADS: "2"
    ORT_INTRA_OP_NUM_THREADS: "2"
    OPENBLAS_NUM_THREADS: "1"
  command: >
    celery -A app.worker worker -Q faces -P prefork -c 1
    --max-tasks-per-child 50 --without-gossip --without-mingle
  logging:
    driver: json-file
    options: { max-size: "10m", max-file: "3" }
```

`--max-tasks-per-child` bounds the RSS creep ONNX and PIL reliably produce. Also try `det_size=(480,480)` instead of 640 — event photos have large faces and the throughput gain is real, but measure recall on your own data before committing.

**Two host-level items that are pure insurance.** Docker's default `json-file` driver is unbounded, and on a 45 GB disk already half full, one chatty worker fills it and takes down Postgres connections, Caddy, and comfortable SSH access — so the `logging` block above goes on *every* service, no exceptions. And add 4 GB of swap; you have 24 GB free disk and a 2.4 GB-capped inference worker, so this is the cheapest OOM-killer protection available.

**The Oracle gotcha that costs people an afternoon.** Oracle's Ubuntu images ship iptables rules dropping everything except 22, *in addition to* the VCN security list. ACME HTTP-01 fails silently until both are fixed. Put this verbatim in the phase doc:

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80  -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

Also split your port table in two. Ports 5432 and 6379 are *egress dependencies*, not listeners; listing them under "Network Ports & Routing" alongside real bind ports is precisely the ambiguity that makes an agent try to publish them.

Exit gate: `curl -I https://snaptracer.devs.surf/healthz` returns 200 with a valid cert and HSTS present; `curl http://...` redirects to https; port 8000 is unreachable from outside the VM; `docker compose ps` shows Beat as its own single-replica service.

---

## Phase 3 — Persistent sessions

With a single origin, this gets simple. Access token, 15 minutes, `httpOnly; Secure; SameSite=Lax; Path=/`, host-only (do *not* set a `Domain` attribute, and never scope to `.devs.surf`). Refresh token, 30 days, `httpOnly`, `Path=/api/v1/auth/refresh`, with rotation and reuse detection — store a hash plus a family ID, and on replay of an already-used refresh token, revoke the entire family and force re-login. That's your session-theft tripwire.

Endpoints: `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout` (clears both cookies and revokes the family), `GET /api/v1/auth/me` for boot hydration. Frontend gets one fetch wrapper that on a 401 calls refresh exactly once, deduplicates concurrent refreshes through a single in-flight promise, and on refresh failure redirects to login.

Be honest in the ADR about the cost: cookies mean you own CSRF. `SameSite=Lax` covers the common cases; add a double-submit token on state-changing routes for defence in depth. It also complicates any future native mobile client — when that day comes, add a separate bearer-token path for `/api/v1/mobile/*` rather than weakening the web session.

Guest sessions are a separate, weaker thing: the magic-link token exchanges for a short-lived, event-scoped guest cookie with no account privileges. Don't reuse the organiser session machinery.

Exit gate: hard refresh preserves the session; deleting the cookie logs out; an expired access token silently refreshes exactly once (assert one network call, not N); replaying a consumed refresh token returns 401 and kills the family. Playwright covers all four.

---

## Phase 4 — Notification abstraction, then WhatsApp

Split into two sub-phases and do not let the agent merge them.

**4a — the abstraction.** Define the protocol, migrate email onto it, delete the console, webhook, and Twilio SMS stubs, and add the delivery ledger that makes everything afterwards debuggable.

```python
# backend/app/services/notifications/base.py
class NotificationProvider(Protocol):
    channel: Literal["email", "whatsapp"]
    async def send(self, to: str, template: str, params: dict) -> DeliveryReceipt: ...
```

New table `notification_deliveries`: guest_id, event_id, channel, template_name, provider_message_id, status enum (`queued|sent|delivered|read|failed|rejected`), attempts, last_error, and timestamps. Without this you cannot answer "did Priya get her link?", which is the single most common support question a photo-distribution product receives.

**4b — Meta WhatsApp Cloud API.** Order matters here for a boring reason: template review takes days and can reject, so submit on day one of the phase and build the rest while you wait.

Your plan currently understates the constraints. Outside the 24-hour customer service window — which only opens when the *guest* messages you first, which they never will — you can send only pre-approved templates. So every send you make is a template send, and the work item isn't "call the API," it's "author, submit, get approved, and handle rejection." Meta moved to per-delivered-message pricing on 1 July 2025 (utility templates inside an open service window are free), and further pricing changes have been rolling through 2026 including a tranche dated 1 October 2026 — so pull the live rate card for your actual recipient countries rather than trusting any number in a planning doc. For an India-heavy audience utility rates make this clearly worth it; for US/EU recipients the margin over email is thin enough that email-first with WhatsApp as opt-in is the better default.

Template shape, matching the Phase 1 token format exactly:

```
Name:     gallery_ready_v1
Category: UTILITY
Language: en
Body:     Hi {{1}}, your photos from {{2}} are ready.
          Tap below to view and download.
Button:   URL (dynamic) → https://snaptracer.devs.surf/g/{{1}}
Footer:   Reply STOP to opt out.
```

Then build: `MetaWhatsAppProvider` in `backend/app/services/notifications/whatsapp.py`; E.164 normalisation via the `phonenumbers` library with the event's country as the default region; a `POST /api/v1/webhooks/whatsapp` endpoint that verifies `X-Hub-Signature-256` before parsing and flips ledger rows to delivered/read; persistence of `wamid` for reconciliation; per-recipient throttling; template rejection treated as a first-class failure state that automatically falls back to email; and STOP-keyword handling that writes an opt-out.

Consent is not a boolean. Meta requires demonstrable opt-in, so store `whatsapp_consent_at`, `consent_source`, and `consent_text_version` per guest, with the actual consent text archived by version. An unconsented guest should return 409, not send.

Exit gate: a real message lands on a test handset; the webhook advances the ledger row to `read`; an unconsented guest returns 409; email fallback fires when the WhatsApp call is mocked to fail; a `STOP` inbound sets opt-out and subsequent sends 409.

---

## Phase 5 — ZIP delivery hardening

Your ZIP workers work. What isn't production-safe yet is the *delivery* of the artifact. Do not stream a 2 GB archive through Caddy from a Python worker — you'll hold a proxy connection for minutes, break on mobile network flaps, and have no resume.

The pattern: `POST /api/v1/galleries/{id}/archive` returns 202 with a job ID; the worker builds the ZIP straight to R2 using multipart upload with a streaming writer (never buffer the whole archive in the 6 GB of RAM you're sharing with inference); the client polls `GET /api/v1/jobs/{id}` or subscribes to SSE for progress; on completion the API issues a presigned R2 URL with a short TTL (15 minutes) and the client downloads direct from R2. Your VM never touches the bytes on the way out, and R2 has no egress fee.

Additions worth doing in the same pass: content-hash deduplication so an identical archive request returns the existing object instead of rebuilding; an R2 lifecycle rule expiring `archives/` objects after 48 hours since they're regenerable; and `Content-Disposition` with a filename derived from the event name so guests don't get `download.zip`.

Exit gate: a 1.5 GB archive completes with worker RSS staying under 400 MB throughout; the presigned URL 403s after its TTL; two identical requests produce one R2 object.

---

## Phase 6 — UI cleanup behind flags

This is the phase your original document opened with, and it's cheap — run it while the WhatsApp template sits in review.

Your instinct to flag rather than delete Group Duplicates and Rank Photo Quality is correct, and it matches WEEK2_PLAN. Wrap the card in `process.env.NEXT_PUBLIC_FEATURE_EXPERIMENTAL_AI === 'true'`, keep the Celery tasks registered but unrouted from the UI, and put a calendar reminder to revisit deletion after 60 days of non-use. Deletion destroys optionality; a flag costs one line. One caveat: `NEXT_PUBLIC_*` is inlined at build time, not runtime, so flipping it requires a rebuild — if you want runtime toggling, read it server-side and pass it down through a layout.

The channel removal in `NotifyGuestsModal.tsx` is different and should be a real deletion, since Phase 4a already removed the backing providers — leaving dead channel options in the UI would just create a broken path. Remove console, webhook, and twilio_sms, keep smtp and twilio_whatsapp (rename the latter's identifier to `whatsapp` since it's Meta Cloud API now, not Twilio — leaving the old name is exactly the kind of lie in the codebase that costs someone an hour in six months). Update the test-notification input's placeholder and validation to switch on channel: email format for email, E.164 for WhatsApp.

The Sidebar's "Week 1 Build / Registration & Infrastructure" block goes away entirely. Build-phase scaffolding visible to users is the strongest possible signal that a product isn't finished.

Exit gate: default build shows no experimental entry points; flipping the flag restores them; `knip` or `ts-prune` reports no dead imports; the notify modal offers exactly two channels and validates each correctly.

---

## Phase 7 — Design system pass, and how not to look AI-generated

Here's the uncomfortable part: "dark glass with frosted cards, one-pixel gradient border wrappers, and soft atmospheric light" is the most recognisably LLM-generated visual language currently in circulation. Executed literally, that spec produces the exact look you're trying to avoid. The tells are specific and they're all in your brief.

What actually reads as AI-generated: gradient borders on everything; blur on every surface; a violet-to-cyan accent gradient; gradient-filled headline text; three equal cards in a row with an icon, a bold title, and two lines of grey filler; glow instead of structure; everything centred; uniform 24px padding everywhere; six shades of the same accent; emoji as iconography; and copy in the register of "Seamlessly orchestrate your workflow."

What reads as designed by a person who has opinions:

Anchor the whole thing on the fact that this is a *photography* product. The photos are the only saturated thing on screen. Chrome is neutral — a near-black base like `#0B0B0C` rather than pure `#000`, text in a two-step hierarchy (`zinc-100` for primary, `zinc-400` for secondary, and resist inventing a third), and hairline borders at `rgba(255,255,255,0.07)` doing the work that glow would otherwise do badly. Pick exactly one accent and use it only for the primary action and focus rings. If you can't tell which button on a screen is the important one within half a second, you've used it too often.

Use blur *once*, on genuinely floating layers — the modal backdrop and the sticky header over a scrolling gallery. Applying `backdrop-blur` to a card sitting on a flat background is a visual lie, since there's nothing behind it to blur, and it costs real compositing performance on a grid of a thousand photos. Cards get a subtle surface lift (`#141416` on `#0B0B0C`) and a hairline border. That's it.

Type does more for perceived quality than any effect. Don't ship Inter at three weights — it's the default of every AI-generated landing page. Something with character in headings and a neutral workhorse for UI text separates you immediately; a real modular scale (13 / 15 / 18 / 24 / 32, and stop) beats fourteen ad-hoc sizes; and tabular numerals on counts and timestamps is the kind of detail people feel without noticing.

Break the grid deliberately. An asymmetric Event Details layout — a wide primary column with a narrow metadata rail — looks considered. Two-thirds/one-third looks designed; three equal cards looks generated. Show real density too: actual guest counts, actual thumbnails, actual timestamps in the mockups. Placeholder-shaped layouts are placeholder-shaped because nobody checked them against real content.

Sequence the work so you don't repaint twice. First, tokens only — CSS custom properties in `globals.css` for surfaces, borders, text, one accent, radii, and shadow, with nothing else changed. Second, the app shell: sidebar with a thin boundary rail and a frosted-only-when-floating active pill, plus the header. Third, the highest-traffic surface, which is the *gallery*, not Event Details — a virtualized masonry grid with blurhash or dominant-colour placeholders, keyboard navigation, and a lightbox. Fourth, Event Details and the Notify modal. Dashboard and Settings come in a second pass; answering your open question directly, don't try to do them in this one.

Exit gate: every colour in the diff resolves to a token; Lighthouse accessibility ≥ 95 with all text at 4.5:1 or better; the gallery holds 60fps scrolling at 1,000 thumbnails on a mid-range Android; and a screenshot of Event Details next to three randomly-generated dark SaaS dashboards is distinguishable by a stranger.

---

## Phase 8 — Operability, before you build anything destructive

`/healthz` returns 200 if the process is alive, full stop — never check dependencies here, or a Neon blip triggers a container restart loop. `/readyz` checks Postgres and Redis reachability and returns 503 when they're down. Wire compose healthchecks with `depends_on: condition: service_healthy`.

Then error tracking with `ENVIRONMENT` tags (Sentry or self-hosted GlitchTip), a Beat task alerting when queue depth crosses a threshold, `docker system prune -af --filter until=168h` on a weekly timer to protect the disk, and — the one that matters most for the next phase — a **documented restore drill against a Neon branch, with a timestamp.** A backup you have never restored is a hypothesis, and Phase 9 is where hypotheses become expensive.

Exit gate: all services report healthy; severing Neon connectivity makes `/readyz` return 503 while `/healthz` stays 200; a restore drill is written up with a date and a wall-clock duration.

---

## Phase 9 — 14-day retention, auto-purge, and biometric consent

Now you can safely build the deleter. Two things are being conflated in "auto purge all data," and they have different legal and product weight, so model them separately.

**Data model.** On the event: `retention_days` (default 14), `auto_purge_enabled` (default true), `purge_after` as a computed column from event end date plus retention, and `retention_overridden_by` / `retention_overridden_at` so a disabled purge is attributable to a human. Biometric embeddings get a *shorter, separate* clock — purge them once matching completes or at 14 days, whichever comes first, because they're the highest-risk data you hold and they have no value after matching. Add a `legal_hold` boolean that blocks purge regardless of other settings.

**The purge task.** Beat-scheduled daily, and every single one of these guardrails earns its keep: a `PURGE_DRY_RUN` env var defaulting to `true` in all environments including prod on first deploy; a per-run cap on events processed so a clock bug can't nuke everything in one pass; an append-only `purge_audit` table recording what was deleted, counts, and byte totals, written *before* deletion and completed after; idempotency so a retried task doesn't double-count; and R2 object deletion driven from the DB manifest rather than a prefix wildcard, with an R2 lifecycle rule as a backstop rather than the primary mechanism.

Sequence: soft-delete and revoke all guest tokens at `purge_after`, then hard-delete after a 72-hour grace period. Warn the organiser by email at T-3 days and T-1 day with a one-click extend. An event whose gallery silently evaporated is a refund request; an event whose organiser got two warnings and ignored them is a support conversation.

Test it with `freezegun`: an event at T-13 is untouched, T-15 soft-deletes, T-15+72h hard-deletes, `auto_purge_enabled=false` never purges, `legal_hold=true` never purges even with auto-purge on.

**Consent, which is a product requirement and not a nice-to-have.** Face embeddings are biometric data — GDPR Article 9 special category, plus India's DPDP Act, Illinois BIPA, and Texas CUBI, and BIPA in particular carries a private right of action. So: explicit consent capture at selfie upload with the text version stored; a stated retention window shown to the guest at the point of upload; `DELETE /api/v1/guests/{id}/biometrics` purging embeddings while retaining the guest row; and a privacy page describing what's stored and for how long. Your 14-day default is genuinely good compliance posture — it turns a liability into a feature you can put on the marketing page. I'm not a lawyer and this summary isn't sufficient; get it reviewed before you process a paying client's event.

Exit gate: the freezegun matrix above passes; a dry run against production data logs a plausible manifest and deletes nothing; audit rows exist for every purge; `DELETE .../biometrics` leaves the guest row and its notification history intact.

---

## Phase 10 — Consolidate the matching path (defer, but don't forget)

You currently have two competing similarity implementations: provisioned pgvector, and an in-memory numpy matmul in the worker you've labelled "I/O bound." That label is wrong — matrix multiplication is CPU-bound, and mislabelling it will mislead every future contributor and every agent that reads the doc. Rename the worker to `worker-general`, or split matching into `worker-match`.

Make pgvector the single path and push the compute to Neon. Store embeddings L2-normalised so you can use inner product, which is the fastest operator for unit vectors:

```sql
ALTER TABLE face_embeddings ALTER COLUMN embedding TYPE vector(512);
CREATE INDEX CONCURRENTLY idx_face_emb_hnsw
  ON face_embeddings USING hnsw (embedding vector_ip_ops)
  WITH (m = 16, ef_construction = 64);
```

Two things to know before you commit. HNSW builds are memory-hungry, so raise `maintenance_work_mem` and always build `CONCURRENTLY`. And filtering by `event_id` degrades HNSW recall, because with an approximate index the filter is applied *after* the index scan — with the default `hnsw.ef_search` of 40, a filter matching 10% of rows leaves you roughly four results. pgvector 0.8 addresses this with iterative scans (`SET hnsw.iterative_scan = relaxed_order`, wrapped in a materialized CTE if you need strict ordering back), but for your actual shape — a few thousand faces per event, hard-partitioned by event — a **partial index per event or list partitioning by `event_id`** is both faster and better for tenant isolation, since a shared approximate index lets one event's vectors affect another's recall. Benchmark at real cardinality (5k faces, 200 guests) before deciding, and record the p95 in the ADR.

Add content-hash deduplication in the same pass so a re-uploaded photo doesn't re-run inference — that's your cheapest available throughput win. Then delete the losing path rather than leaving it as an unflagged fallback.

Exit gate: p95 single-guest match latency against a 5k-face event recorded in the ADR; recall measured against exact brute force on a labelled fixture; exactly one code path remains in the repo.

---

## Two more things about the task format

Every task needs a fully qualified path from repo root and a verification command whose output proves completion. "Create a `MetaWhatsAppService` inside `notifications.py`" will make an agent either guess or create a second `notifications.py`, and "Benefit: seamless UX" is not something an agent can check. The uniform shape — Depends on, Files with create/modify/delete markers, Do, Do NOT, Verify with expected output, Rollback — is worth the small overhead on every task.

And three process rules that matter more than the document format: one phase per branch and PR; every task independently revertable; and any task that would span backend and frontend gets split, with the OpenAPI contract change landing first as its own task. Phase 4 in particular will tempt an agent to do the abstraction and the WhatsApp provider in one pass. Don't let it — you want the abstraction reviewable while the template is still in Meta's queue.N opens roughly N+2 connections, and your threaded worker opens more. Free-tier connection caps are easy to blow through with three workers plus Flower plus the API. 2. You have two competing similarity paths — pick one You provisioned pgvector and you compute cosine similarity in-memory in worker-io via numpy matmul. That's duplicated logic, duplicated truth, and it's the wrong place for it on a 6 GB box. Also, matrix multiplication is not I/O-bound; calling that worker "I/O bound" will mislead every future contributor and every agent reading this doc. Recommendation: make pgvector the single matching path. Store embeddings L2-normalised as vector(512), use vector_cosine_ops with HNSW, and push the compute to Neon: sql ALTER TABLE face_embeddings ALTER COLUMN embedding TYPE vector(512); CREATE INDEX CONCURRENTLY idx_face_emb_hnsw ON face_embeddings USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64); -- per-session recall tuning SET hnsw.ef_search = 100; Query pattern is then ORDER BY embedding <=> :probe LIMIT k filtered by event_id. Two caveats to test before committing: HNSW builds are memory-hungry (raise maintenance_work_mem, build with CONCURRENTLY), and pre-filtering by event_id can degrade HNSW recall — for per-event galleries with a few thousand faces, a partial index per event or just an IVFFlat/exact scan within the event may actually be faster. Benchmark at your real cardinality before deciding. Keep the numpy path only as an explicitly-labelled fallback behind a flag, and rename the worker to worker-general or split matching into worker-match. 3. Celery Beat is co-located with a worker If you ever set replicas: 2 on worker-io, you get two schedulers and every maintenance task fires twice. Split Beat into its own single-replica container now — it costs ~60 MB and removes a whole class of future incident. 4. WhatsApp: your plan understates the constraints "Send gallery links directly to guests" is not something the Cloud API lets you do freely.