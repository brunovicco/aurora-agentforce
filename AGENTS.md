# Aurora Agentforce

Portfolio project: Salesforce Agentforce with an external Python API serving fictional orders.
Read README.md and salesforce/SETUP.md before changing the scope.

- Preserve Python 3.14, uv, complete type annotations, and strict Mypy checks.
- Do not use `from __future__ import annotations`.
- Dependency direction: entrypoints -> application -> domain; adapters hold demo data only.
- Business decisions must remain deterministic. The LLM does not decide return eligibility.
- Use synthetic data only. Never commit secrets, prompts with private information, or personal data.
- Legacy demo routes use a fixed customer reference; do not mistake this for end-user authentication.
- Verified API routes require a signed short-lived session from a trusted upstream issuer; signing is not authentication and must never be delegated to the agent.
- Preserve the verified/unverified boundary and require explicit opt-in for unverified demo reads.
- Test behavior, errors, authorization, and the external API contract.
- Run `uv run python scripts/quality_gate.py` before completing Python changes.
- Keep explanatory documentation in README.md (English), readme.pt-BR.md (Brazilian Portuguese), and salesforce/SETUP.md; maintain them consistently.
- Do not add services, agent frameworks, MCP, databases, or layers without demonstrated need.
- Do not claim Salesforce tests, deployments, or release milestones without org evidence.
- Do not commit, push, publish, or deploy unless explicitly requested.
