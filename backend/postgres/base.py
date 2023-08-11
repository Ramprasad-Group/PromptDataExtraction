from sqlalchemy.orm import DeclarativeBase
from . import ops

class ORMBase(DeclarativeBase):
    """
    A custom base class for the ORM classes.
    Adds functionalities for insert, update, iteration etc.

    """

    def serialize(self):
        return ops.serialize(self)

    def get_one(self, session, criteria = {}) -> 'ORMBase':
        """ Get the first element from current table using a criteria ."""
        return ops.first_row(self, session, criteria)
    
    def get_n(self, session, n : int, criteria = {}) -> 'ORMBase':
        """ Get the first n rows of current table using a criteria ."""
        return ops.first_n_rows(self, session, criteria, n)

    def get_all(self, session, criteria = {}) -> list['ORMBase']:
        """ Get all the elements from current table using a criteria ."""
        return ops.all_rows(self, session, criteria)

    def iter(self, session, column : str, size=1000) -> 'ORMBase':
        """ 
        Iterate over all rows of current table. Optionally specify
        the batch size.
        
        """
        yield ops.iter_rows(self, session, column, size)

    def insert(self, session, *, test=False):
        """ Insert as a table row. """
        return ops.insert_row(self, session, test=test)

    def update(self, session, newObj, *, test=False):
        return ops.update_row(self, session, newObj, test=test)

    def upsert(self, session, which: dict, payload, name : str, *,
               update=False, test=False) -> 'ORMBase':
        """
        Update the database by inserting or updating a record.
        Args:
            which dict:     The criteria to check if the record already exists.
            payload:        The object to insert to the table.
            name str:       Name or ID of the object, for logging purposes.
            update bool:    Whether to update the record if already exists.
        """
        return ops.upsert_row(self, session, which, payload,
                             do_update=update, test=test)
