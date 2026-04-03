import sys


class BruteForceDB:
    """
    Naive list-based database.
    All operations are O(n), used as a baseline for comparison
    with B+ Tree implementation.
    """

    def __init__(self):
        self.data = []  # list of (key, value) tuples

    # INSERT 
    def insert(self, key, value=None):
        """
        Insert key-value pair.
        If key already exists, update its value (to match B+ Tree behavior).
        """
        for i, (k, _) in enumerate(self.data):
            if k == key:
                self.data[i] = (key, value)
                return False  # updated
        self.data.append((key, value))
        return True  # inserted

    #  SEARCH 
    def search(self, key):
        """
        Linear search for key.
        Returns value if found, else None.
        """
        for k, v in self.data:
            if k == key:
                return v
        return None

    #  DELETE 
    def delete(self, key):
        """
        Delete key from database.
        Returns True if deleted, False if not found.
        """
        for i, (k, _) in enumerate(self.data):
            if k == key:
                del self.data[i]
                return True
        return False

    #  RANGE QUERY 
    def range_query(self, start, end):
        """
        Return all (key, value) pairs such that:
        start <= key <= end

        Output is sorted to match B+ Tree behavior.
        """
        if start > end:
            return []

        result = [(k, v) for k, v in self.data if start <= k <= end]
        return sorted(result, key=lambda x: x[0])

    #  UPDATE 
    def update(self, key, new_value):
        """
        Update value for an existing key.
        Returns True if updated, False if key not found.
        """
        for i, (k, _) in enumerate(self.data):
            if k == key:
                self.data[i] = (key, new_value)
                return True
        return False

    #  GET ALL 
    def get_all(self):
        """
        Return all key-value pairs in sorted order
        (to match B+ Tree behavior).
        """
        return sorted(self.data, key=lambda x: x[0])

    #  UTILITIES 
    def size(self):
        """Return number of records."""
        return len(self.data)

    def memory_usage(self):
        """
        Approximate memory usage (including stored elements).
        """
        total = sys.getsizeof(self.data)
        for item in self.data:
            total += sys.getsizeof(item)
            total += sys.getsizeof(item[0])
            total += sys.getsizeof(item[1])
        return total