# Event Observer Flow

1. Read watermark from `observer_state`
2. Query `audit_outbox_event` with `status='pending'` and eligible `event_type`
3. Deduplicate by `source_event_id` in `anchor_request`
4. Create `anchor_request` with scope derived from event type
5. Advance watermark to latest processed `created_at`

Worker loop additionally:

1. Builds packages for pending requests
2. Simulates anchoring for `ready_to_anchor` packages
3. Retries failed requests
