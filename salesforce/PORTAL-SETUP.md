# Experience Cloud portal baseline

Sanitized Metadata API export, API 68.0. Portal template is intentionally outside the deployable DX package. The source org portal was published; this candidate uses an active CustomSite with Network status UnderConstruction, with direct messages and welcome emails disabled. No live deployment or authenticated Agentforce test has been performed for this candidate.

Prerequisites: Digital Experiences enabled, custom external profile `Aurora Customer`, verified sender email, internal administrator and guest-record owner. Review all profile CRUD/FLS, guest permissions and standard template pages before activation. Do not attach the legacy fixed-customer agent. No customer records or credentials are included.

From repository root:

```bash
uv run python scripts/portal_prepare.py
```

Render outside the repository with real environment-specific values (never commit the rendered files):

```bash
uv run python scripts/portal_prepare.py --output /tmp/aurora-portal-rendered \
  --sender "$PORTAL_SENDER" --admin "$PORTAL_ADMIN" --owner "$PORTAL_OWNER"
bash scripts/sf-validate-portal.sh aurora-dev /tmp/aurora-portal-rendered
```

Dry-run only. Do not deploy over the existing live site without reviewing the impact: the candidate requests Network status UnderConstruction. Activation is manual after review. Static checks are not proof of access isolation. Test guest denial, two external logins, cross-account access, logout and Agentforce execution identity independently. The template's standard community routes remain intact; remove or restrict unnecessary functionality in Experience Builder before enabling business operations.

## Salesforce validation evidence

Validated on November 24, 2026, in a Salesforce
Developer Edition using Metadata API v68.0.

- JSON files validated: 117.
- Route references validated: 55.
- Metadata components validated: 3/3.
- Deployment validation status: Succeeded.
- Elapsed time: 14.55 seconds.
- Deployment mode: dry-run.
- Apex tests: skipped.
- Permanent deployment: not performed.

The initial validation rejected CustomSite.active=false.
The corrected configuration uses CustomSite.active=true
and Network.status=UnderConstruction.

This validates metadata compatibility with the existing
development org. It does not establish fresh-org portability,
runtime authentication or customer isolation.

The dry-run wrapper requires PORTAL_SENDER, PORTAL_ADMIN and PORTAL_OWNER in the environment. It compares the rendered file inventory and contents with the template and expected substitutions before invoking Salesforce CLI. This is a local integrity check, not a signed artifact or protection against concurrent filesystem modification.

## Revision after initial validation

34 filenames were restored from mojibake to UTF-8 without changing their Git blobs. The initial 3/3 Salesforce result predates those renames; the corrected revision was subsequently validated as recorded below. The local verifier compares rendered bytes with the current template, not the older validated package. Regression tests are in `tests/test_portal_prepare.py`. Run `uv run pytest tests/test_portal_prepare.py --no-cov` for targeted checks and `uv run python scripts/quality_gate.py` for the full gate.

## Corrected revision evidence (November 24, 2026)

Validated local checkout: `fac9596f8a7646cb6cafeb129768d863d6a20c1f` (fast-forward to the remote branch, as shown in the CLI transcript).

- Locked dependency synchronization succeeded.
- 117 JSON files and 55 route references passed static validation.
- Rendered metadata integrity verified before invoking Salesforce CLI.
- Metadata API v68.0 dry-run: Succeeded, 3/3 components (CustomSite, ExperienceBundle, Network), 14.73 seconds.
- Apex tests and source tracking skipped; no permanent deployment performed.
- GitHub Actions for the same revision: quality, Salesforce DX metadata checks and CodeQL workflows succeeded. Pytest: 144 passed (12 portal cases); combined coverage 95.25%; portal validator coverage 90% (rounded); Mypy: no issues in 30 source files.

This is existing-org metadata compatibility and offline regression evidence, not proof of secure customer login, account isolation, fresh-org provisioning, or authenticated Agentforce execution. The standard template surfaces and permissions still require review before any customer-facing activation. No legacy agent connection is authorized by this result.
