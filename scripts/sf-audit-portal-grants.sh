#!/usr/bin/env bash
set -euo pipefail
[[ $# == 1 ]] || { echo 'Usage: sf-audit-portal-grants.sh ORG_ALIAS' >&2; exit 2; }
root=$(cd "$(dirname "$0")/.." && pwd)
umask 077
private_dir=$(mktemp -d)
trap 'rm -rf -- "$private_dir"' EXIT
cd "$root/salesforce"
query() {
  sf data query --target-org "$1" --json --query "$2" > "$3"
}
query "$1" "SELECT Id, ProfileId, ContactId, IsActive, IsPortalEnabled, Profile.Name, Contact.FirstName, Contact.LastName, Contact.AccountId, Contact.Account.Name FROM User WHERE Contact.Account.Name IN ('Aurora Demo Account A', 'Aurora Demo Account B')" "$private_dir/users.json"
query "$1" "SELECT Name, GuestUserId, GuestUser.Id, GuestUser.ProfileId, GuestUser.UserType FROM Site WHERE Name = 'Aurora_Customer_Portal'" "$private_dir/sites.json"
query "$1" "SELECT Id, ProfileId, IsOwnedByProfile FROM PermissionSet WHERE IsOwnedByProfile = true" "$private_dir/profiles.json"
query "$1" "SELECT AssigneeId, PermissionSetId, PermissionSetGroupId FROM PermissionSetAssignment WHERE Assignee.Contact.Account.Name IN ('Aurora Demo Account A', 'Aurora Demo Account B') OR Assignee.UserType = 'Guest'" "$private_dir/assignments.json"
query "$1" "SELECT ParentId, SObjectType, PermissionsRead, PermissionsCreate, PermissionsEdit, PermissionsDelete, PermissionsViewAllRecords, PermissionsModifyAllRecords FROM ObjectPermissions WHERE SObjectType IN ('Account', 'Contact', 'User', 'Case', 'AuroraCaseApproval__c', 'Order', 'MessagingSession', 'MessagingEndUser')" "$private_dir/grants.json"
query "$1" "SELECT ParentId, SObjectType, Field, PermissionsRead, PermissionsEdit FROM FieldPermissions WHERE SObjectType IN ('Account', 'Contact', 'User', 'Case', 'AuroraCaseApproval__c', 'Order', 'MessagingSession', 'MessagingEndUser')" "$private_dir/fields.json"
query "$1" "SELECT Id, PermissionsViewAllData, PermissionsModifyAllData, PermissionsManageUsers FROM PermissionSet" "$private_dir/system.json"
cd "$root"
uv run python -m scripts.portal_grant_inventory "$private_dir"
