/**
 * Concrete internal resolver for a separately authenticated context broker.
 * The broker must independently authorize the exact runtime conversation.
 * A Named Credential is integration authentication, not customer authentication.
 */
public with sharing class AuroraBrokerBindingResolver
    implements AuroraTrustedContext.BindingResolver {

    private class BrokerReply {
        public String conversation_id;
        public String execution_user_id;
        public Datetime expires_at;
        public Boolean revoked;
        public String session_token;
    }

    public AuroraTrustedContext.Binding findCurrent(String trustedConversationId, Id executionUserId) {
        if (String.isBlank(trustedConversationId) || trustedConversationId.length() > 128 ||
            executionUserId == null || executionUserId != UserInfo.getUserId()) {
            return null;
        }
        try {
            HttpRequest request = new HttpRequest();
            request.setEndpoint('callout:AuroraContextBroker/v1/context/resolve');
            request.setMethod('POST');
            request.setTimeout(10000);
            request.setHeader('Content-Type', 'application/json');
            request.setHeader('Accept', 'application/json');
            request.setBody(JSON.serialize(new Map<String, String>{
                'conversation_id' => trustedConversationId,
                'execution_user_id' => String.valueOf(executionUserId)
            }));
            HttpResponse response = new Http().send(request);
            if (response.getStatusCode() != 200 || String.isBlank(response.getBody()) ||
                response.getBody().length() > 16384) {
                return null;
            }
            BrokerReply reply = (BrokerReply) JSON.deserializeStrict(
                response.getBody(), BrokerReply.class
            );
            if (reply == null || !trustedConversationId.equals(reply.conversation_id) ||
                !String.valueOf(executionUserId).equals(reply.execution_user_id) ||
                reply.revoked != false || reply.expires_at == null ||
                reply.expires_at <= System.now() || String.isBlank(reply.session_token) ||
                reply.session_token.length() > 4096 ||
                !Pattern.matches('^[A-Za-z0-9_-]+[.][A-Za-z0-9_-]+$', reply.session_token)) {
                return null;
            }
            return new AuroraTrustedContext.Binding(
                trustedConversationId, executionUserId, reply.expires_at,
                reply.revoked, reply.session_token
            );
        } catch (Exception ex) {
            return null;
        }
    }
}
