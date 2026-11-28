@IsTest
private class AuroraScopedSessionProbeTest {

    private static final Id USER_A =
        '005000000000001';

    private static final Id USER_B =
        '005000000000002';

    private static final Id SESSION_A =
        '001000000000001';

    private static final Id SESSION_B =
        '001000000000002';

    private class MockLookupException extends Exception {}

    private class MockMatcher
        implements AuroraScopedSessionProbe.Matcher {

        public Integer calls = 0;
        public Boolean failLookup = false;
        public Boolean nullResult = false;

        public Id observedActor;
        public Id observedSession;

        public Map<Id, Id> owners =
            new Map<Id, Id>{
                SESSION_A => USER_A,
                SESSION_B => USER_B
            };

        public Boolean matchSession(
            Id sessionId,
            Id actorId
        ) {
            calls++;
            observedActor = actorId;
            observedSession = sessionId;

            if (failLookup) {
                throw new MockLookupException();
            }

            if (nullResult) {
                return null;
            }

            return owners.get(sessionId) == actorId;
        }
    }

    private static String inspect(
        Id sessionId,
        Id actorId,
        MockMatcher matcher
    ) {
        return AuroraScopedSessionProbe.inspect(
            String.valueOf(sessionId),
            actorId,
            'CspLitePortal',
            matcher
        );
    }

    @IsTest
    static void aliceOwnSession() {
        MockMatcher matcher = new MockMatcher();

        System.assertEquals(
            'CONSISTENT',
            inspect(SESSION_A, USER_A, matcher)
        );

        System.assertEquals(1, matcher.calls);
        System.assertEquals(USER_A, matcher.observedActor);
        System.assertEquals(
            SESSION_A, matcher.observedSession
        );
    }

    @IsTest
    static void bobOwnSession() {
        System.assertEquals(
            'CONSISTENT',
            inspect(
                SESSION_B,
                USER_B,
                new MockMatcher()
            )
        );
    }

    @IsTest
    static void crossCustomerDeniedBothDirections() {
        MockMatcher matcher = new MockMatcher();

        System.assertEquals(
            'NO_MATCH',
            inspect(SESSION_A, USER_B, matcher)
        );

        System.assertEquals(
            'NO_MATCH',
            inspect(SESSION_B, USER_A, matcher)
        );
    }

    @IsTest
    static void guestDeniedBeforeQuery() {
        MockMatcher matcher = new MockMatcher();

        System.assertEquals(
            'UNEXPECTED_EXECUTION_IDENTITY',
            AuroraScopedSessionProbe.inspect(
                String.valueOf(SESSION_A),
                USER_A,
                'Guest',
                matcher
            )
        );

        System.assertEquals(0, matcher.calls);
    }

    @IsTest
    static void sharedAgentDeniedBeforeQuery() {
        MockMatcher matcher = new MockMatcher();

        System.assertEquals(
            'UNEXPECTED_EXECUTION_IDENTITY',
            AuroraScopedSessionProbe.inspect(
                String.valueOf(SESSION_A),
                USER_A,
                'Standard',
                matcher
            )
        );

        System.assertEquals(0, matcher.calls);
    }

    @IsTest
    static void missingActorDenied() {
        MockMatcher matcher = new MockMatcher();

        System.assertEquals(
            'UNEXPECTED_EXECUTION_IDENTITY',
            AuroraScopedSessionProbe.inspect(
                String.valueOf(SESSION_A),
                null,
                'CspLitePortal',
                matcher
            )
        );

        System.assertEquals(0, matcher.calls);
    }

    @IsTest
    static void missingContextDenied() {
        MockMatcher matcher = new MockMatcher();

        System.assertEquals(
            'MISSING_CONTEXT',
            AuroraScopedSessionProbe.inspect(
                null,
                USER_A,
                'CspLitePortal',
                matcher
            )
        );

        System.assertEquals(0, matcher.calls);
    }

    @IsTest
    static void missingMatcherDenied() {
        System.assertEquals(
            'MISSING_CONTEXT',
            AuroraScopedSessionProbe.inspect(
                String.valueOf(SESSION_A),
                USER_A,
                'CspLitePortal',
                null
            )
        );
    }

    @IsTest
    static void malformedReferenceDenied() {
        MockMatcher matcher = new MockMatcher();

        System.assertEquals(
            'INVALID_REFERENCE',
            AuroraScopedSessionProbe.inspect(
                'invalid',
                USER_A,
                'CspLitePortal',
                matcher
            )
        );

        System.assertEquals(0, matcher.calls);
    }

    @IsTest
    static void noMatchingSessionDenied() {
        MockMatcher matcher = new MockMatcher();

        matcher.owners.clear();

        System.assertEquals(
            'NO_MATCH',
            inspect(SESSION_A, USER_A, matcher)
        );
    }

    @IsTest
    static void nullMatchDenied() {
        MockMatcher matcher = new MockMatcher();

        matcher.nullResult = true;

        System.assertEquals(
            'NO_MATCH',
            inspect(SESSION_A, USER_A, matcher)
        );
    }

    @IsTest
    static void lookupExceptionDenied() {
        MockMatcher matcher = new MockMatcher();

        matcher.failLookup = true;

        System.assertEquals(
            'SCOPED_LOOKUP_ERROR',
            inspect(SESSION_A, USER_A, matcher)
        );
    }

    @IsTest
    static void nativeMatcherRejectsUnrelatedId() {
        String outcome =
            AuroraScopedSessionProbe.inspect(
                String.valueOf(UserInfo.getUserId()),
                UserInfo.getUserId(),
                'CspLitePortal',
                AuroraScopedSessionProbe.nativeMatcher()
            );

        System.assert(
            new Set<String>{
                'NO_MATCH',
                'SCOPED_LOOKUP_ERROR'
            }.contains(outcome),
            'Native lookup must not accept unrelated IDs.'
        );
    }

    @IsTest
    static void nullRequestDenied() {
        List<AuroraScopedSessionProbe.Result> results =
            AuroraScopedSessionProbe.run(
                new List<AuroraScopedSessionProbe.Request>{
                    null
                }
            );

        System.assertEquals(1, results.size());

        System.assertEquals(
            false,
            results[0].sessionBindingConsistent
        );
    }

    @IsTest
    static void batchDenied() {
        List<AuroraScopedSessionProbe.Result> results =
            AuroraScopedSessionProbe.run(
                new List<AuroraScopedSessionProbe.Request>{
                    new AuroraScopedSessionProbe.Request(),
                    new AuroraScopedSessionProbe.Request()
                }
            );

        System.assertEquals(2, results.size());

        for (AuroraScopedSessionProbe.Result item : results) {
            System.assertEquals(
                false,
                item.sessionBindingConsistent
            );
        }
    }

    @IsTest
    static void singleMalformedRequestDenied() {
        AuroraScopedSessionProbe.Request request =
            new AuroraScopedSessionProbe.Request();

        request.messagingSessionId = 'invalid';

        List<AuroraScopedSessionProbe.Result> results =
            AuroraScopedSessionProbe.run(
                new List<AuroraScopedSessionProbe.Request>{
                    request
                }
            );

        System.assertEquals(1, results.size());

        System.assertEquals(
            false,
            results[0].sessionBindingConsistent
        );
    }

    @IsTest
    static void emptyAndNullRequests() {
        System.assertEquals(
            0,
            AuroraScopedSessionProbe.run(null).size()
        );

        System.assertEquals(
            0,
            AuroraScopedSessionProbe.run(
                new List<AuroraScopedSessionProbe.Request>()
            ).size()
        );
    }
}
