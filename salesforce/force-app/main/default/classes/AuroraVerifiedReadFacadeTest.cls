@IsTest
private class AuroraVerifiedReadFacadeTest {
    private class Resolver implements AuroraTrustedContext.BindingResolver {
        public Boolean revoked = false;

        public AuroraTrustedContext.Binding findCurrent(String conversationId, Id userId) {
            return new AuroraTrustedContext.Binding(
                conversationId, userId, System.now().addMinutes(2), revoked, 'synthetic.payload'
            );
        }
    }

    private class Reply implements HttpCalloutMock {
        private Integer code;
        Reply(Integer code) {
            this.code = code;
        }

        public HttpResponse respond(HttpRequest request) {
            System.assertEquals('synthetic.payload',
                request.getHeader('X-Aurora-Customer-Session'));
            HttpResponse response = new HttpResponse();
            response.setStatusCode(code);
            if (code != 200) {
                response.setBody('{"detail":"private diagnostic"}');
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

    private static AuroraVerifiedReadFacade facade(Resolver resolver) {
        return new AuroraVerifiedReadFacade(new AuroraTrustedOrderActions(
            new AuroraTrustedContext('conversation-1', resolver)
        ));
    }

    private static void assertUnavailable(AuroraVerifiedReadFacade.ReadResult result) {
        System.assertEquals('unavailable', result.outcome);
        System.assertEquals(null, result.order_id);
        System.assertEquals(null, result.product);
        System.assertEquals(null, result.status);
        System.assertEquals(null, result.eligible);
        System.assertEquals(null, result.reason);
        System.assertEquals(null, result.reason_code);
        System.assertEquals(null, result.policy_reference);
        System.assertEquals(null, result.evaluated_on);
    }

    @IsTest static void returnsOnlyBusinessFields() {
        Test.setMock(HttpCalloutMock.class, new Reply(200));
        AuroraVerifiedReadFacade reads = facade(new Resolver());
        AuroraVerifiedReadFacade.ReadResult order = reads.getOrder('AUR-1001');
        System.assertEquals('success', order.outcome);
        System.assertEquals('shipped', order.status);
        System.assertEquals(null, order.eligible);
        AuroraVerifiedReadFacade.ReadResult eligibility = reads.checkEligibility('AUR-1001');
        System.assertEquals('success', eligibility.outcome);
        System.assertEquals(false, eligibility.eligible);
        System.assertEquals(null, eligibility.product);
        System.assert(!JSON.serialize(order).contains('synthetic.payload'));
    }

    @IsTest static void rejectsMissingRevokedAndInvalidContext() {
        Integer calls = Limits.getCallouts();
        AuroraVerifiedReadFacade missing = new AuroraVerifiedReadFacade(null);
        assertUnavailable(missing.getOrder('AUR-1001'));
        assertUnavailable(missing.checkEligibility('AUR-1001'));
        Resolver resolver = new Resolver();
        AuroraVerifiedReadFacade reads = facade(resolver);
        assertUnavailable(reads.getOrder('../health'));
        resolver.revoked = true;
        assertUnavailable(reads.checkEligibility('AUR-1001'));
        System.assertEquals(calls, Limits.getCallouts());
    }

    @IsTest static void hidesBackendDenialDetails() {
        Test.setMock(HttpCalloutMock.class, new Reply(404));
        AuroraVerifiedReadFacade reads = facade(new Resolver());
        assertUnavailable(reads.getOrder('AUR-1001'));
        assertUnavailable(reads.checkEligibility('AUR-1001'));
    }
}
