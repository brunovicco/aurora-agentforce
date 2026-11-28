public with sharing class AuroraConversationBindingProbe {

    private static final String EXPECTED_CHANNEL_DEVELOPER_NAME =
        'Aurora_Authenticated_Chat';

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

    public interface Reader {
        Map<String, Object> read(
            String kind, Id recordId
        );
    }

    private class NativeReader implements Reader {

        public Map<String, Object> read(
            String kind, Id recordId
        ) {
            String soql;

            if (kind == 'session') {
                soql =
                    'SELECT Id, Status, ConversationId, ' +
                    'MessagingChannelId, MessagingEndUserId ' +
                    'FROM MessagingSession';
            } else if (kind == 'endUser') {
                soql =
                    'SELECT Id, AuthenticatedEndUserId, ' +
                    'MessagingChannelId FROM MessagingEndUser';
            } else if (kind == 'channel') {
                soql =
                    'SELECT Id, DeveloperName, IsActive ' +
                    'FROM MessagingChannel';
            } else if (kind == 'conversation') {
                soql = 'SELECT Id FROM Conversation';
            } else {
                return null;
            }

            List<SObject> rows = Database.queryWithBinds(
                soql + ' WHERE Id = :recordId LIMIT 1',
                new Map<String, Object>{
                    'recordId' => recordId
                },
                AccessLevel.USER_MODE
            );

            return rows.isEmpty()
                ? null
                : rows[0].getPopulatedFieldsAsMap();
        }
    }

    @TestVisible
    private static Reader nativeReader() {
        return new NativeReader();
    }

    @TestVisible
    private static String inspect(
        String sessionReference,
        Id executionUserId,
        String executionUserType,
        Reader reader
    ) {
        if (executionUserId == null ||
            executionUserType != 'CspLitePortal') {
            return 'UNEXPECTED_EXECUTION_IDENTITY';
        }

        if (String.isBlank(sessionReference) ||
            reader == null) {
            return 'MISSING_CONTEXT';
        }

        if (!Pattern.matches(
            '^[A-Za-z0-9]{15}([A-Za-z0-9]{3})?$',
            sessionReference
        )) {
            return 'INVALID_REFERENCE';
        }

        String stage = 'SESSION';

        try {
            Id sessionId = Id.valueOf(sessionReference);

            Map<String, Object> session =
                reader.read('session', sessionId);

            if (session == null ||
                (Id) session.get('Id') != sessionId) {
                return 'SESSION_UNAVAILABLE';
            }

            if ((String) session.get('Status') != 'Active') {
                return 'SESSION_NOT_ACTIVE';
            }

            Id channelId =
                (Id) session.get('MessagingChannelId');

            Id endUserId =
                (Id) session.get('MessagingEndUserId');

            Id conversationId =
                (Id) session.get('ConversationId');

            if (channelId == null ||
                endUserId == null ||
                conversationId == null) {
                return 'INCOMPLETE_CONTEXT';
            }

            stage = 'END_USER';

            Map<String, Object> endUser =
                reader.read('endUser', endUserId);

            if (endUser == null ||
                (Id) endUser.get('Id') != endUserId ||
                (Id) endUser.get('AuthenticatedEndUserId')
                    != executionUserId ||
                (Id) endUser.get('MessagingChannelId')
                    != channelId) {
                return 'IDENTITY_BINDING_UNAVAILABLE';
            }

            stage = 'CHANNEL';

            Map<String, Object> channel =
                reader.read('channel', channelId);

            if (channel == null ||
                (Id) channel.get('Id') != channelId ||
                (String) channel.get('DeveloperName')
                    != EXPECTED_CHANNEL_DEVELOPER_NAME ||
                (Boolean) channel.get('IsActive') != true) {
                return 'CHANNEL_UNAVAILABLE';
            }

            stage = 'CONVERSATION';

            Map<String, Object> conversation =
                reader.read('conversation', conversationId);

            if (conversation == null ||
                (Id) conversation.get('Id') != conversationId) {
                return 'CONVERSATION_UNAVAILABLE';
            }

            return 'CONSISTENT';

        } catch (Exception ex) {
            return stage + '_LOOKUP_ERROR';
        }
    }

    @InvocableMethod(
        label='Inspect Conversation Binding'
        description='Isolated read-only binding diagnostics.'
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

            // This diagnostic accepts one action request.
            if (requests.size() != 1) {
                outcome = 'UNSUPPORTED_BATCH';
            } else if (request != null) {
                outcome = inspect(
                    request.messagingSessionId,
                    UserInfo.getUserId(),
                    UserInfo.getUserType(),
                    nativeReader()
                );
            }

            Result result = new Result();

            result.sessionBindingConsistent =
                outcome == 'CONSISTENT';

            System.debug(
                LoggingLevel.INFO,
                'AURORA_CONVERSATION_PROBE_V1' +
                '|consistent=' +
                result.sessionBindingConsistent +
                '|outcome=' + outcome
            );

            results.add(result);
        }

        return results;
    }
}
