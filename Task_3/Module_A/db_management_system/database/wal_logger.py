import json
import os
import threading
from datetime import datetime

WAL_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'wal.log')

class WALLogger:
    """
    Write-Ahead Log (WAL).
    Every BEGIN, INSERT, UPDATE, DELETE, COMMIT, ROLLBACK
    is appended to wal.log BEFORE the B+ Tree is touched.
    This guarantees durability and crash recovery.
    """
    _lock = threading.Lock()

    def __init__(self, path=WAL_PATH):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def _append(self, entry: dict):
        entry['timestamp'] = datetime.utcnow().isoformat()
        with self._lock:
            with open(self.path, 'a') as f:
                f.write(json.dumps(entry) + '\n')

    def log_begin(self, txn_id):
        self._append({'type': 'BEGIN', 'txn_id': txn_id})

    def log_operation(self, txn_id, table, op, key, before, after):
        """
        op: 'INSERT' | 'UPDATE' | 'DELETE'
        before: old record (None for INSERT)
        after:  new record (None for DELETE)
        """
        self._append({
            'type': op,
            'txn_id': txn_id,
            'table': table,
            'key': key,
            'before': before,
            'after': after
        })

    def log_commit(self, txn_id):
        self._append({'type': 'COMMIT', 'txn_id': txn_id})

    def log_rollback(self, txn_id):
        self._append({'type': 'ROLLBACK', 'txn_id': txn_id})

    def log_checkpoint(self):
        self._append({'type': 'CHECKPOINT'})

    def read_all(self):
        if not os.path.exists(self.path):
            return []
        with open(self.path, 'r') as f:
            return [json.loads(line) for line in f if line.strip()]

    def clear(self):
        """Truncate log after a clean checkpoint."""
        with self._lock:
            open(self.path, 'w').close()