public with sharing class AuroraIdentityProbe {

    public interface SessionProvider {
        Map<String, String> current();
    }

    private class SalesforceSessionProvider
        implements SessionProvider {

        public Map<String, String> current() {
            return Auth.SessionManagement.getCurrentSession();
        }
    }

    @TestVisible
    private static SessionProvider sessionProvider =
        new SalesforceSessionProvider();


    public class Request {
        @InvocableVariable
        public Boolean requested;
    }

    public class Result {
        @InvocableVariable
        public Boolean sessionPresent;

        @InvocableVariable
        public Boolean sessionUserMatchesExecutionUser;

        @InvocableVariable
        public Boolean executionUserNotGuest;
    }

    @TestVisible
    private static Result evaluate(
        Id executionUserId,
        String executionUserType,
        Map<String, String> session
    ) {
        Result result = new Result();

        result.sessionPresent = false;
        result.sessionUserMatchesExecutionUser = false;

        result.executionUserNotGuest =
            executionUserId != null &&
            !String.isBlank(executionUserType) &&
            !'Guest'.equalsIgnoreCase(executionUserType);

        if (session == null) {
            return result;
        }

        result.sessionPresent =
            !String.isBlank(session.get('SessionId'));

        try {
            String sessionUser = session.get('UsersId');

            if (
                result.sessionPresent &&
                !String.isBlank(sessionUser) &&
                executionUserId != null
            ) {
                result.sessionUserMatchesExecutionUser =
                    (Id) sessionUser == executionUserId;
            }
        } catch (Exception ex) {
            result.sessionUserMatchesExecutionUser = false;
        }

        return result;
    }

    @InvocableMethod(
        label='Aurora Identity Probe'
        description='Read-only session context diagnostics.'
    )
    public static List<Result> inspect(
        List<Request> requests
    ) {
        List<Result> results = new List<Result>();

        if (requests == null || requests.isEmpty()) {
            return results;
        }

        Map<String, String> session;

        try {
            session = sessionProvider == null
                ? null
                : sessionProvider.current();
        } catch (Exception ex) {
            session = null;
        }

        for (Request ignored : requests) {
            results.add(evaluate(
                UserInfo.getUserId(),
                UserInfo.getUserType(),
                session
            ));
        }

        return results;
    }
}
