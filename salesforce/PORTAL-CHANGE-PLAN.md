# Controlled portal change — dedicated Developer Edition

The operator confirmed that the current Developer Edition is exclusively for the synthetic Aurora project. Do not change permissions or attach the legacy agent. This plan backs up only the three metadata components in the portal manifest; it is not an org or data backup, nor a guaranteed rollback of published state.

## Gate 1: capture the existing editable metadata

Record the currently published site status, navigation, login and guest behavior and verify no legacy messaging channel is connected. Keep screenshots private. Freeze concurrent Builder edits. Run from repository root:

```bash
bash scripts/sf-backup-portal.sh aurora-dev
```

Keep the printed private directory and original ZIP; do not upload or commit either. The tool validates CRC, path safety, expected manifest, site/network files and presence of routes/views and records SHA-256. It does not establish complete backup fidelity or restore compatibility. Retain a second secure copy outside temporary storage before proceeding.

## Gate 2: restore dry-run

After review of the archive integrity report, validate the untouched original ZIP against the same org using Salesforce CLI metadata-dir and dry-run. A successful validation does not restore anything or guarantee publication rollback. Capture existing site publication state separately. If validation fails, stop.

## Gate 3: candidate change

Only after both dry-runs pass, compare current metadata with the candidate and review differences, including Network status UnderConstruction, site configuration and dependencies. Prefer the narrowest applicable ExperienceBundle change rather than overwriting unrelated site settings. Approve a specific deploy command separately. No publication until Builder preview and access review. Do not connect any legacy agent.

## Rollback

If change or preview fails, stop further changes. Verify original ZIP SHA-256 and validate restoration again; redeploy only after reviewing the exact org, scope and current status. Restore publication state separately if needed and repeat login and access checks. Metadata restoration cannot undo unrelated business writes or guarantee exact restoration of runtime state.
