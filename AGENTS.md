# Aurora Agentforce

Projeto de portfólio: Agentforce na Salesforce e uma API Python de pedidos fictícios.
Leia README.md e salesforce/SETUP.md antes de alterar escopo.

- Preserve Python 3.14, uv, tipagem completa e Mypy strict.
- Não use `from __future__ import annotations`.
- Dependências: entrypoints -> application -> domain; adapters contém apenas dados de demonstração.
- Regras de negócio são determinísticas. O LLM não decide elegibilidade.
- Trabalhe apenas com dados sintéticos. Nunca registre chaves, prompts ou dados pessoais.
- O contexto da demonstração tem um único cliente fixo; não confunda isso com autenticação de usuários.
- Teste comportamento, erros, autorização e contrato externo.
- Execute `uv run python scripts/quality_gate.py` antes de concluir alterações Python.
- Mantenha apenas README e SETUP como documentação explicativa; atualize-os quando necessário.
- Não adicione serviços, frameworks de agentes, MCP, banco ou camadas sem necessidade demonstrável.
- Não declare testes Salesforce, publicação ou deploy concluídos sem evidência na organização.
- Não faça commit, push, publicação ou deploy sem pedido explícito.
