import os
import json
import pickle
import threading

SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'snapshots')

class SnapshotManager:
    """
    Saves pre-transaction snapshots by extracting all records from the
    B+ Tree into a plain dict, avoiding deepcopy recursion on large trees.
    Restores by clearing the table and re-inserting from the saved records.
    """

    def __init__(self):
        self._snapshots = {}   # txn_id -> {table_name: {key: record}}
        self._lock = threading.Lock()
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)

    def _extract_records(self, data_obj):
        """
        Extract all records from tbl.data into a plain dict.
        tbl.data is the BPlusTree instance — we use get_all() to read
        every record out as a flat list of (key, value) pairs.
        """
        records = {}
        try:
            # get_all() returns list of (key, value) tuples
            all_records = data_obj.get_all()
            for key, value in all_records:
                records[key] = value
        except Exception:
            pass
        return records

    def save(self, txn_id, table_name, data_obj):
        """Save a snapshot of all current records before transaction touches them."""
        with self._lock:
            if txn_id not in self._snapshots:
                self._snapshots[txn_id] = {}
            if table_name not in self._snapshots[txn_id]:
                # Extract records into a plain dict — no deepcopy of the tree
                self._snapshots[txn_id][table_name] = self._extract_records(data_obj)

    def restore(self, txn_id, table_name):
        """Return saved records dict for this table, or None."""
        with self._lock:
            return self._snapshots.get(txn_id, {}).get(table_name)

    def discard(self, txn_id):
        """Drop snapshots after commit or rollback."""
        with self._lock:
            self._snapshots.pop(txn_id, None)

    def persist_to_disk(self, table_name, data_obj):
        """Persist committed state to disk as a plain dict."""
        path = os.path.join(SNAPSHOT_DIR, f'{table_name}.pkl')
        records = self._extract_records(data_obj)
        with open(path, 'wb') as f:
            pickle.dump(records, f)

    def load_from_disk(self, table_name):
        """Load persisted records dict from disk."""
        path = os.path.join(SNAPSHOT_DIR, f'{table_name}.pkl')
        if not os.path.exists(path):
            return None
        with open(path, 'rb') as f:
            return pickle.load(f)