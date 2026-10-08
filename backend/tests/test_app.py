import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app

class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / 'test.sqlite3')
        self.app = create_app(self.path)
        self.client = self.app.test_client()
    def tearDown(self):
        self.temp.cleanup()
    def add(self, name='Ana'):
        return self.client.post('/api/tickets', json={'name': name})
    def test_full_lifecycle_and_persistence(self):
        self.assertEqual(self.add().json['id'], 1)
        self.assertEqual(self.add('Luis').json['id'], 2)
        self.assertEqual(self.client.post('/api/desks/1/call').json['ticket_id'], 1)
        self.assertEqual(self.client.post('/api/desks/1/call').status_code, 409)
        self.assertEqual(self.client.post('/api/desks/1/complete', json={'ticket_id': 2}).status_code, 409)
        self.assertEqual(self.client.post('/api/desks/1/complete', json={'ticket_id': 1}).status_code, 200)
        self.assertEqual(self.client.post('/api/desks/1/call').json['ticket_id'], 2)
        state = create_app(self.path).test_client().get('/api/state').json
        self.assertEqual(state['completed'], 1)
        self.assertEqual(state['desks'][0]['ticket']['id'], 2)
        self.assertEqual(len(state['desks']), 4)
        self.assertEqual(self.add().json['id'], 3)
    def test_invalid_requests(self):
        for name in ['', '   ', 'x' * 81, 123]:
            self.assertEqual(self.client.post('/api/tickets', json={'name': name}).status_code, 400)
        self.assertEqual(self.client.post('/api/tickets', json=[]).status_code, 400)
        self.assertEqual(self.client.post('/api/desks/5/call').status_code, 404)
        self.assertEqual(self.client.post('/api/desks/1/call').status_code, 409)
        self.assertEqual(self.client.get('/api/missing').status_code, 404)
    def test_concurrent_calls_never_duplicate(self):
        for i in range(8): self.add(str(i))
        def call(desk):
            with self.app.test_client() as client:
                response = client.post(f'/api/desks/{desk}/call')
                return response.status_code, response.json.get('ticket_id')
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(call, [1, 2, 3, 4]))
        self.assertTrue(all(code == 200 for code, _ in results))
        self.assertEqual({ticket for _, ticket in results}, {1, 2, 3, 4})
        state = self.client.get('/api/state').json
        self.assertEqual([t['id'] for t in state['waiting']], [5, 6, 7, 8])

if __name__ == '__main__':
    unittest.main()
