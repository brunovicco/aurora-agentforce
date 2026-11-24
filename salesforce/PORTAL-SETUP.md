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

34 filenames were restored from mojibake to UTF-8 without changing their Git blobs. The initial 3/3 Salesforce result predates those renames; repeat rendering and the dry-run before making any new compatibility claim. The local verifier compares rendered bytes with the current template, not the older validated package. Regression tests are in `tests/test_portal_prepare.py`. Run `uv run pytest tests/test_portal_prepare.py --no-cov` for targeted checks and `uv run python scripts/quality_gate.py` for the full gate.
