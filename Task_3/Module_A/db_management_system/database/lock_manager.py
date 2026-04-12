import threading

class LockManager:
    """
    Table-level two-phase locking (2PL).
    Supports shared (read) and exclusive (write) locks.
    Growing phase: acquire locks. Shrinking phase: release at COMMIT/ROLLBACK.
    """

    def __init__(self):
        self._locks = {}       # table_name -> {'mode': 'S'/'X', 'owners': set()}
        self._meta_lock = threading.Lock()
        self._conditions = {}  # table_name -> threading.Condition

    def _get_condition(self, table):
        if table not in self._conditions:
            self._conditions[table] = threading.Condition(self._meta_lock)
        return self._conditions[table]

    def acquire_shared(self, txn_id, table, timeout=5.0):
        """
        Shared lock: multiple readers can hold it simultaneously.
        Blocked only if an exclusive lock is held by another transaction.
        """
        with self._meta_lock:
            cond = self._get_condition(table)
            deadline = threading.Event()

            def _try():
                lock = self._locks.get(table)
                if lock is None:
                    self._locks[table] = {'mode': 'S', 'owners': {txn_id}}
                    return True
                if lock['mode'] == 'S':
                    lock['owners'].add(txn_id)
                    return True
                if lock['mode'] == 'X' and txn_id in lock['owners']:
                    return True   # already holding exclusive → OK
                return False

            import time
            end = time.time() + timeout
            while not _try():
                remaining = end - time.time()
                if remaining <= 0:
                    raise TimeoutError(f"Txn {txn_id}: timeout acquiring S-lock on '{table}'")
                cond.wait(timeout=remaining)

    def acquire_exclusive(self, txn_id, table, timeout=5.0):
        """
        Exclusive lock: only one transaction may hold it, no readers allowed.
        """
        with self._meta_lock:
            cond = self._get_condition(table)

            def _try():
                lock = self._locks.get(table)
                if lock is None:
                    self._locks[table] = {'mode': 'X', 'owners': {txn_id}}
                    return True
                if lock['mode'] == 'X' and lock['owners'] == {txn_id}:
                    return True   # already holding it
                # Upgrade S→X if we're the only shared holder
                if lock['mode'] == 'S' and lock['owners'] == {txn_id}:
                    lock['mode'] = 'X'
                    return True
                return False

            import time
            end = time.time() + timeout
            while not _try():
                remaining = end - time.time()
                if remaining <= 0:
                    raise TimeoutError(f"Txn {txn_id}: timeout acquiring X-lock on '{table}'")
                cond.wait(timeout=remaining)

    def release_all(self, txn_id):
        """Release every lock held by this transaction. Call at COMMIT or ROLLBACK."""
        with self._meta_lock:
            to_remove = []
            for table, lock in self._locks.items():
                lock['owners'].discard(txn_id)
                if not lock['owners']:
                    to_remove.append(table)
            for table in to_remove:
                del self._locks[table]
                cond = self._conditions.get(table)
                if cond:
                    cond.notify_all()