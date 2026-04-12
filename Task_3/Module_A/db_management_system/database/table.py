from .bplustree import BPlusTree

class Table:
    def __init__(self, name, schema, order=8, search_key=None):
        self.name = name
        self.schema = schema
        self.order = order
        self.data = BPlusTree(order=order)
        self.search_key = search_key

        if self.search_key is None or self.search_key not in self.schema:
            raise ValueError("search_key must be a valid field in schema")

    def validate_record(self, record):
        """Validate that the given record matches the table schema."""
        if set(record.keys()) != set(self.schema.keys()):
            return False
        for field, field_type in self.schema.items():
            if not isinstance(record[field], field_type):
                return False
        return True

    def insert(self, record):
        if not self.validate_record(record):
            raise ValueError("Record does not match schema")
        key = record[self.search_key]
        success = self.data.insert(key, record)
        return success

    def get(self, record_id):
        """Retrieve a single record by its ID."""
        return self.data.search(record_id)

    def get_all(self):
        """
        Retrieve all records in sorted key order as (key, value) tuples.

        FIX (Assignment 3): Previously returned only values — that broke
        SnapshotManager which needs (key, value) pairs to rebuild the B+ Tree
        on rollback.  Now consistent with BPlusTree.get_all().

        If you only want the record dicts (no keys), call:
            [v for _, v in table.get_all()]
        """
        return self.data.get_all()   # returns list of (key, value) tuples

    def update(self, record_id, new_record):
        """Update a record identified by `record_id` with `new_record` data."""
        if not self.validate_record(new_record):
            raise ValueError("New record does not match schema")
        if new_record[self.search_key] != record_id:
            raise ValueError("Cannot change primary key value")
        return self.data.update(record_id, new_record)

    def delete(self, record_id):
        """Delete the record from the table by its `record_id`."""
        return self.data.delete(record_id)

    def range_query(self, start_value, end_value):
        """Perform a range query using the search key."""
        return [value for key, value in self.data.range_query(start_value, end_value)]
