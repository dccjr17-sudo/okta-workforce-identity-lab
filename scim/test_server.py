import json
import secrets
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from server import Store, handler, USER, MSG

class ProvisioningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='.')
        self.store = Store(self.temp.name + '/test.sqlite3')
        self.token = secrets.token_urlsafe(32)
        self.http = ThreadingHTTPServer(('127.0.0.1', 0), handler(self.store, self.token))
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join()
        self.store.db.close()
        self.temp.cleanup()

    def request(self, method, path, body=None, auth=True):
        headers = {'Content-Type': 'application/scim+json'}
        if auth:
            headers['Authorization'] = 'Bearer ' + self.token
        req = Request('http://127.0.0.1:' + str(self.http.server_port) + '/scim/v2/' + path, data=json.dumps(body).encode() if body is not None else None, headers=headers, method=method)
        try:
            response = urlopen(req)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def test_full_lifecycle_and_persistence(self):
        self.assertEqual(self.request('GET', 'Users', auth=False)[0], 401)
        self.assertEqual(self.request('GET', 'Users?filter=userName%20eq%20%22alex.employee%40example.com%22')[1]['totalResults'], 0)
        status, user = self.request('POST', 'Users', {'schemas': [USER], 'userName': 'alex.employee@example.com', 'name': {'givenName': 'Alex', 'familyName': 'Employee'}, 'active': True, 'password': 'discard-me'})
        self.assertEqual(status, 201)
        self.assertNotIn('password', user)
        uid = user['id']
        self.assertEqual(self.request('POST', 'Users', {'userName': 'ALEX.EMPLOYEE@example.com'})[0], 409)
        self.assertEqual(self.request('GET', 'Users?filter=userName%20eq%20%22ALEX.EMPLOYEE%40example.com%22')[1]['totalResults'], 1)
        user['title'] = 'Contractor Analyst'
        self.assertEqual(self.request('PUT', 'Users/' + uid, user)[1]['title'], 'Contractor Analyst')
        patch = {'schemas': [MSG + 'PatchOp'], 'Operations': [{'op': 'replace', 'value': {'active': False}}]}
        self.assertFalse(self.request('PATCH', 'Users/' + uid, patch)[1]['active'])
        reopened = Store(self.temp.name + '/test.sqlite3')
        self.assertFalse(reopened.users()[0]['active'])
        reopened.db.close()
        self.assertEqual(self.request('GET', 'Users?count=0')[1]['itemsPerPage'], 0)
        self.assertEqual(self.request('GET', 'Users?filter=unsupported')[0], 400)
        self.assertEqual(self.request('GET', 'Users/missing')[0], 404)
        self.assertEqual(self.request('DELETE', 'Users/' + uid)[0], 405)

    def test_lab_boundary_and_patch(self):
        self.assertEqual(self.request('POST', 'Users', {'userName': 'real@company.test'})[0], 400)
        _, user = self.request('POST', 'Users', {'userName': 'jamie.admin@example.com'})
        status, updated = self.request('PATCH', 'Users/' + user['id'], {'Operations': [{'op': 'replace', 'path': 'name.givenName', 'value': 'Jamie'}, {'op': 'replace', 'path': 'active', 'value': False}]})
        self.assertEqual(status, 200)
        self.assertEqual(updated['name']['givenName'], 'Jamie')
        self.assertFalse(updated['active'])
        self.assertTrue(self.request('GET', 'ServiceProviderConfig')[1]['patch']['supported'])

if __name__ == '__main__':
    unittest.main()
