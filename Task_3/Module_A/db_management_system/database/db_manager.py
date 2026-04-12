from .table import Table
from .transaction_manager import TransactionManager
class DatabaseManager:
    """
    Manages multiple databases, each containing multiple tables.
    Structure:
        { db_name: { table_name: Table instance } }
    """

    def __init__(self):
        self.databases = {}

    #  DATABASE LEVEL 

    def create_database(self, db_name):
        """
        Create a new database with the given name.
        """
        if not db_name:
            raise ValueError("Database name cannot be empty")

        if db_name in self.databases:
            return False

        self.databases[db_name] = {}
        return True

    def delete_database(self, db_name):
        """
        Delete an existing database and all its tables.
        """
        if db_name in self.databases:
            del self.databases[db_name]
            return True
        return False

    def list_databases(self):
        """
        Return a list of all database names.
        """
        return list(self.databases.keys())

    #  TABLE LEVEL 

    def create_table(self, db_name, table_name, schema, order=8, search_key=None):
        """
        Create a new table inside a database.
        """
        if db_name not in self.databases:
            self.create_database(db_name)

        if not table_name:
            raise ValueError("Table name cannot be empty")

        if table_name in self.databases[db_name]:
            return False

        if search_key is None or search_key not in schema:
            raise ValueError("search_key must be provided and exist in schema")

        self.databases[db_name][table_name] = Table(
            table_name, schema, order, search_key
        )
        return True

    def delete_table(self, db_name, table_name):
        """
        Delete a table from the database.
        """
        if db_name in self.databases and table_name in self.databases[db_name]:
            del self.databases[db_name][table_name]
            return True
        return False

    def list_tables(self, db_name):
        """
        List all tables in a database.
        Returns (list, success_flag)
        """
        if db_name in self.databases:
            return list(self.databases[db_name].keys()), True
        return [], False

    def get_table(self, db_name, table_name):
        """
        Retrieve a Table instance.
        Returns (table, success_flag)
        """
        if db_name in self.databases and table_name in self.databases[db_name]:
            return self.databases[db_name][table_name], True
        return None, False

    #  DEBUG / DISPLAY 

    def __repr__(self):
        dbs = ", ".join(self.databases.keys()) or "none"
        return f"DatabaseManager(databases=[{dbs}])"
    
    def get_transaction_manager(self, db_name):
        """Return a TransactionManager bound to the tables of the given database."""
        if db_name not in self.databases:
            raise KeyError(f"Database '{db_name}' not found.")
        tables = self.databases[db_name]  # dict of {table_name: Table object}
        return TransactionManager(tables)