@IsTest
private class AuroraIdentityProbeTest {

    private class ProviderFailureException extends Exception {}

    private class MockSessionProvider
        implements AuroraIdentityProbe.SessionProvider {

        private Map<String, String> payload;
        private Boolean shouldFail;

        public MockSessionProvider(
            Map<String, String> payload,
            Boolean shouldFail
        ) {
            this.payload = payload;
            this.shouldFail = shouldFail;
        }

        public Map<String, String> current() {
            if (shouldFail == true) {
                throw new ProviderFailureException(
                    'Synthetic provider failure.'
                );
            }

            return payload;
        }
    }


    @IsTest
    static void missingSession() {
        AuroraIdentityProbe.Result result =
            AuroraIdentityProbe.evaluate(
                UserInfo.getUserId(),
                'Standard',
                null
            );

        System.assertEquals(false, result.sessionPresent);
        System.assertEquals(
            false,
            result.sessionUserMatchesExecutionUser
        );
    }

    @IsTest
    static void matchingSession() {
        Map<String, String> session =
            new Map<String, String>{
                'SessionId' => 'synthetic',
                'UsersId' => String.valueOf(
                    UserInfo.getUserId()
                )
            };

        AuroraIdentityProbe.Result result =
            AuroraIdentityProbe.evaluate(
                UserInfo.getUserId(),
                'Standard',
                session
            );

        System.assertEquals(true, result.sessionPresent);
        System.assertEquals(
            true,
            result.sessionUserMatchesExecutionUser
        );
    }

    @IsTest
    static void missingSessionIdentifier() {
        AuroraIdentityProbe.Result result =
            AuroraIdentityProbe.evaluate(
                UserInfo.getUserId(),
                'Standard',
                new Map<String, String>{
                    'UsersId' => String.valueOf(
                        UserInfo.getUserId()
                    )
                }
            );

        System.assertEquals(false, result.sessionPresent);
        System.assertEquals(
            false,
            result.sessionUserMatchesExecutionUser
        );
    }

    @IsTest
    static void mismatchedSessionUser() {
        AuroraIdentityProbe.Result result =
            AuroraIdentityProbe.evaluate(
                UserInfo.getUserId(),
                'Standard',
                new Map<String, String>{
                    'SessionId' => 'synthetic',
                    'UsersId' => '005000000000001'
                }
            );

        System.assertEquals(true, result.sessionPresent);
        System.assertEquals(
            false,
            result.sessionUserMatchesExecutionUser
        );
    }

    @IsTest
    static void malformedSessionUser() {
        AuroraIdentityProbe.Result result =
            AuroraIdentityProbe.evaluate(
                UserInfo.getUserId(),
                'Standard',
                new Map<String, String>{
                    'SessionId' => 'synthetic',
                    'UsersId' => 'invalid'
                }
            );

        System.assertEquals(
            false,
            result.sessionUserMatchesExecutionUser
        );
    }

    @IsTest
    static void guestContext() {
        AuroraIdentityProbe.Result result =
            AuroraIdentityProbe.evaluate(
                UserInfo.getUserId(),
                'Guest',
                null
            );

        System.assertEquals(
            false,
            result.executionUserNotGuest
        );
    }

    @IsTest
    static void invocableContract() {
        System.assertEquals(
            0,
            AuroraIdentityProbe.inspect(null).size()
        );

        List<AuroraIdentityProbe.Request> requests =
            new List<AuroraIdentityProbe.Request>{
                new AuroraIdentityProbe.Request(),
                new AuroraIdentityProbe.Request()
            };

        AuroraIdentityProbe.sessionProvider =
            new MockSessionProvider(
                new Map<String, String>{
                    'SessionId' => 'synthetic',
                    'UsersId' => String.valueOf(
                        UserInfo.getUserId()
                    )
                },
                false
            );

        Test.startTest();

        List<AuroraIdentityProbe.Result> results =
            AuroraIdentityProbe.inspect(requests);

        Test.stopTest();

        System.assertEquals(2, results.size());

        for (AuroraIdentityProbe.Result result : results) {
            System.assertEquals(true, result.sessionPresent);
            System.assertEquals(
                true,
                result.sessionUserMatchesExecutionUser
            );
        }

        System.assertEquals(
            results[0].sessionPresent,
            results[1].sessionPresent
        );
        System.assertEquals(
            results[0].sessionUserMatchesExecutionUser,
            results[1].sessionUserMatchesExecutionUser
        );
    }

    @IsTest
    static void invocableMissingSession() {
        AuroraIdentityProbe.sessionProvider =
            new MockSessionProvider(null, false);

        List<AuroraIdentityProbe.Result> results =
            AuroraIdentityProbe.inspect(
                new List<AuroraIdentityProbe.Request>{
                    new AuroraIdentityProbe.Request()
                }
            );

        System.assertEquals(1, results.size());
        System.assertEquals(false, results[0].sessionPresent);
        System.assertEquals(
            false,
            results[0].sessionUserMatchesExecutionUser
        );
    }

    @IsTest
    static void invocableProviderFailure() {
        AuroraIdentityProbe.sessionProvider =
            new MockSessionProvider(null, true);

        List<AuroraIdentityProbe.Result> results =
            AuroraIdentityProbe.inspect(
                new List<AuroraIdentityProbe.Request>{
                    new AuroraIdentityProbe.Request()
                }
            );

        System.assertEquals(1, results.size());
        System.assertEquals(false, results[0].sessionPresent);
        System.assertEquals(
            false,
            results[0].sessionUserMatchesExecutionUser
        );
    }
}
