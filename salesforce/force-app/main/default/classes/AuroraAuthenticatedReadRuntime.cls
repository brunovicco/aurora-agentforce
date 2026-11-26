/**
 * Internal composition boundary for the future authenticated Salesforce runtime.
 * A linked session identifier is correlation only. The injected authorizer must
 * verify the current authenticated session independently, not trust chat input.
 */
public with sharing class AuroraAuthenticatedReadRuntime {
    public interface SessionAuthorizer {
        Boolean permits(String conversationId, Id executionUserId);
    }

    private final SessionAuthorizer authorizer;
    private final AuroraTrustedContext.BindingResolver resolver;

    public AuroraAuthenticatedReadRuntime(
        SessionAuthorizer authorizer, AuroraTrustedContext.BindingResolver resolver
    ) {
        this.authorizer = authorizer;
        this.resolver = resolver;
    }

    private AuroraVerifiedReadFacade scopedReads(String conversationId) {
        try {
            if (authorizer != null && resolver != null &&
                !String.isBlank(conversationId) && conversationId.length() <= 128 &&
                authorizer.permits(conversationId, UserInfo.getUserId()) == true) {
                return new AuroraVerifiedReadFacade(new AuroraTrustedOrderActions(
                    new AuroraTrustedContext(conversationId, resolver)
                ));
            }
        } catch (Exception ex) {
            // No diagnostics or session material in the returned business result.
        }
        return new AuroraVerifiedReadFacade(null);
    }

    public AuroraVerifiedReadFacade.ReadResult getOrder(
        String trustedConversationId, String orderId
    ) {
        return scopedReads(trustedConversationId).getOrder(orderId);
    }

    public AuroraVerifiedReadFacade.ReadResult checkEligibility(
        String trustedConversationId, String orderId
    ) {
        return scopedReads(trustedConversationId).checkEligibility(orderId);
    }
}
