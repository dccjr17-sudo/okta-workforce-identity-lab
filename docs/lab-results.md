# Configuration and validation

## Identities and groups

| Identity | Initial workforce group | Initial application access |
|---|---|---|
| Alex Employee — alex.employee@example.com | Workforce-Employees | App-Demo-Users |
| Jamie Admin — jamie.admin@example.com | Workforce-Admins | App-Demo-Users |
| Taylor Contractor — taylor.contractor@example.com | Workforce-Contractors | None |

Workforce-Admins had no group-assigned administrator privileges. Jamie's persona does not imply Okta administrative rights. Pre-existing tenant members in Workforce-Employees and Workforce-Admins were retained outside the lab scope.

## MFA and session configuration

| Policy | Group | Settings |
|---|---|---|
| Lab-MFA-Enrollment | App-Demo-Users | Password and Okta Verify required; no grace period; Email disabled; email auto-enrollment off |
| Lab-Contractor-MFA-Enrollment | Workforce-Contractors | Same enrollment requirements |
| Lab-Global-Session | App-Demo-Users | Password and MFA at every sign-in; maximum 8 hours; idle 30 minutes; no persistent cookies |
| Lab-Contractor-Global-Session | Workforce-Contractors | Password and MFA at every sign-in; maximum 4 hours; idle 15 minutes; no persistent cookies |

Contractor policies were reordered to priority 1, other lab policies to 2, and Default Policy to 3. Enrollment rules allow the configured authenticators for Okta and supported applications from any location.

Alex, Jamie, and Taylor completed enrollment and fresh MFA sign-ins. Alex used both TOTP and push; Jamie used push. Taylor's 15-minute idle limit was tested by waiting beyond that interval and observing reauthentication. Alex/Jamie's initial 30-minute idle limit and the 4/8-hour maximum limits were not tested by elapsed time.

## Federation tests

Lab-SAML-Demo uses RSA SAML Test Service Provider with SAML 2.0 and an active SHA-2 certificate. The supplied Sign On configuration lists Any two factors. Alex and Jamie launched it from Okta and received correct NameID, firstname, email, and lastname values. Taylor was initially blocked through the direct app link. SP-initiated SAML was not tested.

Lab-OIDC-Demo is an SPA with no client secret, required PKCE, Authorization Code enabled, Refresh Token/DPoP disabled, and app-initiated login. Redirect URI: https://oidcdebugger.com/debug. Requests used the org authorization server, SHA-256 PKCE, query response mode, and fresh state/nonce/verifier values. Alex's screenshots confirm matching state and token issuance; Jamie's success and ID token were user-reported. Taylor's initial request produced access_denied for missing assignment.

Initial requests used openid profile email. The later Alex mover check used openid only. Token claim and signature validation were not independently tested.

## Manual lifecycle tests

| Scenario | Change | Observed result |
|---|---|---|
| Approved contractor access | Add Taylor to App-Demo-Users | SAML success with correct attributes; OIDC PKCE exchange with ID token |
| Approval removed | Remove Taylor from App-Demo-Users | Fresh SAML and OIDC requests denied for missing assignment |
| Leaver | Deactivate Taylor | Deactivated profile; reported fresh end-user sign-in failed |
| Workforce mover | Move Alex from Employees to Contractors; retain App-Demo-Users | System Log targets contractor MFA/enrollment rules; both federation flows still succeed |

The leaver sign-in screen contains a generic error; it does not independently identify the username/cause. It supports the reported Taylor test alongside his Deactivated status. An earlier Admin Console denial was excluded. Existing external sessions and tokens were not tested for revocation.

Alex's name stayed unchanged to track the same identity. Employee is a fictional surname, not the authoritative workforce classification.

## SCIM create/update/deactivate

SCIM Playground signup/key generation stalled and the account route returned 404. No outage was independently confirmed. A local Python SCIM user-provisioning server replaced that dependency.

Lab-SCIM-Demo uses the SCIM 2.0 Test App (OAuth Bearer Token) template. Credentials tested successfully through a temporary HTTPS tunnel. Create Users, Update User Attributes, and Deactivate Users were enabled; password sync disabled. The app's own SAML login was not configured. App-SCIM-Users was assigned to this app separately from App-Demo-Users.

1. Adding Alex to App-SCIM-Users caused POST /scim/v2/Users to return 201. An authenticated local read showed the correct username/name and active=True.
2. Changing Alex's Okta title to Contractor Analyst appeared in the downstream account with active=True.
3. Removing Alex from App-SCIM-Users left the downstream record present with title retained and active=False.

These prove live Okta-originated provisioning against the lab implementation, not just local unit tests. Local HTTP tests also verified authentication, filtering, duplicate detection, updates, deactivation, pagination, and SQLite persistence.

## Last observed state

- Alex: Active; Everyone, Workforce-Contractors, App-Demo-Users; title Contractor Analyst. Removed from App-SCIM-Users by test instructions; downstream account inactive.
- Jamie: Active with App-Demo-Users approval; workforce-admin lab persona without group-granted administrator privileges.
- Taylor: Deactivated and removed from App-Demo-Users.
- Contractor policy precedence remains above the other lab policies.

## References

- [Okta SCIM 2.0 protocol reference](https://developer.okta.com/docs/api/openapi/okta-scim/guides/scim-20)
- [Okta RSA SAML test-service setup](https://saml-doc.okta.com/SAML_Docs/How-to-Configure-SAML-2.0-for-RSA-SAML-Test-Service-Provider.html)
- [OIDC Debugger](https://oidcdebugger.com/)
- [Okta policy overview](https://help.okta.com/oie/en-us/content/topics/identity-engine/policies/about-policies.htm)
