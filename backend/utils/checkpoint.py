""" Add a checkpoint of row ID to keep track of the processed
    database tables.
"""

import pylogg
from backend import sett
from backend.postgres.orm import TableCursor

log = pylogg.New('ckpt')


def add_new(db, name : str, table : str, row : int,
                   comment : dict = {}) -> bool:
    """ Add a new checkpoint by inserting and committing
        a new row id to the table_cursor.
        
        db:         PostGres scoped session object.
        name:       Name of the process for which this checkpoint is for.
        table:      Name of the table to keep track of.
        row:        Max row ID that has been proccessed. Must be greater
                    than the currently stored checkpoints.
        comment:    Additional information, filtering string (optional).

        Returns True if successful.
    """
    t2 = log.info(f"New Checkpoint. Name: {name}, Table: {table}, Row: {row} "
             f"Comments: {comment}")

    cursor = TableCursor()
    cursor.name = name
    cursor.table = table 
    cursor.row = row
    cursor.comment = comment

    # Make sure the row id is newer.
    current_cursors = list_all(db, name, table, comment)
    for c in current_cursors:
        if row < c.row:
            log.error("Current Row ID is older than previous checkpoint.")
            log.error("Row ID: {}, previous checkpoint: {}.{} for process {}",
                      row, c.table, c.row, name)
            return False
    
    cursor.insert(db)
    db.commit()
    t2.done("New checkpoint added.")
    return True


def get_last(db, name : str, table : str, comment : dict = {}) -> int:
    """ Return the last stored max row id for the specified table.
        Returns 0 if no checkpoint is found.

        db:         PostGres scoped session object.
        name:       Name of the process for which this checkpoint is for.
        table:      Name of the table to keep track of.
        comment:    Additional information, filtering string (optional).
    """
    current_cursors = list_all(db, name, table, comment)
    last = 0
    for c in current_cursors:
        if c.row > last:
            last = c.row
    return last


def list_all(db, name : str, table : str,
                     comment : dict = {}) -> list[TableCursor]:
    """ Get the list of all previous checkpoints.

        db:         PostGres scoped session object.
        name:       Name of the process for which this checkpoint is for.
        table:      Name of the table to keep track of.
        comment:    Additional information, filtering string (optional).
    """
    criteria = {'name': name, 'table': table}
    return TableCursor().get_all(db, criteria)
