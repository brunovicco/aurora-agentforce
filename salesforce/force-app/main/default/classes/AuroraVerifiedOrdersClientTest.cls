@IsTest
private class AuroraVerifiedOrdersClientTest {
    private static final String TOKEN = 'synthetic.payload';

    private class Reply implements HttpCalloutMock {
        private String suffix;
        private Integer statusCode;
        private String body;

        Reply(String suffix, Integer statusCode, String body) {
            this.suffix = suffix;
            this.statusCode = statusCode;
            this.body = body;
        }

        public HttpResponse respond(HttpRequest request) {
            System.assertEquals('GET', request.getMethod());
            System.assertEquals(
                'callout:AuroraOrders/verified/orders/AUR-1001' + suffix,
                request.getEndpoint()
            );
            System.assertEquals(TOKEN, request.getHeader('X-Aurora-Customer-Session'));
            HttpResponse response = new HttpResponse();
            response.setStatusCode(statusCode);
            response.setBody(body);
            return response;
        }
    }

    @IsTest static void readsOrder() {
        Test.setMock(HttpCalloutMock.class, new Reply('', 200,
            '{"order_id":"AUR-1001","product":"Demo","status":"shipped"}'));
        System.assertEquals('shipped',
            AuroraVerifiedOrdersClient.getOrder('AUR-1001', TOKEN).status);
    }

    @IsTest static void readsEligibility() {
        Test.setMock(HttpCalloutMock.class, new Reply('/return-eligibility', 200,
            '{"order_id":"AUR-1001","eligible":false,"reason_code":"NOT_DELIVERED",'+
            '"reason":"Not delivered","policy_reference":"DEMO","evaluated_on":"2026-11-05"}'));
        System.assertEquals(false,
            AuroraVerifiedOrdersClient.checkEligibility('AUR-1001', TOKEN).eligible);
    }

    @IsTest static void readsCaseOwnershipEvidence() {
        Test.setMock(HttpCalloutMock.class, new Reply('/case-authorization', 200,
            '{"order_id":"AUR-1001","request_key":"customer-demo-001:AUR-1001:post-sale"}'));
        System.assertEquals('customer-demo-001:AUR-1001:post-sale',
            AuroraVerifiedOrdersClient.authorizeCase('AUR-1001', TOKEN).request_key);
    }

    @IsTest static void rejectsInvalidInputBeforeCallout() {
        Integer beforeCalls = Limits.getCallouts();
        for (String orderId : new List<String>{null, '../health', 'AUR-12345'}) {
            try {
                AuroraVerifiedOrdersClient.getOrder(orderId, TOKEN);
                System.assert(false, 'Expected denial');
            } catch (AuroraVerifiedOrdersClient.UnavailableException ex) {
                System.assertEquals('Order unavailable.', ex.getMessage());
            }
        }
        for (String token : new List<String>{null, '', 'invalid', 'abc.def.ghi'}) {
            try {
                AuroraVerifiedOrdersClient.getOrder('AUR-1001', token);
                System.assert(false, 'Expected denial');
            } catch (AuroraVerifiedOrdersClient.UnavailableException ex) {
                System.assertEquals('Order unavailable.', ex.getMessage());
            }
        }
        System.assertEquals(beforeCalls, Limits.getCallouts());
    }

    @IsTest static void rejectsBackendDenial() {
        Test.setMock(HttpCalloutMock.class, new Reply('', 401, '{"detail":"private diagnostic"}'));
        try {
            AuroraVerifiedOrdersClient.getOrder('AUR-1001', TOKEN);
            System.assert(false, 'Expected denial');
        } catch (AuroraVerifiedOrdersClient.UnavailableException ex) {
            System.assertEquals('Order unavailable.', ex.getMessage());
        }
    }

    @IsTest static void rejectsMismatchedOrder() {
        Test.setMock(HttpCalloutMock.class, new Reply('', 200,
            '{"order_id":"AUR-9001","product":"Demo","status":"shipped"}'));
        try {
            AuroraVerifiedOrdersClient.getOrder('AUR-1001', TOKEN);
            System.assert(false, 'Expected denial');
        } catch (AuroraVerifiedOrdersClient.UnavailableException ex) {
            System.assertEquals('Order unavailable.', ex.getMessage());
        }
    }

    @IsTest static void rejectsMismatchedCaseKey() {
        Test.setMock(HttpCalloutMock.class, new Reply('/case-authorization', 200,
            '{"order_id":"AUR-1001","request_key":"customer-demo-001:AUR-9001:post-sale"}'));
        try {
            AuroraVerifiedOrdersClient.authorizeCase('AUR-1001', TOKEN);
            System.assert(false, 'Expected denial');
        } catch (AuroraVerifiedOrdersClient.UnavailableException ex) {
            System.assertEquals('Order unavailable.', ex.getMessage());
        }
    }

    @IsTest static void rejectsMalformedEligibility() {
        Test.setMock(HttpCalloutMock.class, new Reply('/return-eligibility', 200,
            '{"order_id":"AUR-1001","eligible":true}'));
        try {
            AuroraVerifiedOrdersClient.checkEligibility('AUR-1001', TOKEN);
            System.assert(false, 'Expected denial');
        } catch (AuroraVerifiedOrdersClient.UnavailableException ex) {
            System.assertEquals('Order unavailable.', ex.getMessage());
        }
    }
}
