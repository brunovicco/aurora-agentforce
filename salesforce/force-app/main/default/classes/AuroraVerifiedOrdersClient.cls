/**
 * Internal callout client. Never expose sessionToken as an Agentforce or Flow input.
 * A trusted runtime caller must establish the current customer/conversation binding.
 * The Orders API independently validates signature, expiry and ownership.
 */
public with sharing class AuroraVerifiedOrdersClient {
    public class UnavailableException extends Exception {}

    private static final Set<String> ORDER_STATUSES = new Set<String>{
        'processing', 'shipped', 'delivered', 'cancelled'
    };

    public class OrderResult {
        public String order_id;
        public String product;
        public String status;
    }

    public class EligibilityResult {
        public String order_id;
        public Boolean eligible;
        public String reason_code;
        public String reason;
        public String policy_reference;
        public Date evaluated_on;
    }

    public class CaseAuthorization {
        public String order_id;
        public String request_key;
    }

    public static OrderResult getOrder(String orderId, String sessionToken) {
        try {
            OrderResult result = (OrderResult) JSON.deserializeStrict(
                fetch(orderId, sessionToken, ''), OrderResult.class
            );
            if (result == null || !orderId.equals(result.order_id) ||
                String.isBlank(result.product) ||
                !ORDER_STATUSES.contains(result.status)) {
                throw new UnavailableException('Order unavailable.');
            }
            return result;
        } catch (Exception ex) {
            throw new UnavailableException('Order unavailable.');
        }
    }

    public static EligibilityResult checkEligibility(String orderId, String sessionToken) {
        try {
            EligibilityResult result = (EligibilityResult) JSON.deserializeStrict(
                fetch(orderId, sessionToken, '/return-eligibility'), EligibilityResult.class
            );
            if (result == null || !orderId.equals(result.order_id) || result.eligible == null ||
                String.isBlank(result.reason_code) || String.isBlank(result.reason) ||
                String.isBlank(result.policy_reference) || result.evaluated_on == null) {
                throw new UnavailableException('Order unavailable.');
            }
            return result;
        } catch (Exception ex) {
            throw new UnavailableException('Order unavailable.');
        }
    }

    // Ownership evidence only. Does not create a Case or substitute for approval.
    public static CaseAuthorization authorizeCase(String orderId, String sessionToken) {
        try {
            CaseAuthorization result = (CaseAuthorization) JSON.deserializeStrict(
                fetch(orderId, sessionToken, '/case-authorization'), CaseAuthorization.class
            );
            if (result == null || !orderId.equals(result.order_id) ||
                String.isBlank(result.request_key) || result.request_key.length() > 100 ||
                !Pattern.matches(
                    '^(customer-demo-00[12]:' + orderId + ':post-sale|v1:[0-9a-f]{64})$',
                    result.request_key
                )) {
                throw new UnavailableException('Order unavailable.');
            }
            return result;
        } catch (Exception ex) {
            throw new UnavailableException('Order unavailable.');
        }
    }

    private static String fetch(String orderId, String sessionToken, String suffix) {
        if (String.isBlank(orderId) || !Pattern.matches('^AUR-[0-9]{4}$', orderId) ||
            String.isBlank(sessionToken) || sessionToken.length() > 4096 ||
            !Pattern.matches('^[A-Za-z0-9_-]+[.][A-Za-z0-9_-]+$', sessionToken)) {
            throw new UnavailableException('Order unavailable.');
        }
        HttpRequest request = new HttpRequest();
        request.setEndpoint('callout:AuroraOrders/verified/orders/' + orderId + suffix);
        request.setMethod('GET');
        request.setTimeout(10000);
        request.setHeader('Accept', 'application/json');
        request.setHeader('X-Aurora-Customer-Session', sessionToken);
        HttpResponse response = new Http().send(request);
        if (response.getStatusCode() != 200 || String.isBlank(response.getBody()) ||
            response.getBody().length() > 16384) {
            throw new UnavailableException('Order unavailable.');
        }
        return response.getBody();
    }
}
