# SCIM user-provisioning test server

Python 3 standard library only. Persistent SQLite storage. Bearer authentication. Only fictional usernames ending in `@example.com` are accepted. This intentionally limited server supports Okta user provisioning, not full SCIM compliance.

## Supported operations

- GET /scim/v2/Users with userName eq filters and pagination
- POST /scim/v2/Users with case-insensitive duplicate detection
- GET and PUT /scim/v2/Users/{id}
- PATCH add/replace for supported profile fields and active=false
- ServiceProviderConfig; empty Groups discovery

Passwords are discarded; request logging excludes bodies and authorization headers. Group push, imports of groups, DELETE, bulk, arbitrary filtering/PATCH paths, and complete schema discovery are unsupported. Do not enable password sync.

## Local setup (PowerShell)

From the repository root, create a local runtime directory and a random token:

```powershell
New-Item -ItemType Directory -Force .runtime | Out-Null
$tokenBytes = New-Object byte[] 32
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
try { $rng.GetBytes($tokenBytes) } finally { $rng.Dispose() }
$env:SCIM_TOKEN = [Convert]::ToBase64String($tokenBytes)
Set-Content .runtime/token.txt $env:SCIM_TOKEN -NoNewline
$env:SCIM_DB = '.runtime/lab-users.sqlite3'
python -u scim/server.py
```

The token/database are ignored by Git. Treat them as private local data. The server binds to 127.0.0.1:8080 only. Stop with Ctrl+C.

In another window at the repository root, an official Cloudflare cloudflared installation can create a temporary test endpoint:

```powershell
cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8080 --protocol http2
```

Use the generated HTTPS address plus /scim/v2 in Okta. Paste only your lab token into OAuth Bearer Token. A restart changes the quick-tunnel address. Stop the tunnel after testing.

## Tests

```powershell
Set-Location scim
python -m unittest -v test_server.py
```

Tests start an ephemeral localhost server and use temporary databases/random credentials. They validate the meaningful HTTP lifecycle rather than changing real Okta data.

## Receiving-account inspection

In a third window at the repository root:

```powershell
$labHeaders = @{ Authorization = 'Bearer ' + (Get-Content .runtime/token.txt -Raw) }
$labUsers = Invoke-RestMethod 'http://127.0.0.1:8080/scim/v2/Users' -Headers $labHeaders
$labUsers.Resources | Select-Object userName,active,title
```

## Okta lab procedure

Configure SCIM 2.0 Test App (OAuth Bearer Token), label Lab-SCIM-Demo, hidden dashboard icon, no SAML login setup. Enable API integration, test credentials, then enable Create Users, Update User Attributes, and Deactivate Users. Assign a dedicated App-SCIM-Users group. Add the fictional Alex user, change a mapped title, then remove the group membership. Verify downstream active true, title update, and active false respectively. Retain Alex's separate SAML/OIDC approval.
