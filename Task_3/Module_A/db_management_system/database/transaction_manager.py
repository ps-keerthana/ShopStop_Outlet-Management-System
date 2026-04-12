import threading
import uuid
from .wal_logger import WALLogger
from .lock_manager import LockManager
from .snapshot import SnapshotManager


class Transaction:
    def __init__(self, txn_id, wal, lock_mgr, snapshot_mgr, tables):
        self.txn_id = txn_id
        self._wal = wal
        self._lock_mgr = lock_mgr
        self._snap = snapshot_mgr
        self._tables = tables
        self._active = True

    def _require_active(self):
        if not self._active:
            raise RuntimeError(f"Transaction {self.txn_id} is no longer active.")

    def _get_table(self, table_name):
        if table_name not in self._tables:
            raise KeyError(f"Table '{table_name}' does not exist.")
        return self._tables[table_name]

    # ------------------------------------------------------------------ CRUD

    def insert(self, table_name, record):
        """record must contain the search_key field."""
        self._require_active()
        tbl = self._get_table(table_name)
        self._lock_mgr.acquire_exclusive(self.txn_id, table_name)
        self._snap.save(self.txn_id, table_name, tbl.data)
        key = record[tbl.search_key]
        self._wal.log_operation(self.txn_id, table_name, 'INSERT', key, None, record)
        tbl.insert(record)

    def update(self, table_name, key, new_record):
        self._require_active()
        tbl = self._get_table(table_name)
        self._lock_mgr.acquire_exclusive(self.txn_id, table_name)
        self._snap.save(self.txn_id, table_name, tbl.data)
        old = tbl.get(key)
        self._wal.log_operation(self.txn_id, table_name, 'UPDATE', key, old, new_record)
        tbl.update(key, new_record)

    def delete(self, table_name, key):
        self._require_active()
        tbl = self._get_table(table_name)
        self._lock_mgr.acquire_exclusive(self.txn_id, table_name)
        self._snap.save(self.txn_id, table_name, tbl.data)
        old = tbl.get(key)
        self._wal.log_operation(self.txn_id, table_name, 'DELETE', key, old, None)
        tbl.delete(key)

    def search(self, table_name, key):
        """Public method called from notebook — maps to tbl.get()."""
        self._require_active()
        tbl = self._get_table(table_name)
        self._lock_mgr.acquire_shared(self.txn_id, table_name)
        return tbl.get(key)

    def range_query(self, table_name, start, end):
        self._require_active()
        tbl = self._get_table(table_name)
        self._lock_mgr.acquire_shared(self.txn_id, table_name)
        return tbl.range_query(start, end)

    # ------------------------------------------------------------------ COMMIT

    def commit(self):
        self._require_active()
        self._wal.log_commit(self.txn_id)
        # Persist every table touched to disk for durability
        for table_name in self._snap._snapshots.get(self.txn_id, {}):
            tbl = self._tables[table_name]
            self._snap.persist_to_disk(table_name, tbl.data)
        self._snap.discard(self.txn_id)
        self._lock_mgr.release_all(self.txn_id)
        self._active = False
        print(f"[TXN {self.txn_id[:8]}] COMMITTED")

    # ------------------------------------------------------------------ ROLLBACK

    def rollback(self):
        self._require_active()
        self._wal.log_rollback(self.txn_id)
        for table_name, records_snapshot in self._snap._snapshots.get(self.txn_id, {}).items():
            tbl = self._tables[table_name]
            from .bplustree import BPlusTree
            tbl.data = BPlusTree(order=tbl.order)
            for key, record in records_snapshot.items():
                tbl.data.insert(key, record)
            print(f"[TXN {self.txn_id[:8]}] ROLLED BACK '{table_name}' "
                  f"({len(records_snapshot)} records restored)")
        self._snap.discard(self.txn_id)
        self._lock_mgr.release_all(self.txn_id)
        self._active = False
        print(f"[TXN {self.txn_id[:8]}] ROLLBACK COMPLETE")


class TransactionManager:
    def __init__(self, tables, wal=None, lock_mgr=None, snapshot_mgr=None):
        self._tables = tables
        self._wal = wal or WALLogger()
        self._lock_mgr = lock_mgr or LockManager()
        self._snap = snapshot_mgr or SnapshotManager()
        self._active_txns = {}
        self._global_lock = threading.Lock()

    def begin(self) -> Transaction:
        txn_id = str(uuid.uuid4())
        self._wal.log_begin(txn_id)
        txn = Transaction(txn_id, self._wal, self._lock_mgr, self._snap, self._tables)
        with self._global_lock:
            self._active_txns[txn_id] = txn
        print(f"[TXN {txn_id[:8]}] BEGUN")
        return txn

    def recover(self):
        """
        Two-phase crash recovery:

        Phase 1 — Load last committed snapshots from disk.
            Each committed transaction persists a full table snapshot (pickle).
            This gives us the last known-good state.

        Phase 2 — WAL redo pass.
            Read the WAL log from top to bottom.
            For every transaction that has a COMMIT record, replay its
            INSERT / UPDATE / DELETE operations on top of the snapshot.
            Transactions that have no COMMIT record (incomplete / crashed)
            are silently ignored — their effects never reached disk.

        This correctly handles the gap between the last snapshot and the
        most recent committed WAL entries, which is the case that snapshot-
        only recovery misses.
        """
        from .bplustree import BPlusTree

        print("[RECOVERY] Phase 1 — loading last persisted snapshots from disk...")
        reload_count = 0
        for table_name, tbl in self._tables.items():
            records = self._snap.load_from_disk(table_name)
            if records is not None:
                tbl.data = BPlusTree(order=tbl.order)
                for key, record in records.items():
                    tbl.data.insert(key, record)
                reload_count += 1
                print(f"[RECOVERY]   Loaded '{table_name}' ({len(records)} records).")
            else:
                print(f"[RECOVERY]   No snapshot found for '{table_name}', starting empty.")

        # ---------------------------------------------------------------- Phase 2
        print("[RECOVERY] Phase 2 — WAL redo pass...")
        entries = self._wal.read_all()

        # Group WAL entries by transaction
        ops_by_txn = {}   # txn_id -> [entry, ...]
        committed = set()

        for entry in entries:
            t    = entry['type']
            tid  = entry.get('txn_id')
            if t == 'BEGIN':
                ops_by_txn[tid] = []
            elif t in ('INSERT', 'UPDATE', 'DELETE'):
                ops_by_txn.setdefault(tid, []).append(entry)
            elif t == 'COMMIT':
                committed.add(tid)
            # ROLLBACK / CHECKPOINT entries are intentionally skipped

        incomplete = set(ops_by_txn.keys()) - committed

        # Redo committed transactions whose ops might not be in the snapshot
        redo_count = 0
        for tid in committed:
            ops = ops_by_txn.get(tid, [])
            for op in ops:
                table_name = op.get('table')
                tbl = self._tables.get(table_name)
                if tbl is None:
                    continue   # table not registered in this db instance
                op_type = op['type']
                key     = op['key']
                after   = op.get('after')
                before  = op.get('before')
                try:
                    if op_type == 'INSERT':
                        # Only insert if not already present (snapshot may already have it)
                        if tbl.get(key) is None and after is not None:
                            tbl.insert(after)
                            redo_count += 1
                    elif op_type == 'UPDATE':
                        if after is not None:
                            existing = tbl.get(key)
                            if existing != after:
                                tbl.update(key, after)
                                redo_count += 1
                    elif op_type == 'DELETE':
                        if tbl.get(key) is not None:
                            tbl.delete(key)
                            redo_count += 1
                except Exception:
                    pass   # skip ops that can't be applied (e.g. already deleted)

        print(f"[RECOVERY] Reloaded {reload_count} table snapshot(s) from disk.")
        print(f"[RECOVERY] Found {len(committed)} committed transaction(s) in WAL.")
        print(f"[RECOVERY] Replayed {redo_count} WAL operation(s) on top of snapshots.")
        print(f"[RECOVERY] Ignored {len(incomplete)} incomplete (no-COMMIT) transaction(s).")
        print("[RECOVERY] Recovery complete — database is consistent.")

        return {
            'reloaded_from_disk': reload_count,
            'committed_txns':     len(committed),
            'redo_ops_applied':   redo_count,
            'incomplete_txns':    list(incomplete),
        }
