# Salesforce — configuração e estado da demonstração Aurora

**Marco parcial (21/11/2026).** A integração foi configurada e exercitada
em uma Salesforce Developer Edition, com ações reais de Agentforce e criação
de registros `Case`. Este guia descreve o que foi validado, o que é
específico da organização e o que ainda falta. **Não é um procedimento
de instalação automática em qualquer org, nem uma solução pronta para produção.**

## Componentes implementados

- Bundle do agente: `force-app/main/default/aiAuthoringBundles/Aurora_Pos_Venda_1/`
  (`Aurora_Pos_Venda_1.agent`), com ações `Get_Order`,
  `Check_Return_Eligibility` e `Create_Support_Case`.
- External Service `AuroraOrdersService` (operações `getOrder` e
  `checkReturnEligibility`), usando a Named Credential `AuroraOrders`.
- Flow autolaunched `AbrirCasoPosVenda` (`order_id` como entrada;
  `case_number` e `outcome` como saídas).
- Campo único `Case.AuroraRequestKey__c` para idempotência.
- Objeto `AuroraCaseApproval__c`, com `RequestKey__c` único,
  `Approved__c` e `ExpiresAt__c` para autorização prévia independente.
- Permission Sets `Aurora_API_Access`, `Aurora_Approval_Read` e
  `Aurora_Case_Access`.

O código e os metadados estão versionados; **não** estão versionados os
segredos da External Credential, autorização local do Salesforce CLI, dados
criados na org nem a URL temporária do túnel.

## Integração da API

A API Python local usa `AURORA_API_KEY` com pelo menos 32 caracteres
e autenticação pelo cabeçalho `X-API-Key`. O contrato publicado é
[`openapi.json`](openapi.json), OpenAPI 3.0.3.

Para conectar a Salesforce, inicie a API conforme o [README principal](../README.md)
e use uma URL HTTPS acessível temporariamente, por exemplo:

```bash
cloudflared tunnel --url http://localhost:8000
```

O Quick Tunnel muda de endereço e requer o processo local em execução.
Ele foi utilizado nos testes, **não é uma hospedagem permanente**.

A configuração manual na organização inclui:

1. External Credential `AuroraApiAuth`, principal nomeado
   `AuroraDemoPrincipal` e parâmetro secreto de chave de API.
2. Cabeçalho `X-API-Key` construído a partir do parâmetro protegido
   da credencial, sem copiar o valor para metadados versionados.
3. Named Credential `AuroraOrders` apontando para o endpoint HTTPS atual,
   com acesso do principal concedido ao usuário de execução via
   `Aurora_API_Access`.
4. Registro de External Service `AuroraOrdersService` associado à Named
   Credential. Para um ambiente novo, valide ordem de provisionamento,
   permissões e compatibilidade de API antes de implantar o pacote.

**A chave autentica a integração Salesforce → API, não o cliente da
conversa.** O backend utiliza `customer-demo-001` fixo; não presuma
isolamento por cliente autenticado.

## Fluxo de autorização e idempotência

O Flow faz nova validação do pedido na API e constrói uma chave determinística
do tipo `customer-demo-001:AUR-1003:post-sale` (dados inteiramente fictícios).

A sequência validada é:

1. Verificar resposta `200` e `order_id` idêntico ao solicitado.
2. Buscar aprovação independente com `RequestKey__c` correspondente,
   `Approved__c = true` e `ExpiresAt__c` futuro.
3. **Somente após aprovação**, consultar o Case existente e, se não houver,
   criar um novo com a chave única.
4. Devolver `created` ou `existing` com `case_number` verdadeiro;
   `approval_required`, `unavailable` e `failed` não divulgam número.

A ação `Create_Support_Case` exige confirmação nativa do Agentforce.
Uma resposta `yes` na conversa **não substitui** a aprovação independente.
A aprovação é representada pelo objeto personalizado, preenchido
separadamente por um usuário autorizado; **não implementamos um Salesforce
Approval Process formal nem um mecanismo de consentimento do cliente**.
Nunca conceda ao agente permissão para criar, editar ou excluir aprovações.

## Validar na Developer Edition

No diretório `salesforce/`, com a org autenticada (alias de exemplo:
`aurora-dev`):

```bash
sf agent validate authoring-bundle \
  --api-name Aurora_Pos_Venda_1 \
  --target-org aurora-dev \
  --api-version 68.0

python3 ../scripts/verify_aurora_flow.py

sf agent preview start \
  --authoring-bundle Aurora_Pos_Venda_1 \
  --use-live-actions \
  --target-org aurora-dev
```

A validação do bundle concluiu com **zero erros**. O Flow corrigido foi
implantado e ficou ativo na org utilizada na demonstração. Para testar
uma sessão nova, use o ID retornado:

```bash
SESSION_ID="COLE_O_ID_RETORNADO"

sf agent preview send \
  --authoring-bundle Aurora_Pos_Venda_1 \
  --session-id "$SESSION_ID" \
  --utterance "Please open a support case for order AUR-1003." \
  --target-org aurora-dev

sf agent preview send \
  --authoring-bundle Aurora_Pos_Venda_1 \
  --session-id "$SESSION_ID" \
  --utterance "yes" \
  --target-org aurora-dev

sf agent trace read \
  --session-id "$SESSION_ID" \
  --format detail \
  --dimension actions
```

**Atenção:** `--use-live-actions` pode executar gravações reais.
Não repita comandos de criação ou alteração de aprovação sem compreender
o efeito sobre o estado da organização.

### Evidências coletadas

- `AUR-1003`: criação real de Case e recuperação posterior do mesmo número
  com aprovação válida, sem duplicação.
- Aprovação revogada: resultado `approval_required`, sem divulgação
  do número do Case que já existia. O trace bruto mostrou
  `case_number = ''`.
- Confirmação negativa: ação de criação não foi invocada no preview testado.
- Resposta do agente atualizada: orienta procurar a equipe de suporte,
  sem afirmar existência de um canal oficial de aprovação do Salesforce.
- Revisão de `ObjectPermissions`, `FieldPermissions`,
  `PermissionSetGroupComponent` e `UserRecordAccess`: leitura de
  aprovações, sem criação/edição/exclusão; leitura/criação de Cases,
  sem edição/exclusão. Verificações efetuadas com o usuário
  Einstein Agent da demonstração.

Essas evidências são **testes manuais pontuais**, não um relatório completo
do Testing Center ou uma garantia de segurança de produção.

## Limitação de segurança demonstrada

Um preview com a pergunta
`What is the current status of order AUR-1003?`
retornou `Mouse Aurora` e `shipped` **sem verificar a identidade
do consumidor**.

Isso demonstra uma lacuna entre autenticação da integração e autenticação
do cliente. O Approval Guard protege o caminho de Case, mas as ações de
status e elegibilidade ainda dependem de um único cliente sintético fixo.
O identificador `VerifiedCustomerId` no Agent Script é apenas uma variável
reservada; **não é uma identidade autenticada**.

**Não exponha esse agente como canal público de atendimento até
implementar autorização individual no backend e nos Flows.**

## Pendências para evolução

1. Integrar identidade autenticada do consumidor ao canal ou a uma etapa
   confiável de verificação (OTP é uma opção de desenho, **não implementada**).
2. Propagar contexto autenticado protegido contra manipulação pelo agente,
   validar o vínculo cliente–pedido nas duas ações externas e no Flow,
   e vincular aprovações e Cases à identidade verificada.
3. Aplicar comportamento fail-closed a chamadas sem identidade, com
   testes de acesso cruzado, expiração e revogação de sessão.
4. Revisar e versionar, após inspeção, scripts auxiliares locais de
   retrieve, deploy e validação, manifesto e workflow Salesforce CI.
   Eles não fazem parte do marco validado automaticamente.
5. Executar integralmente os
   [12 cenários de avaliação](../evals/scenarios.json), capturar
   evidências/latência, automatizar testes e preparar uma demonstração gravada.
6. Documentar uma implantação reproduzível em uma org limpa, incluindo
   pré-requisitos das credenciais, valores de picklists e dependências da org.

O projeto emprega **dados fictícios**, não usa reembolsos reais e não deve
ser confundido com um serviço de pós-venda em produção.
