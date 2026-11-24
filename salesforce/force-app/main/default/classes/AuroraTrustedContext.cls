/**
 * Internal context boundary for an authenticated runtime.
 * No invocable or remote entrypoint. The resolver must be supplied by trusted
 * infrastructure, never by the reasoning model or a customer request.
 */
public with sharing class AuroraTrustedContext {
    public class ContextUnavailableException extends Exception {}

    public class Binding {
        public String conversationId;
        public Id executionUserId;
        public Datetime expiresAt;
        public Boolean revoked;
        private String sessionToken;

        public Binding(String conversationId, Id executionUserId,
                       Datetime expiresAt, Boolean revoked, String sessionToken) {
            this.conversationId = conversationId;
            this.executionUserId = executionUserId;
            this.expiresAt = expiresAt;
            this.revoked = revoked;
            this.sessionToken = sessionToken;
        }

        public String tokenForTrustedCallout() {
            return sessionToken;
        }
    }

    public interface BindingResolver {
        Binding findCurrent(String trustedConversationId, Id executionUserId);
    }

    private final String conversationId;
    private final BindingResolver resolver;

    public AuroraTrustedContext(String trustedConversationId, BindingResolver resolver) {
        this.conversationId = trustedConversationId;
        this.resolver = resolver;
    }

    public String resolveForCallout() {
        try {
            if (String.isBlank(conversationId) || conversationId.length() > 128 ||
                resolver == null) {
                throw new ContextUnavailableException('Customer context unavailable.');
            }
            Id executionUserId = UserInfo.getUserId();
            Binding current = resolver.findCurrent(conversationId, executionUserId);
            if (current == null || !conversationId.equals(current.conversationId) ||
                current.executionUserId != executionUserId || current.revoked != false ||
                current.expiresAt == null || current.expiresAt <= System.now()) {
                throw new ContextUnavailableException('Customer context unavailable.');
            }
            String token = current.tokenForTrustedCallout();
            if (String.isBlank(token) || token.length() > 4096 ||
                !Pattern.matches('^[A-Za-z0-9_-]+[.][A-Za-z0-9_-]+$', token)) {
                throw new ContextUnavailableException('Customer context unavailable.');
            }
            return token;
        } catch (Exception ex) {
            throw new ContextUnavailableException('Customer context unavailable.');
        }
    }
}
