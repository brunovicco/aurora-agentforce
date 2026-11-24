@IsTest
private class AuroraBrokerBindingResolverTest {
    private class Reply implements HttpCalloutMock {
        private Integer statusCode;
        private String mode;
        Reply(Integer statusCode, String mode) {
            this.statusCode = statusCode;
            this.mode = mode;
        }
        public HttpResponse respond(HttpRequest request) {
            System.assertEquals('callout:AuroraContextBroker/v1/context/resolve',
                request.getEndpoint());
            System.assertEquals('POST', request.getMethod());
            Map<String, Object> payload =
                (Map<String, Object>) JSON.deserializeUntyped(request.getBody());
            System.assertEquals(2, payload.size());
            System.assertEquals('conversation-1', payload.get('conversation_id'));
            System.assertEquals(String.valueOf(UserInfo.getUserId()),
                payload.get('execution_user_id'));
            HttpResponse response = new HttpResponse();
            response.setStatusCode(statusCode);
            if (mode == 'malformed') {
                response.setBody('not-json');
                return response;
            }
            response.setBody(JSON.serialize(new Map<String, Object>{
                'conversation_id' => mode == 'wrong-conversation' ? 'conversation-2' : 'conversation-1',
                'execution_user_id' => mode == 'wrong-user' ? 'other' : String.valueOf(UserInfo.getUserId()),
                'expires_at' => mode == 'expired' ? System.now().addSeconds(-1) : System.now().addMinutes(2),
                'revoked' => mode == 'revoked',
                'session_token' => mode == 'bad-token' ? 'invalid' : 'synthetic.payload'
            }));
            return response;
        }
    }

    @IsTest static void resolvesThroughSeparateBrokerCredential() {
        Test.setMock(HttpCalloutMock.class, new Reply(200, 'valid'));
        AuroraTrustedContext context = new AuroraTrustedContext(
            'conversation-1', new AuroraBrokerBindingResolver()
        );
        System.assertEquals('synthetic.payload', context.resolveForCallout());
    }

    @IsTest static void rejectsMissingRuntimeContextBeforeCallout() {
        Integer calls = Limits.getCallouts();
        AuroraBrokerBindingResolver resolver = new AuroraBrokerBindingResolver();
        System.assertEquals(null, resolver.findCurrent(null, UserInfo.getUserId()));
        System.assertEquals(null, resolver.findCurrent('conversation-1', null));
        System.assertEquals(calls, Limits.getCallouts());
    }

    @IsTest static void rejectsUntrustedBrokerResponses() {
        AuroraBrokerBindingResolver resolver = new AuroraBrokerBindingResolver();
        for (String mode : new List<String>{
            'wrong-conversation', 'wrong-user', 'expired', 'revoked', 'bad-token', 'malformed'
        }) {
            Test.setMock(HttpCalloutMock.class, new Reply(200, mode));
            System.assertEquals(null,
                resolver.findCurrent('conversation-1', UserInfo.getUserId()), mode);
        }
        for (Integer statusCode : new List<Integer>{401, 403, 404, 503}) {
            Test.setMock(HttpCalloutMock.class, new Reply(statusCode, 'valid'));
            System.assertEquals(null,
                resolver.findCurrent('conversation-1', UserInfo.getUserId()));
        }
    }
}
