# Evidence index

These are selected user-supplied lab screenshots. Captured views use fictional identities or supplied redactions. Some cropped views omit context; they should be interpreted with the documented test procedure. Token-result images with visible fragments were excluded from this publication package.

| Evidence | What it supports |
|---|---|
| [Fictional users](01-fictional-users.png) | Three users initially staged |
| [No group administrator privileges](01-no-group-admin-privileges.png) | Supplied Workforce-Admins role inspection; group heading cropped |
| [Enrollment policy](02-enrollment-policy.png) | Required authenticators, App-Demo-Users scope, active rule |
| [Session rule](02-session-rule.png) | MFA frequency and configured session limits |
| [Required enrollment](02-required-enrollment.png) | Alex prompted for Okta Verify |
| [Jamie's MFA options](02-jamie-mfa-methods.png) | Code and push choices |
| [Alex SAML attributes](03-alex-saml-attributes.png) | Fictional identity attributes received |
| [Jamie SAML success](03-jamie-saml-success.png) | Successful federation with expected NameID |
| [OIDC unassigned denial](04-unassigned-denial.png) | Taylor test; assignment error and access_denied |
| [Taylor SAML grant](05-taylor-saml-grant.png) | Successful launch after approval added |
| [Group removal](05-group-access-removed.png) | App-Demo-Users contains only Alex and Jamie |
| [SAML denial after removal](05-saml-access-removed.png) | New app launch blocked |
| [Taylor deactivated](05-taylor-deactivated.png) | Okta account status |
| [Mover before](05-mover-before.png) | Alex in Workforce-Employees and App-Demo-Users |
| [Mover after](05-mover-after.png) | Alex in Workforce-Contractors and App-Demo-Users |
| [Contractor rule selected](05-mover-contractor-rule.png) | System Log targets contractor session/enrollment rules |
| [SCIM created](06-scim-created.png) | Correct downstream user with active=True |
| [SCIM updated](06-scim-updated.png) | Title update while active |
| [SCIM deactivated](06-scim-deactivated.png) | Retained record with active=False |

OIDC success/token-exchange results are recorded in the results document; raw codes/tokens are intentionally not published. Missing evidence for a test is identified in that document, rather than inferred from these screenshots.
