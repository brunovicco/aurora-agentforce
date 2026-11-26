@IsTest
private class AuroraExecutionIdentityProbeTest {

    @IsTest
    static void portalIdentity() {
        AuroraExecutionIdentityProbe.Result result =
            AuroraExecutionIdentityProbe.inspect(
                UserInfo.getUserId(),
                'CspLitePortal'
            );

        System.assertEquals(
            true, result.executionUserIdPresent
        );
        System.assertEquals(
            true, result.executionUserNotGuest
        );
        System.assertEquals(
            true,
            result.executionUserIsExpectedPortalType
        );
    }

    @IsTest
    static void standardIdentity() {
        AuroraExecutionIdentityProbe.Result result =
            AuroraExecutionIdentityProbe.inspect(
                UserInfo.getUserId(),
                'Standard'
            );

        System.assertEquals(
            true, result.executionUserNotGuest
        );
        System.assertEquals(
            false,
            result.executionUserIsExpectedPortalType
        );
    }

    @IsTest
    static void guestIdentity() {
        AuroraExecutionIdentityProbe.Result result =
            AuroraExecutionIdentityProbe.inspect(
                UserInfo.getUserId(),
                'Guest'
            );

        System.assertEquals(
            false, result.executionUserNotGuest
        );
        System.assertEquals(
            false,
            result.executionUserIsExpectedPortalType
        );
    }

    @IsTest
    static void missingIdentity() {
        AuroraExecutionIdentityProbe.Result result =
            AuroraExecutionIdentityProbe.inspect(
                null,
                'CspLitePortal'
            );

        System.assertEquals(
            false, result.executionUserIdPresent
        );
        System.assertEquals(
            false, result.executionUserNotGuest
        );
        System.assertEquals(
            false,
            result.executionUserIsExpectedPortalType
        );
    }

    @IsTest
    static void missingUserType() {
        AuroraExecutionIdentityProbe.Result result =
            AuroraExecutionIdentityProbe.inspect(
                UserInfo.getUserId(),
                null
            );

        System.assertEquals(
            false, result.executionUserNotGuest
        );
    }

    @IsTest
    static void invocableUsesPlatformIdentity() {
        List<AuroraExecutionIdentityProbe.Result> results =
            AuroraExecutionIdentityProbe.run(
                new List<AuroraExecutionIdentityProbe.Request>{
                    new AuroraExecutionIdentityProbe.Request(),
                    new AuroraExecutionIdentityProbe.Request()
                }
            );

        System.assertEquals(2, results.size());

        for (
            AuroraExecutionIdentityProbe.Result result
            : results
        ) {
            System.assertEquals(
                true, result.executionUserIdPresent
            );

            System.assertEquals(
                UserInfo.getUserType() == 'CspLitePortal',
                result.executionUserIsExpectedPortalType
            );
        }
    }

    @IsTest
    static void nullRequests() {
        System.assertEquals(
            0,
            AuroraExecutionIdentityProbe.run(null).size()
        );
    }

    @IsTest
    static void emptyRequests() {
        System.assertEquals(
            0,
            AuroraExecutionIdentityProbe.run(
                new List<AuroraExecutionIdentityProbe.Request>()
            ).size()
        );
    }
}
