/**
 * Candidate read action boundary. Not invocable until an authenticated runtime
 * supplies the current conversation and an independently authorized resolver.
 */
public with sharing class AuroraVerifiedReadFacade {
    public class ReadResult {
        public String outcome;
        public String order_id;
        public String product;
        public String status;
        public Boolean eligible;
        public String reason;
        public String reason_code;
        public String policy_reference;
        public Date evaluated_on;
    }

    private final AuroraTrustedOrderActions actions;

    public AuroraVerifiedReadFacade(AuroraTrustedOrderActions actions) {
        this.actions = actions;
    }

    private static ReadResult unavailable() {
        ReadResult result = new ReadResult();
        result.outcome = 'unavailable';
        return result;
    }

    private static Boolean validOrder(String orderId) {
        return !String.isBlank(orderId) && Pattern.matches('^AUR-[0-9]{4}$', orderId);
    }

    public ReadResult getOrder(String orderId) {
        if (actions == null || !validOrder(orderId)) {
            return unavailable();
        }
        try {
            AuroraVerifiedOrdersClient.OrderResult order = actions.getOrder(orderId);
            ReadResult result = new ReadResult();
            result.outcome = 'success';
            result.order_id = order.order_id;
            result.product = order.product;
            result.status = order.status;
            return result;
        } catch (Exception ex) {
            return unavailable();
        }
    }

    public ReadResult checkEligibility(String orderId) {
        if (actions == null || !validOrder(orderId)) {
            return unavailable();
        }
        try {
            AuroraVerifiedOrdersClient.EligibilityResult eligibility =
                actions.checkEligibility(orderId);
            ReadResult result = new ReadResult();
            result.outcome = 'success';
            result.order_id = eligibility.order_id;
            result.eligible = eligibility.eligible;
            result.reason = eligibility.reason;
            result.reason_code = eligibility.reason_code;
            result.policy_reference = eligibility.policy_reference;
            result.evaluated_on = eligibility.evaluated_on;
            return result;
        } catch (Exception ex) {
            return unavailable();
        }
    }
}
