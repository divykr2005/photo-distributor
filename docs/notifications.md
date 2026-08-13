# Notification Engine Architecture & Setup (Week 3)

The notification dispatch engine manages magic link delivery to guests across multiple pluggable transport channels.

---

## 1. Notifier Protocol & Adapters (Decision D26)

All notification providers implement the standard `Notifier` interface:

- `ConsoleNotifier` (default development adapter): Logs formatted messages to stdout / Celery logger.
- `SMTPNotifier`: Email transport via standard SMTP with HTML and plain-text fallback templates.
- `WebhookNotifier`: Outbound HTTP POST payload dispatch to external CRM or messaging endpoints.
- `TwilioSMSNotifier`: SMS delivery via Twilio API.
- `TwilioWhatsAppNotifier`: WhatsApp Template delivery via Twilio Content API (behind feature flag `NOTIFIER_WHATSAPP_ENABLED`).

---

## 2. Idempotency & Deduplication (Decision D27)

Notification dispatches are guarded against duplicate delivery by a database constraint:

```sql
UNIQUE (guest_id, channel, notification_type, dedupe_key)
```

- `dedupe_key` defaults to `{token_hash[:8]}_{photo_count_bucket}`.
- If a dispatch task is triggered repeatedly, duplicate records are marked `status = 'skipped_duplicate'` and the provider API is not called.

---

## 3. Retries & Error Handling

- **Transient Failures (HTTP 429, 5xx, Network Timeout):** Automatically retried up to 5 times using exponential backoff with jitter (`60s × 2^n`).
- **Hard Rejections (Invalid Number, Unsubscribed, HTTP 400/404):** Immediately marked `status = 'failed'` without retrying.

---

## 4. Quiet Hours Windowing (Decision D28)

- **Window:** 21:00–08:00 (9:00 PM – 8:00 AM) local time of the event.
- **Action:** Messages queued during quiet hours calculate the next 08:00 AM local timestamp and reschedule execution using Celery ETA.

---

## 5. Local Sandbox Instructions

To test notifications locally without sending real SMS or emails:

1. Set `NOTIFIER_CHANNEL=console` in `.env`.
2. Run notification dispatch:
   ```bash
   python -m workers.notifications
   ```
3. Check stdout or Celery task logs for generated magic link URLs and template copy.
