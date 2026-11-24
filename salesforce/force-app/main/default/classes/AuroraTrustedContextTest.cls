@IsTest
private class AuroraTrustedContextTest {
    private class Resolver implements AuroraTrustedContext.BindingResolver {
        public AuroraTrustedContext.Binding current;
        public Integer reads = 0;

        public AuroraTrustedContext.Binding findCurrent(String conversationId, Id userId) {
            reads++;
            System.assertEquals('conversation-1', conversationId);
            System.assertEquals(UserInfo.getUserId(), userId);
            return current;
        }
    }

    private class Reply implements HttpCalloutMock {
        public HttpResponse respond(HttpRequest request) {
            System.assertEquals('synthetic.payload',
                request.getHeader('X-Aurora-Customer-Session'));
            HttpResponse response = new HttpResponse();
            response.setStatusCode(200);
            if (request.getEndpoint().endsWith('/case-authorization')) {
                response.setBody(
                    '{"order_id":"AUR-1001","request_key":"customer-demo-001:AUR-1001:post-sale"}'
                );
            } else if (request.getEndpoint().endsWith('/return-eligibility')) {
                response.setBody('{"order_id":"AUR-1001","eligible":false,' +
                    '"reason_code":"NOT_DELIVERED","reason":"Demo","policy_reference":"DEMO",' +
                    '"evaluated_on":"2026-11-05"}');
            } else {
                response.setBody('{"order_id":"AUR-1001","product":"Demo","status":"shipped"}');
            }
            return response;
        }
    }

    private static AuroraTrustedContext.Binding validBinding() {
        return new AuroraTrustedContext.Binding('conversation-1', UserInfo.getUserId(),
            System.now().addMinutes(5), false, 'synthetic.payload');
    }

    private static void assertDenied(AuroraTrustedOrderActions actions) {
        Integer calls = Limits.getCallouts();
        try {
            actions.getOrder('AUR-1001');
            System.assert(false, 'Expected context denial');
        } catch (AuroraTrustedContext.ContextUnavailableException ex) {
            System.assertEquals('Customer context unavailable.', ex.getMessage());
        }
        System.assertEquals(calls, Limits.getCallouts());
    }

    @IsTest static void resolvesEveryOperationAndRevocation() {
        Resolver resolver = new Resolver();
        resolver.current = validBinding();
        AuroraTrustedOrderActions actions = new AuroraTrustedOrderActions(
            new AuroraTrustedContext('conversation-1', resolver)
        );
        Test.setMock(HttpCalloutMock.class, new Reply());
        System.assertEquals('shipped', actions.getOrder('AUR-1001').status);
        System.assertEquals(false, actions.checkEligibility('AUR-1001').eligible);
        System.assertEquals('customer-demo-001:AUR-1001:post-sale',
            actions.authorizeCase('AUR-1001').request_key);
        System.assertEquals(3, resolver.reads);
        resolver.current.revoked = true;
        assertDenied(actions);
        System.assertEquals(4, resolver.reads);
    }

    @IsTest static void deniesMissingOrMismatchedBinding() {
        Resolver resolver = new Resolver();
        AuroraTrustedOrderActions actions = new AuroraTrustedOrderActions(
            new AuroraTrustedContext('conversation-1', resolver)
        );
        assertDenied(actions);
        resolver.current = validBinding();
        resolver.current.conversationId = 'conversation-2';
        assertDenied(actions);
        resolver.current = validBinding();
        resolver.current.executionUserId = null;
        assertDenied(actions);
        resolver.current = validBinding();
        resolver.current.expiresAt = System.now().addSeconds(-1);
        assertDenied(actions);
        resolver.current = validBinding();
        resolver.current.revoked = null;
        assertDenied(actions);
    }

    @IsTest static void deniesUnconfiguredContext() {
        assertDenied(new AuroraTrustedOrderActions(null));
        assertDenied(new AuroraTrustedOrderActions(new AuroraTrustedContext(null, null)));
    }
}
