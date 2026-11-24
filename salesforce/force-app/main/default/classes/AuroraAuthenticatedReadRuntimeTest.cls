@IsTest
private class AuroraAuthenticatedReadRuntimeTest {
    private class Authorizer implements AuroraAuthenticatedReadRuntime.SessionAuthorizer {
        public Boolean allowed = true;
        public Boolean fail = false;
        public Integer checks = 0;

        public Boolean permits(String conversationId, Id executionUserId) {
            checks++;
            System.assertEquals(UserInfo.getUserId(), executionUserId);
            if (fail) {
                throw new AuroraTrustedContext.ContextUnavailableException('private diagnostic');
            }
            return allowed && conversationId == 'conversation-1';
        }
    }

    private class Resolver implements AuroraTrustedContext.BindingResolver {
        public Integer reads = 0;

        public AuroraTrustedContext.Binding findCurrent(String conversationId, Id userId) {
            reads++;
            return new AuroraTrustedContext.Binding(
                conversationId, userId, System.now().addMinutes(2), false, 'synthetic.payload'
            );
        }
    }

    private class Reply implements HttpCalloutMock {
        public HttpResponse respond(HttpRequest request) {
            System.assertEquals('synthetic.payload',
                request.getHeader('X-Aurora-Customer-Session'));
            HttpResponse response = new HttpResponse();
            response.setStatusCode(200);
            if (request.getEndpoint().endsWith('/return-eligibility')) {
                response.setBody('{"order_id":"AUR-1001","eligible":false,' +
                    '"reason_code":"NOT_DELIVERED","reason":"Demo","policy_reference":"DEMO",' +
                    '"evaluated_on":"2026-11-05"}');
            } else {
                response.setBody('{"order_id":"AUR-1001","product":"Demo","status":"shipped"}');
            }
            return response;
        }
    }

    @IsTest static void reauthorizesEveryOperation() {
        Authorizer auth = new Authorizer();
        Resolver resolver = new Resolver();
        AuroraAuthenticatedReadRuntime runtime =
            new AuroraAuthenticatedReadRuntime(auth, resolver);
        Test.setMock(HttpCalloutMock.class, new Reply());
        System.assertEquals('success', runtime.getOrder('conversation-1', 'AUR-1001').outcome);
        System.assertEquals('success',
            runtime.checkEligibility('conversation-1', 'AUR-1001').outcome);
        auth.allowed = false;
        Integer calls = Limits.getCallouts();
        System.assertEquals('unavailable',
            runtime.getOrder('conversation-1', 'AUR-1001').outcome);
        System.assertEquals(3, auth.checks);
        System.assertEquals(2, resolver.reads);
        System.assertEquals(calls, Limits.getCallouts());
    }

    @IsTest static void rejectsCrossConversationAndAuthorizerFailure() {
        Authorizer auth = new Authorizer();
        Resolver resolver = new Resolver();
        AuroraAuthenticatedReadRuntime runtime =
            new AuroraAuthenticatedReadRuntime(auth, resolver);
        Integer calls = Limits.getCallouts();
        System.assertEquals('unavailable',
            runtime.getOrder('conversation-2', 'AUR-1001').outcome);
        auth.fail = true;
        System.assertEquals('unavailable',
            runtime.checkEligibility('conversation-1', 'AUR-1001').outcome);
        System.assertEquals(0, resolver.reads);
        System.assertEquals(calls, Limits.getCallouts());
    }

    @IsTest static void deniesUnconfiguredRuntime() {
        Resolver resolver = new Resolver();
        AuroraAuthenticatedReadRuntime runtime =
            new AuroraAuthenticatedReadRuntime(null, resolver);
        System.assertEquals('unavailable',
            runtime.getOrder('conversation-1', 'AUR-1001').outcome);
        System.assertEquals(0, resolver.reads);
    }
}
