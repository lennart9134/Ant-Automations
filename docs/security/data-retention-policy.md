# Data Retention and Deletion Policy

## Retention Periods

| Data Category | Default Retention | Minimum | Maximum | Configurable |
|--------------|-------------------|---------|---------|-------------|
| Workflow execution state | 90 days | 30 days | 2 years | Yes, per tenant |
| Audit log | 1 year | 1 year (regulatory) | 7 years | Yes, per tenant |
| Model inference logs | 30 days | 7 days | 1 year | Yes, per tenant |
| Connector action logs | 90 days | 30 days | 2 years | Yes, per tenant |
| Approval records | 1 year | 1 year (regulatory) | 7 years | Yes, per tenant |
| User session data | 24 hours | 1 hour | 7 days | Yes, per tenant |
| Tenant configuration | Indefinite | — | — | Deleted on tenant removal |

## Automated Deletion

- Daily batch job evaluates retention policies per tenant
- Expired records are hard-deleted (not soft-deleted) from Postgres
- Associated MinIO objects are deleted in the same batch
- Deletion events are logged in the audit trail (meta-audit)

## Right to Erasure (GDPR Art. 17)

- Personal data can be purged per individual via `DELETE /api/v1/admin/users/{user_id}/data`
- Erasure cascades: workflow state referencing the user, audit log entries (anonymized, not deleted), connector action logs
- Audit log entries are anonymized (user ID replaced with hash) rather than deleted to maintain audit trail integrity
- Erasure completion is confirmed via webhook to the requesting tenant admin

## Backup and Recovery

- Postgres backups: daily encrypted snapshots, retained for 30 days
- Backups inherit the retention policy of the source data
- Backup deletion is automated when source retention period expires
