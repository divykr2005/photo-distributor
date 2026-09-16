# Operations & Maintenance

This document outlines standard operating procedures and maintenance tasks for the AI Event Photo Distribution system.

## Cloudflare R2 Lifecycle Rules

To prevent ballooning storage costs from temporary ZIP files (which are only needed until the user downloads them), you must configure a lifecycle rule in your Cloudflare R2 dashboard.

1. Go to the Cloudflare Dashboard -> **R2** -> `snaptracer` bucket.
2. Select **Settings** -> **Object Lifecycle Rules**.
3. Click **Add rule**.
4. Set the **Rule Name**: `Expire Stale ZIPs`
5. Under **Apply rule to:**, select **Prefix** and enter `zips/`.
6. Under **Action**, choose **Delete objects**.
7. Set the condition to **7 days** after object creation.
8. Save the rule.

*Note: The Celery beat task `sweep_expired_zips` cleans up database records for ZIPs older than 1 hour. The R2 lifecycle rule ensures the actual binary data is dropped if not explicitly deleted.*

## Database Restore Drills (Neon)

Neon branch-based restores allow us to test recovery procedures without impacting production. You should perform this drill at least once per quarter.

### Drill Procedure

1. **Create a recovery branch:**
   In the Neon console, create a new branch from your `main` branch. Select a Point-In-Time (PITR) in the past (e.g., 2 hours ago) to simulate recovering from data corruption. Name the branch `restore-drill-YYYYMMDD`.

2. **Verify connection:**
   Get the connection string for `restore-drill-YYYYMMDD`.
   In your local or staging environment, temporarily update `DATABASE_URL` in `.env` to point to the drill branch.

3. **Run Application Tests:**
   Restart the backend and run tests against the database:
   ```bash
   docker compose restart backend
   python -c "import requests; print(requests.get('http://localhost:8000/readyz').json())"
   ```

4. **Verify Data Integrity:**
   Ensure recent event photos are still accessible, and the matching engine functions correctly.

5. **Cleanup:**
   Restore `DATABASE_URL` to the production branch.
   In the Neon console, delete the `restore-drill-YYYYMMDD` branch to avoid excess storage costs.

## System Maintenance

The host VM should have a cron job to automatically run docker pruning to prevent disk exhaustion from old container logs and dangling images.

```bash
# Add to root crontab: sudo crontab -e
# Run weekly on Sunday at 3 AM
0 3 * * 0 /opt/photo-distributor/scripts/weekly_maintenance.sh >> /var/log/docker-maintenance.log 2>&1
```

A 4GB swap file must be provisioned on small-tier VMs to prevent OOM kills during model loading or peak concurrent extraction. Use `/scripts/setup_swap.sh` for initial VM provisioning.
