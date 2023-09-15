""" Add a checkpoint of row ID to keep track of the processed
    database tables.
"""

import pylogg
from backend import postgres, sett
from backend.postgres.orm import TableCursor

log = pylogg.New('ckpt')


def add_new(db, name : str, table : str, row : int,
                   comment : str = None) -> bool:
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
             f"Comment: {comment}")

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
            if sett.Run.debugCount > 0:
                raise ValueError("Row ID older than checkpoint.")
            return False
    
    cursor.insert(db)
    db.commit()
    t2.done("New checkpoint added.")
    return True


def get_last(db, name : str, table : str, comment : str = None) -> int:
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
                     comment : str = None) -> list[TableCursor]:
    """ Get the list of all previous checkpoints.

        db:         PostGres scoped session object.
        name:       Name of the process for which this checkpoint is for.
        table:      Name of the table to keep track of.
        comment:    Additional information, filtering string (optional).
    """
    criteria = {'name': name, 'table': table}
    if comment:
        criteria['comment'] = comment
    return TableCursor().get_all(db, criteria)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('name', help="Process name")
    parser.add_argument('table', help="Table name")
    parser.add_argument('-r', '--row', type=int, default=0,
                        help="Max row processed")
    parser.add_argument('-c', '--comment', default=None, help="Comment string")
    parser.add_argument('-l', '--list', default=False, help="List all",
                        action='store_true')
    parser.add_argument('-g', '--get', default=False, help="Get last max row",
                        action='store_true')
    args = parser.parse_args()

    sett.load_settings()
    postgres.load_settings()
    pylogg.setLevel(sett.Run.logLevel)
    db = postgres.connect()

    if args.list:
        history = list_all(db, args.name, args.table, args.comment)
        for item in history:
            print(f"\nName: {item.name}, Table: {item.table}, Row: {item.row}")
            if item.comment:
                print(f"Comment: {item.comment}")
            print("-"*50)
        if not history:
            print("No history found.")

    if args.get:
        last = get_last(db, args.name, args.table, args.comment)
        print(f"\nTable: {args.table}, Last ID: {last}, Comment: {args.comment}")

    if not args.list and not args.get:
        add_new(db, args.name, args.table, args.row, args.comment)

    pylogg.close()
