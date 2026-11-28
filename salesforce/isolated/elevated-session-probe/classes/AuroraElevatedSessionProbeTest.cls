@IsTest
private class AuroraElevatedSessionProbeTest {

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
        implements AuroraElevatedSessionProbe.Matcher {

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
        return AuroraElevatedSessionProbe.inspect(
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
            AuroraElevatedSessionProbe.inspect(
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
            AuroraElevatedSessionProbe.inspect(
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
            AuroraElevatedSessionProbe.inspect(
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
            AuroraElevatedSessionProbe.inspect(
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
            AuroraElevatedSessionProbe.inspect(
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
            AuroraElevatedSessionProbe.inspect(
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
            AuroraElevatedSessionProbe.inspect(
                String.valueOf(UserInfo.getUserId()),
                UserInfo.getUserId(),
                'CspLitePortal',
                AuroraElevatedSessionProbe.nativeMatcher()
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
        List<AuroraElevatedSessionProbe.Result> results =
            AuroraElevatedSessionProbe.run(
                new List<AuroraElevatedSessionProbe.Request>{
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
        List<AuroraElevatedSessionProbe.Result> results =
            AuroraElevatedSessionProbe.run(
                new List<AuroraElevatedSessionProbe.Request>{
                    new AuroraElevatedSessionProbe.Request(),
                    new AuroraElevatedSessionProbe.Request()
                }
            );

        System.assertEquals(2, results.size());

        for (AuroraElevatedSessionProbe.Result item : results) {
            System.assertEquals(
                false,
                item.sessionBindingConsistent
            );
        }
    }

    @IsTest
    static void singleMalformedRequestDenied() {
        AuroraElevatedSessionProbe.Request request =
            new AuroraElevatedSessionProbe.Request();

        request.messagingSessionId = 'invalid';

        List<AuroraElevatedSessionProbe.Result> results =
            AuroraElevatedSessionProbe.run(
                new List<AuroraElevatedSessionProbe.Request>{
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
            AuroraElevatedSessionProbe.run(null).size()
        );

        System.assertEquals(
            0,
            AuroraElevatedSessionProbe.run(
                new List<AuroraElevatedSessionProbe.Request>()
            ).size()
        );
    }

    @IsTest
    static void elevationAfterBaselineNoMatch() {
        MockMatcher baseline = new MockMatcher();
        baseline.owners.clear();

        MockMatcher elevated = new MockMatcher();

        List<String> result =
            AuroraElevatedSessionProbe.compare(
                String.valueOf(SESSION_A),
                USER_A,
                'CspLitePortal',
                baseline,
                elevated
            );

        System.assertEquals(
            new List<String>{
                'NO_MATCH', 'CONSISTENT'
            },
            result
        );

        System.assertEquals(1, baseline.calls);
        System.assertEquals(1, elevated.calls);

        System.assertEquals(
            baseline.observedActor,
            elevated.observedActor
        );

        System.assertEquals(
            baseline.observedSession,
            elevated.observedSession
        );
    }

    @IsTest
    static void noElevationAfterBaselineSuccess() {
        MockMatcher baseline = new MockMatcher();
        MockMatcher elevated = new MockMatcher();

        System.assertEquals(
            new List<String>{
                'CONSISTENT', 'NOT_RUN'
            },
            AuroraElevatedSessionProbe.compare(
                String.valueOf(SESSION_A),
                USER_A,
                'CspLitePortal',
                baseline,
                elevated
            )
        );

        System.assertEquals(0, elevated.calls);
    }

    @IsTest
    static void noElevationAfterBaselineError() {
        MockMatcher baseline = new MockMatcher();
        baseline.failLookup = true;

        MockMatcher elevated = new MockMatcher();

        System.assertEquals(
            new List<String>{
                'SCOPED_LOOKUP_ERROR', 'NOT_RUN'
            },
            AuroraElevatedSessionProbe.compare(
                String.valueOf(SESSION_A),
                USER_A,
                'CspLitePortal',
                baseline,
                elevated
            )
        );

        System.assertEquals(0, elevated.calls);
    }

    @IsTest
    static void crossCustomerDeniedAfterElevation() {
        MockMatcher baseline = new MockMatcher();
        baseline.owners.clear();

        MockMatcher elevated = new MockMatcher();

        System.assertEquals(
            new List<String>{
                'NO_MATCH', 'NO_MATCH'
            },
            AuroraElevatedSessionProbe.compare(
                String.valueOf(SESSION_B),
                USER_A,
                'CspLitePortal',
                baseline,
                elevated
            )
        );

        System.assertEquals(1, elevated.calls);
    }

    @IsTest
    static void unexpectedIdentityNeverElevates() {
        MockMatcher baseline = new MockMatcher();
        MockMatcher elevated = new MockMatcher();

        System.assertEquals(
            new List<String>{
                'UNEXPECTED_EXECUTION_IDENTITY',
                'NOT_RUN'
            },
            AuroraElevatedSessionProbe.compare(
                String.valueOf(SESSION_A),
                USER_A,
                'Guest',
                baseline,
                elevated
            )
        );

        System.assertEquals(0, baseline.calls);
        System.assertEquals(0, elevated.calls);
    }

    @IsTest
    static void privilegedLookupExceptionDenied() {
        MockMatcher baseline = new MockMatcher();
        baseline.owners.clear();

        MockMatcher elevated = new MockMatcher();
        elevated.failLookup = true;

        System.assertEquals(
            new List<String>{
                'NO_MATCH', 'SCOPED_LOOKUP_ERROR'
            },
            AuroraElevatedSessionProbe.compare(
                String.valueOf(SESSION_A),
                USER_A,
                'CspLitePortal',
                baseline,
                elevated
            )
        );
    }

    @IsTest
    static void nativeElevationRejectsUnrelatedId() {
        String outcome =
            AuroraElevatedSessionProbe.inspect(
                String.valueOf(UserInfo.getUserId()),
                UserInfo.getUserId(),
                'CspLitePortal',
                AuroraElevatedSessionProbe.elevatedMatcher()
            );

        System.assert(
            new Set<String>{
                'NO_MATCH',
                'SCOPED_LOOKUP_ERROR'
            }.contains(outcome)
        );
    }

}
