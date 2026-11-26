public with sharing class AuroraExecutionIdentityProbe {

    public class Request {
        @InvocableVariable(
            label='Run execution diagnostics'
        )
        public Boolean requested;
    }

    public class Result {
        @InvocableVariable
        public Boolean executionUserIdPresent;

        @InvocableVariable
        public Boolean executionUserNotGuest;

        @InvocableVariable
        public Boolean executionUserIsExpectedPortalType;
    }

    @TestVisible
    private static Result inspect(
        Id executionUserId,
        String executionUserType
    ) {
        Result result = new Result();

        result.executionUserIdPresent =
            executionUserId != null;

        result.executionUserNotGuest =
            executionUserId != null &&
            !String.isBlank(executionUserType) &&
            executionUserType != 'Guest';

        result.executionUserIsExpectedPortalType =
            executionUserId != null &&
            executionUserType == 'CspLitePortal';

        return result;
    }

    @InvocableMethod(
        label='Inspect Execution Identity'
        description='Isolated execution identity diagnostics.'
    )
    public static List<Result> run(
        List<Request> requests
    ) {
        List<Result> results = new List<Result>();

        if (requests == null) {
            return results;
        }

        for (Request request : requests) {
            Result result = inspect(
                UserInfo.getUserId(),
                UserInfo.getUserType()
            );

            System.debug(
                LoggingLevel.INFO,
                'AURORA_EXECUTION_PROBE_V2' +
                '|userIdPresent=' +
                result.executionUserIdPresent +
                '|notGuest=' +
                result.executionUserNotGuest +
                '|expectedPortalType=' +
                result.executionUserIsExpectedPortalType
            );

            results.add(result);
        }

        return results;
    }
}
