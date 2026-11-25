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

## Backup evidence

Revision `f66f408`: original portal Metadata API v68.0 retrieve succeeded in 9.86 seconds; all three requested components present and archive checks succeeded. The ZIP and SHA-256 report remain private with the operator. No deployment performed. CI: 204 tests passed, configured coverage 95.56%, Mypy clean, Bandit no findings; format-only failure corrected in the next revision.

Run `bash scripts/sf-validate-portal-restore.sh aurora-dev /private/backup-directory` to recheck the retained ZIP against its original integrity report and submit only a dry-run. This report is not a signature, and the operator must retain the original hash separately. No restoration or publication occurs.

## Restore validation evidence

Revision `94c5e6f`: the operator retained a private permanent copy of the backup and rechecked it against the original integrity report. Salesforce API 68.0 restoration dry-run succeeded, 3/3 components, 17.33 seconds, Apex tests and source tracking skipped. All three CI workflows passed for this revision. No restoration, deployment or publication performed. This is compatibility evidence, not a proven rollback of published state.

## Compare candidate against retained backup

Run `uv run python -m scripts.portal_compare /private/backup-directory` from repository root. This compares the sanitized candidate ExperienceBundle against the original verified ZIP without extracting it. JSON semantic equality ignores whitespace and object key order; Unicode filenames are normalized to NFC, collisions rejected. Only relative names of explicitly approved changed files and aggregate counts are printed. The comparison does not inspect live drift, publication state, or differences in Site/Network. Do not deploy the full candidate manifest based on this report. Any extra change or file inventory mismatch requires investigation. A scoped package and its own dry-run are required next.

## Scope comparison evidence

Revision `d61fc09`: all three CI workflows passed. The operator compared the verified original backup with the candidate: 117 files on each side, exactly the three intended JSON changes, no unexpected changes, additions or removals. No live drift evidence or deployment authorization was produced.

## Scoped validation

Run `bash scripts/sf-validate-portal-scope.sh aurora-dev /private/original-backup-directory`. The script retrieves a fresh copy of the same three components into a private temporary directory, verifies both ZIPs and compares the component payloads (JSON semantically; other files bytewise). A difference blocks further work, including differences caused by Salesforce serialization. It then rechecks the three-file candidate scope and creates a private ExperienceBundle-only Metadata API directory with a single-member manifest, validates it using dry-run and prints a package digest. No site/network deployment or publication occurs. The temporary fresh retrieve is deleted; original backup is preserved. Drift checking is a point-in-time observation, not a lock. Keep Builder edits frozen. The package is retained privately for subsequent review; do not deploy it without separate approval.

## First scoped dry-run evidence

Revision `ea34756`: fresh retrieve succeeded (9.40 seconds); payload matched original backup and candidate scope matched. The ExperienceBundle-only dry-run failed because the package generator omitted the sibling `experiences/Aurora_Customer_Portal1.site-meta.xml` descriptor. The next revision includes that existing descriptor, checks it bytewise against the retained backup, and tests exact package inventory. No permanent deployment occurred. Retry the scoped validation; do not reuse the earlier incomplete package.

## Scoped dry-run success evidence

Revision `9521a988db9fb0d1fa04e86610011bed07fe2bc2`: fresh retrieve succeeded (6.69 seconds), all three component payloads matched the original backup, three intended changes and no unexpected changes, sibling descriptor matched the backup. ExperienceBundle-only dry-run succeeded (1/1, 15.46 seconds, API 68.0), tests and source tracking skipped. All three GitHub Actions workflows passed. The approved candidate digest was `acecdd84db26ddf80aa1d9c3d16cfb5cfe88faf13a1769373f114a1899c46baf`. No deployment or publication performed.

## Approved-package preflight

Before any authorized deployment, keep concurrent Builder changes frozen, capture published status and verify the legacy agent is disconnected. Run `bash scripts/sf-check-portal-deploy.sh aurora-dev /private/original-backup-directory /private/approved-candidate-directory APPROVED_SHA256`. This read-only preflight verifies exact candidate file inventory and bytes against the repository, checks the previously observed package digest, retrieves a fresh copy of the original three components, and checks no drift. It never deploys. If any check fails, stop. Only deploy the exact reviewed ExperienceBundle package with a separately approved command; inspect actual publication behavior and do not manually publish until reviewed.

## Final preflight evidence

Revision `001f4a86656b61b0abde0bd1dd4e97bf68b2a052`: all three CI workflows succeeded. Operator executed the approved-package preflight; fresh metadata retrieve succeeded in 6.07 seconds, archive integrity passed, live payload matched original backup and candidate inventory/bytes/digest matched the validated package. No deployment performed. Publication state and absence of a legacy messaging channel still require operator confirmation. Freeze concurrent changes; repeat preflight immediately before separately approved deployment if any time or change has intervened.

## Controlled deployment evidence

The operator confirmed all four change approval controls (published state recorded, legacy agent disconnected, no concurrent Builder edits, permanent ExperienceBundle-only deploy authorized). Immediate preflight passed: fresh retrieve 14.95 seconds, no drift, candidate integrity verified. Salesforce API 68.0 permanent deployment succeeded, 1/1 ExperienceBundle, 11.21 seconds. Apex tests and source tracking skipped. The submitted manifest contained only the ExperienceBundle. Actual post-deploy metadata, publication state, effective security and rollback execution remain unverified. No manual publication was reported. Do not connect the legacy agent.

## Post-deployment verification

Run `bash scripts/sf-check-portal-postdeploy.sh aurora-dev /private/original-backup-directory /private/approved-candidate-directory APPROVED_SHA256`. It retrieves the three metadata components again, verifies the approved candidate bytes, overlays only the approved ExperienceBundle payload onto the original backup in memory and compares with the retrieved payload. JSON is compared semantically and other files bytewise. Differences block verification and require review, including platform serialization changes. This is not a publication or runtime check. It does not deploy, publish or modify permissions. If the retrieved metadata matches, inspect Builder preview and the current publication state separately before authorizing publication.

## First post-deployment retrieve

Revision `899efd3`: retrieve succeeded (9.93 seconds), all 120 expected payload files were present, no additions/removals and zero mismatches outside the ExperienceBundle. Two bundle payload files differed; metadata equivalence remains false. The next revision adds structural diagnostics without values and fixes Ruff lint/format findings. CI for `899efd3` had 218 passing tests and 95.56% configured coverage, but failed lint and format. Do not publish or automatically restore until differences are classified. Diagnostic property names and filenames should be reviewed locally for sensitive identifiers before sharing; no metadata values are printed. No normalization exceptions have been introduced.

## Observed empty-region serialization

Revision `05e991e`: all three CI workflows succeeded. Post-deploy retrieve succeeded in 7.71 seconds; all 120 files present, no outside-scope mismatches. Five missing `components` properties were reported: theme search region and home featured, content, sidebar and footer regions. Inspection of the versioned candidate confirmed all five properties were empty arrays. The next revision recognizes only these exact file/region paths, only missing properties corresponding to an explicit empty array, and only matching region identity/type/name. Strict equality remains separately reported; semantic equivalence is not proof of Salesforce runtime behavior. Nonempty arrays, nulls, other paths/files and unrelated differences still block verification. No candidate metadata, backup, or Salesforce configuration changed. Verify again and inspect Builder preview before publication.
