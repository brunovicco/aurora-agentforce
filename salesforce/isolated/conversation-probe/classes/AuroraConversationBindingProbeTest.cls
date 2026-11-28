@IsTest
private class AuroraConversationBindingProbeTest {

    private static final Id USER_A =
        '005000000000001';

    private static final Id USER_B =
        '005000000000002';

    private static final Id SESSION_ID =
        '001000000000001';

    private static final Id CHANNEL_ID =
        '001000000000002';

    private static final Id END_USER_ID =
        '001000000000003';

    private static final Id CONVERSATION_ID =
        '001000000000004';

    private class MockFailureException extends Exception {}

    private class MockReader
        implements AuroraConversationBindingProbe.Reader {

        public String failingKind;
        public Integer calls = 0;

        public Map<String, Map<String, Object>> records =
            new Map<String, Map<String, Object>>{
                'session' => new Map<String, Object>{
                    'Id' => SESSION_ID,
                    'Status' => 'Active',
                    'MessagingChannelId' => CHANNEL_ID,
                    'MessagingEndUserId' => END_USER_ID,
                    'ConversationId' => CONVERSATION_ID
                },
                'endUser' => new Map<String, Object>{
                    'Id' => END_USER_ID,
                    'AuthenticatedEndUserId' => USER_A,
                    'MessagingChannelId' => CHANNEL_ID
                },
                'channel' => new Map<String, Object>{
                    'Id' => CHANNEL_ID,
                    'DeveloperName' => 'Aurora_Authenticated_Chat',
                    'IsActive' => true
                },
                'conversation' => new Map<String, Object>{
                    'Id' => CONVERSATION_ID
                }
            };

        public Map<String, Object> read(
            String kind, Id recordId
        ) {
            calls++;

            if (kind == failingKind) {
                throw new MockFailureException();
            }

            Map<String, Object> row = records.get(kind);

            return row != null &&
                (Id) row.get('Id') == recordId
                ? row : null;
        }
    }

    private static String inspect(
        Id actor, MockReader reader
    ) {
        return AuroraConversationBindingProbe.inspect(
            String.valueOf(SESSION_ID),
            actor,
            'CspLitePortal',
            reader
        );
    }

    @IsTest
    static void matchingIdentity() {
        System.assertEquals(
            'CONSISTENT',
            inspect(USER_A, new MockReader())
        );
    }

    @IsTest
    static void crossCustomerDenied() {
        MockReader reader = new MockReader();

        System.assertEquals(
            'IDENTITY_BINDING_UNAVAILABLE',
            inspect(USER_B, reader)
        );

        System.assertEquals(2, reader.calls);
    }

    @IsTest
    static void guestDeniedBeforeLookup() {
        MockReader reader = new MockReader();

        System.assertEquals(
            'UNEXPECTED_EXECUTION_IDENTITY',
            AuroraConversationBindingProbe.inspect(
                String.valueOf(SESSION_ID),
                USER_A, 'Guest', reader
            )
        );

        System.assertEquals(0, reader.calls);
    }

    @IsTest
    static void sharedAgentDenied() {
        System.assertEquals(
            'UNEXPECTED_EXECUTION_IDENTITY',
            AuroraConversationBindingProbe.inspect(
                String.valueOf(SESSION_ID),
                USER_A, 'Standard', new MockReader()
            )
        );
    }

    @IsTest
    static void missingContextDenied() {
        System.assertEquals(
            'MISSING_CONTEXT',
            AuroraConversationBindingProbe.inspect(
                null, USER_A,
                'CspLitePortal', new MockReader()
            )
        );
    }

    @IsTest
    static void malformedReferenceDenied() {
        System.assertEquals(
            'INVALID_REFERENCE',
            AuroraConversationBindingProbe.inspect(
                'invalid', USER_A,
                'CspLitePortal', new MockReader()
            )
        );
    }

    @IsTest
    static void missingSessionDenied() {
        MockReader reader = new MockReader();
        reader.records.remove('session');

        System.assertEquals(
            'SESSION_UNAVAILABLE',
            inspect(USER_A, reader)
        );
    }

    @IsTest
    static void endedSessionDenied() {
        MockReader reader = new MockReader();
        reader.records.get('session').put(
            'Status', 'Ended'
        );

        System.assertEquals(
            'SESSION_NOT_ACTIVE',
            inspect(USER_A, reader)
        );
    }

    @IsTest
    static void missingAuthenticatedUserDenied() {
        MockReader reader = new MockReader();

        reader.records.get('endUser').remove(
            'AuthenticatedEndUserId'
        );

        System.assertEquals(
            'IDENTITY_BINDING_UNAVAILABLE',
            inspect(USER_A, reader)
        );
    }

    @IsTest
    static void wrongChannelDenied() {
        MockReader reader = new MockReader();

        reader.records.get('channel').put(
            'DeveloperName', 'Other_Channel'
        );

        System.assertEquals(
            'CHANNEL_UNAVAILABLE',
            inspect(USER_A, reader)
        );
    }

    @IsTest
    static void mismatchedEndUserChannelDenied() {
        MockReader reader = new MockReader();

        reader.records.get('endUser').put(
            'MessagingChannelId', SESSION_ID
        );

        System.assertEquals(
            'IDENTITY_BINDING_UNAVAILABLE',
            inspect(USER_A, reader)
        );
    }

    @IsTest
    static void inactiveChannelDenied() {
        MockReader reader = new MockReader();

        reader.records.get('channel').put(
            'IsActive', false
        );

        System.assertEquals(
            'CHANNEL_UNAVAILABLE',
            inspect(USER_A, reader)
        );
    }

    @IsTest
    static void missingConversationDenied() {
        MockReader reader = new MockReader();
        reader.records.remove('conversation');

        System.assertEquals(
            'CONVERSATION_UNAVAILABLE',
            inspect(USER_A, reader)
        );
    }

    @IsTest
    static void lookupFailureDenied() {
        MockReader reader = new MockReader();
        reader.failingKind = 'session';

        System.assertEquals(
            'SESSION_LOOKUP_ERROR',
            inspect(USER_A, reader)
        );
    }

    @IsTest
    static void bulkRequestsDenied() {
        List<AuroraConversationBindingProbe.Result> results =
            AuroraConversationBindingProbe.run(
                new List<AuroraConversationBindingProbe.Request>{
                    new AuroraConversationBindingProbe.Request(),
                    new AuroraConversationBindingProbe.Request()
                }
            );

        System.assertEquals(2, results.size());

        for (AuroraConversationBindingProbe.Result item : results) {
            System.assertEquals(
                false, item.sessionBindingConsistent
            );
        }
    }

    @IsTest
    static void nullRequests() {
        System.assertEquals(
            0,
            AuroraConversationBindingProbe.run(null).size()
        );
    }

    @IsTest
    static void nativeReaderDoesNotResolveUnrelatedId() {
        AuroraConversationBindingProbe.Reader reader =
            AuroraConversationBindingProbe.nativeReader();

        for (String kind : new List<String>{
            'session', 'endUser', 'channel', 'conversation'
        }) {
            try {
                Map<String, Object> result =
                    reader.read(kind, UserInfo.getUserId());

                System.assertEquals(
                    null, result,
                    'Unrelated User ID must not resolve: ' + kind
                );
            } catch (QueryException ex) {
                // USER_MODE can reject inaccessible objects.
                System.assertEquals(
                    false,
                    String.isBlank(ex.getMessage())
                );
            }
        }
    }

    @IsTest
    static void nativeReaderRejectsUnsupportedKind() {
        AuroraConversationBindingProbe.Reader reader =
            AuroraConversationBindingProbe.nativeReader();

        System.assertEquals(
            null,
            reader.read('unsupported', USER_A)
        );
    }

    @IsTest
    static void incompleteReferencesDenied() {
        for (String fieldName : new List<String>{
            'MessagingChannelId',
            'MessagingEndUserId',
            'ConversationId'
        }) {
            MockReader reader = new MockReader();
            reader.records.get('session').remove(fieldName);

            System.assertEquals(
                'INCOMPLETE_CONTEXT',
                inspect(USER_A, reader),
                fieldName
            );

            System.assertEquals(1, reader.calls);
        }
    }

    @IsTest
    static void missingRelatedRecordsDenied() {
        Map<String, String> expected =
            new Map<String, String>{
                'endUser' => 'IDENTITY_BINDING_UNAVAILABLE',
                'channel' => 'CHANNEL_UNAVAILABLE',
                'conversation' => 'CONVERSATION_UNAVAILABLE'
            };

        for (String kind : expected.keySet()) {
            MockReader reader = new MockReader();
            reader.records.remove(kind);

            System.assertEquals(
                expected.get(kind),
                inspect(USER_A, reader)
            );
        }
    }

    @IsTest
    static void relatedLookupFailuresDenied() {
        Map<String, String> expected =
            new Map<String, String>{
                'endUser' => 'END_USER_LOOKUP_ERROR',
                'channel' => 'CHANNEL_LOOKUP_ERROR',
                'conversation' => 'CONVERSATION_LOOKUP_ERROR'
            };

        for (String kind : expected.keySet()) {
            MockReader reader = new MockReader();
            reader.failingKind = kind;

            System.assertEquals(
                expected.get(kind),
                inspect(USER_A, reader)
            );
        }
    }

    @IsTest
    static void missingExecutionIdentityAndReaderDenied() {
        MockReader reader = new MockReader();

        System.assertEquals(
            'UNEXPECTED_EXECUTION_IDENTITY',
            AuroraConversationBindingProbe.inspect(
                String.valueOf(SESSION_ID),
                null,
                'CspLitePortal',
                reader
            )
        );

        System.assertEquals(0, reader.calls);

        System.assertEquals(
            'MISSING_CONTEXT',
            AuroraConversationBindingProbe.inspect(
                String.valueOf(SESSION_ID),
                USER_A,
                'CspLitePortal',
                null
            )
        );
    }

    @IsTest
    static void nullRequestDenied() {
        List<AuroraConversationBindingProbe.Result> results =
            AuroraConversationBindingProbe.run(
                new List<AuroraConversationBindingProbe.Request>{
                    null
                }
            );

        System.assertEquals(1, results.size());
        System.assertEquals(
            false, results[0].sessionBindingConsistent
        );
    }

    @IsTest
    static void malformedSingleRequestDenied() {
        AuroraConversationBindingProbe.Request request =
            new AuroraConversationBindingProbe.Request();

        request.messagingSessionId = 'invalid';

        List<AuroraConversationBindingProbe.Result> results =
            AuroraConversationBindingProbe.run(
                new List<AuroraConversationBindingProbe.Request>{
                    request
                }
            );

        System.assertEquals(1, results.size());
        System.assertEquals(
            false, results[0].sessionBindingConsistent
        );
    }

    @IsTest
    static void emptyRequestsReturnEmptyResults() {
        System.assertEquals(
            0,
            AuroraConversationBindingProbe.run(
                new List<AuroraConversationBindingProbe.Request>()
            ).size()
        );
    }

}
