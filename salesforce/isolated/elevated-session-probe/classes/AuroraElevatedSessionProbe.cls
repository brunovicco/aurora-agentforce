public with sharing class AuroraElevatedSessionProbe {

    private static final String EXPECTED_CHANNEL_NAME =
        'Aurora_Authenticated_Chat';

    private static final String SCOPED_SOQL =
        'SELECT Id FROM MessagingSession ' +
        'WHERE Id = :sessionId ' +
        'AND MessagingEndUser.AuthenticatedEndUserId = :actorId ' +
        'AND MessagingChannel.DeveloperName = :channelName ' +
        'AND MessagingChannel.IsActive = true ' +
        'AND Status = \'Active\' ' +
        'AND ConversationId != null LIMIT 1';

    public class Request {
        @InvocableVariable(
            label='Platform messaging session'
            required=true
        )
        public String messagingSessionId;
    }

    public class Result {
        @InvocableVariable
        public Boolean sessionBindingConsistent;
    }

    public interface Matcher {
        Boolean matchSession(
            Id sessionId,
            Id actorId
        );
    }

    private with sharing class NativeMatcher
        implements Matcher {

        public Boolean matchSession(
            Id sessionId,
            Id actorId
        ) {
            List<SObject> rows = Database.queryWithBinds(
                SCOPED_SOQL,
                new Map<String, Object>{
                    'sessionId' => sessionId,
                    'actorId' => actorId,
                    'channelName' => EXPECTED_CHANNEL_NAME
                },
                AccessLevel.SYSTEM_MODE
            );

            return rows.size() == 1 &&
                (Id) rows[0].get('Id') == sessionId;
        }
    }

    private without sharing class ElevatedMatcher
        implements Matcher {

        public Boolean matchSession(
            Id sessionId,
            Id actorId
        ) {
            List<SObject> rows = Database.queryWithBinds(
                SCOPED_SOQL,
                new Map<String, Object>{
                    'sessionId' => sessionId,
                    'actorId' => actorId,
                    'channelName' => EXPECTED_CHANNEL_NAME
                },
                AccessLevel.SYSTEM_MODE
            );

            return rows.size() == 1 &&
                (Id) rows[0].get('Id') == sessionId;
        }
    }

    @TestVisible
    private static Matcher nativeMatcher() {
        return new NativeMatcher();
    }

    @TestVisible
    private static Matcher elevatedMatcher() {
        return new ElevatedMatcher();
    }

    @TestVisible
    private static List<String> compare(
        String sessionReference,
        Id actorId,
        String actorType,
        Matcher baselineMatcher,
        Matcher privilegedMatcher
    ) {
        String baseline = inspect(
            sessionReference,
            actorId,
            actorType,
            baselineMatcher
        );

        String elevated = 'NOT_RUN';

        if (baseline == 'NO_MATCH') {
            elevated = inspect(
                sessionReference,
                actorId,
                actorType,
                privilegedMatcher
            );
        }

        return new List<String>{
            baseline,
            elevated
        };
    }

    @TestVisible
    private static String inspect(
        String sessionReference,
        Id actorId,
        String actorType,
        Matcher matcher
    ) {
        if (actorId == null ||
            actorType != 'CspLitePortal') {
            return 'UNEXPECTED_EXECUTION_IDENTITY';
        }

        if (String.isBlank(sessionReference) ||
            matcher == null) {
            return 'MISSING_CONTEXT';
        }

        if (!Pattern.matches(
            '^[A-Za-z0-9]{15}([A-Za-z0-9]{3})?$',
            sessionReference
        )) {
            return 'INVALID_REFERENCE';
        }

        Id sessionId;

        try {
            sessionId = Id.valueOf(sessionReference);
        } catch (Exception ex) {
            return 'INVALID_REFERENCE';
        }

        try {
            Boolean matched = matcher.matchSession(
                sessionId,
                actorId
            );

            return matched == true
                ? 'CONSISTENT'
                : 'NO_MATCH';

        } catch (Exception ex) {
            return 'SCOPED_LOOKUP_ERROR';
        }
    }

    @InvocableMethod(
        label='Inspect Scoped Session Binding'
        description='Isolated session consistency diagnostics.'
    )
    public static List<Result> run(
        List<Request> requests
    ) {
        List<Result> results = new List<Result>();

        if (requests == null) {
            return results;
        }

        for (Request request : requests) {

            String outcome = 'MISSING_CONTEXT';
            String baselineOutcome = 'NOT_RUN';
            String elevatedOutcome = 'NOT_RUN';

            if (requests.size() != 1) {
                outcome = 'UNSUPPORTED_BATCH';

            } else if (request != null) {
                List<String> comparison = compare(
                    request.messagingSessionId,
                    UserInfo.getUserId(),
                    UserInfo.getUserType(),
                    nativeMatcher(),
                    elevatedMatcher()
                );

                baselineOutcome = comparison[0];
                elevatedOutcome = comparison[1];

                outcome = baselineOutcome == 'NO_MATCH'
                    ? elevatedOutcome
                    : baselineOutcome;
            }

            Result result = new Result();

            result.sessionBindingConsistent =
                outcome == 'CONSISTENT';

            System.debug(
                LoggingLevel.INFO,
                'AURORA_ELEVATED_SESSION_PROBE_V1' +
                ' consistent=' +
                result.sessionBindingConsistent +
                ' outcome=' + outcome +
                ' baseline=' + baselineOutcome +
                ' elevated=' + elevatedOutcome
            );

            results.add(result);
        }

        return results;
    }
}
