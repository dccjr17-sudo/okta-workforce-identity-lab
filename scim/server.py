"""Small, authenticated SCIM user-provisioning lab. Not a production SCIM server."""
import copy
import hmac
import json
import os
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

USER = 'urn:ietf:params:scim:schemas:core:2.0:User'
MSG = 'urn:ietf:params:scim:api:messages:2.0:'

class Store:
    def __init__(self, path):
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute('CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT UNIQUE, body TEXT)')
        self.db.commit()

    def users(self):
        with self.lock:
            return [json.loads(row[0]) for row in self.db.execute('SELECT body FROM users ORDER BY rowid')]

    def save(self, body, uid=None):
        body = copy.deepcopy(body)
        body.pop('password', None)
        username = body.get('userName')
        if not isinstance(username, str) or not username.endswith('@example.com'):
            raise ValueError('Lab users must have an @example.com userName')
        if not isinstance(body.get('active', True), bool):
            raise ValueError('active must be a boolean')
        with self.lock:
            prior = next((u for u in self.users() if u['id'] == uid), None)
            body['id'] = uid or str(uuid.uuid4())
            body['schemas'] = body.get('schemas', [USER])
            body.setdefault('active', True)
            now = datetime.now(timezone.utc).isoformat()
            body['meta'] = {'resourceType': 'User', 'created': prior['meta']['created'] if prior else now, 'lastModified': now}
            self.db.execute('INSERT INTO users VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET username=excluded.username, body=excluded.body', (body['id'], username.casefold(), json.dumps(body)))
            self.db.commit()
        return body

def handler(store, token):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Do not log credentials, bodies, IP addresses, or query strings.

        def reply(self, status, body):
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/scim+json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            print(json.dumps({'method': self.command, 'resource': urlsplit(self.path).path, 'status': status}), flush=True)

        def error(self, status, detail, kind=None):
            result = {'schemas': [MSG + 'Error'], 'status': str(status), 'detail': detail}
            if kind:
                result['scimType'] = kind
            self.reply(status, result)

        def run_request(self):
            if not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + token):
                return self.error(401, 'Bearer authentication required')
            parsed = urlsplit(self.path)
            path = parsed.path.rstrip('/')
            if self.command == 'GET' and path == '/scim/v2/ServiceProviderConfig':
                return self.reply(200, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig'], 'patch': {'supported': True}, 'bulk': {'supported': False, 'maxOperations': 0, 'maxPayloadSize': 0}, 'filter': {'supported': True, 'maxResults': 200}, 'changePassword': {'supported': False}, 'sort': {'supported': False}, 'etag': {'supported': False}, 'authenticationSchemes': [{'type': 'oauthbearertoken', 'name': 'Bearer token', 'description': 'Lab bearer authentication', 'primary': True}]})
            if path == '/scim/v2/Groups' and self.command == 'GET':
                return self.reply(200, {'schemas': [MSG + 'ListResponse'], 'totalResults': 0, 'startIndex': 1, 'itemsPerPage': 0, 'Resources': []})
            if path != '/scim/v2/Users' and not path.startswith('/scim/v2/Users/'):
                return self.error(404, 'Resource not found')
            uid = path.split('/')[-1] if path != '/scim/v2/Users' else None
            current = next((u for u in store.users() if u['id'] == uid), None)
            if uid and current is None:
                return self.error(404, 'User not found')
            if self.command == 'GET':
                if uid:
                    return self.reply(200, current)
                query = parse_qs(parsed.query)
                users = store.users()
                if 'filter' in query:
                    match = re.fullmatch(r'userName\s+eq\s+"([^"]+)"', query['filter'][0], re.I)
                    if not match:
                        return self.error(400, 'Only userName eq filtering is supported', 'invalidFilter')
                    users = [u for u in users if u['userName'].casefold() == match[1].casefold()]
                start = max(1, int(query.get('startIndex', ['1'])[0]))
                count = max(0, min(200, int(query.get('count', ['100'])[0])))
                page = users[start-1:start-1+count]
                return self.reply(200, {'schemas': [MSG + 'ListResponse'], 'totalResults': len(users), 'startIndex': start, 'itemsPerPage': len(page), 'Resources': page})
            if self.command not in ('POST', 'PUT', 'PATCH'):
                return self.error(405, 'Operation not supported')
            length = int(self.headers.get('Content-Length', '0'))
            if length < 1 or length > 65536:
                return self.error(413, 'Request body must be between 1 and 65536 bytes')
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError('JSON object required')
            if self.command == 'POST' and not uid:
                return self.reply(201, store.save(body))
            if self.command == 'PUT' and uid:
                return self.reply(200, store.save(body, uid))
            if self.command == 'PATCH' and uid:
                changed = copy.deepcopy(current)
                for operation in body.get('Operations', []):
                    if operation.get('op', '').lower() not in ('add', 'replace'):
                        raise ValueError('Only add/replace PATCH supported')
                    target = operation.get('path')
                    value = operation.get('value')
                    if target is None and isinstance(value, dict):
                        changed.update(value)
                    elif target in ('active', 'userName', 'displayName', 'name', 'emails', 'title', 'userType', 'locale', 'externalId'):
                        changed[target] = value
                    elif target in ('name.givenName', 'name.familyName'):
                        changed.setdefault('name', {})[target.split('.')[1]] = value
                    else:
                        raise ValueError('Unsupported PATCH path')
                return self.reply(200, store.save(changed, uid))
            return self.error(405, 'Operation not supported')

        def dispatch(self):
            try:
                self.run_request()
            except sqlite3.IntegrityError:
                self.error(409, 'userName already exists', 'uniqueness')
            except (ValueError, KeyError, TypeError):
                self.error(400, 'Invalid request or unsupported lab operation', 'invalidValue')
            except Exception:
                self.error(500, 'Internal server error')

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = dispatch
    return Handler

if __name__ == '__main__':
    token = os.environ.get('SCIM_TOKEN', '')
    if len(token) < 32:
        raise SystemExit('Set SCIM_TOKEN to a random value of at least 32 characters. Never commit it.')
    store = Store(os.environ.get('SCIM_DB', 'lab-users.sqlite3'))
    server = ThreadingHTTPServer(('127.0.0.1', int(os.environ.get('SCIM_PORT', '8080'))), handler(store, token))
    print('SCIM lab listening on loopback port 8080; use /scim/v2 as the base path.', flush=True)
    server.serve_forever()
