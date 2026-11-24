/**
 * Internal facade, constructed only by trusted runtime code.
 * Business methods accept only an order ID. No token is returned.
 */
public with sharing class AuroraTrustedOrderActions {
    private final AuroraTrustedContext context;

    public AuroraTrustedOrderActions(AuroraTrustedContext context) {
        this.context = context;
    }

    private String resolveToken() {
        if (context == null) {
            throw new AuroraTrustedContext.ContextUnavailableException(
                'Customer context unavailable.'
            );
        }
        return context.resolveForCallout();
    }

    public AuroraVerifiedOrdersClient.OrderResult getOrder(String orderId) {
        return AuroraVerifiedOrdersClient.getOrder(orderId, resolveToken());
    }

    public AuroraVerifiedOrdersClient.EligibilityResult checkEligibility(String orderId) {
        return AuroraVerifiedOrdersClient.checkEligibility(orderId, resolveToken());
    }

    public AuroraVerifiedOrdersClient.CaseAuthorization authorizeCase(String orderId) {
        return AuroraVerifiedOrdersClient.authorizeCase(orderId, resolveToken());
    }
}
