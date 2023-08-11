import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase

import pylogg
log = pylogg.New('db')


class Operation:
    """
    Perform operation on a ORM class that is not a child
    of ORMBase.
    Adds functionalities for insert, update, iteration etc.
    
    """

    def __init__(self, table : DeclarativeBase):
        if not hasattr(table, "__tablename__"):
            raise ValueError("table must be a child of DeclarativeBase")
        self.table : DeclarativeBase = table

    def get_one(self, session, criteria = {}) -> DeclarativeBase:
        """ Get the first row using a criteria ."""
        return first_row(self.table, session, criteria)

    def get_n(self, session, n : int, criteria = {}) -> DeclarativeBase:
        """ Get the first n rows using a criteria ."""
        return first_n_rows(self.table, session, criteria, n)

    def get_all(self, session, criteria = {}) -> list[DeclarativeBase]:
        """ Get all the elements from current table using a criteria ."""
        return all_rows(self.table, session, criteria)

    def iter(self, session, column : str, size=1000) -> DeclarativeBase:
        """
        Iterate over all rows of the table based on a column.
        Optionally specify the batch size.
        """
        yield iter_rows(self.table, session, column, size)

    def insert(self, session, *, test=False):
        """ Insert the current table data. """
        return insert_row(self.table, session, test=test)

    def update(self, session, newObj, *, test=False):
        return update_row(self.table, session, newObj, test=test)

    def upsert(self, session, which: dict, payload, name : str, *,
               update=False, test=False) -> DeclarativeBase:
        """
        Update the database by inserting or updating a record.
        Args:
            which dict:     The criteria to check if the record already exists.
            payload:        The object to insert to the table.
            name str:       Name or ID of the object, for logging purposes.
            update bool:    Whether to update the record if already exists.
        """

        return upsert_row(self.table, session, which, payload,
                          name, do_update=update, test=test)


def serialize(tbl):
    """ Serialize a table class data. """
    res = {}
    for attr in vars(tbl.__class__):
        if attr.startswith("_"):
            continue
        val = tbl.__getattribute__(attr)
        res[attr] = val
    return res


def first_row(tbl, sess, criteria):
    """ Get the first element from a table using a criteria ."""
    return sess.query(tbl.__class__).filter_by(**criteria).first()


def all_rows(tbl, sess, criteria):
    """ Get all rows from a table using a criteria ."""
    return sess.query(tbl.__class__).filter_by(**criteria).all()


def first_n_rows(tbl, sess, criteria, n : int):
    """ Get all rows from a table using a criteria ."""
    return sess.query(tbl.__class__).filter_by(**criteria).limit(n).all()


def insert_row(tbl, sess, *, test=False):
    """ Insert the current table data. """
    payload = serialize(tbl)
    try:
        sess.execute(sa.insert(tbl.__class__), payload)
    except Exception as err:
        log.error("Insert ({}) - {}", tbl.__tablename__, err)
    if test:
        sess.rollback()
        log.trace("Insert ({}) - rollback", tbl.__tablename__)
    else:
        sess.commit()
        log.trace("Insert ({})", tbl.__tablename__)


def update_row(tbl, sess, newObj, *, test=False):
    """ Update the selected row with new table object. """
    values = serialize(newObj)
    try:
        sql = sa.update(tbl.__class__).where(tbl.id == newObj.id).values(**values)
        sess.execute(sql)
    except Exception as err:
        log.error("Update ({}) - {}", tbl.__tablename__, err)
    if test:
        sess.rollback()
        log.trace("Update ({}) - rollback", tbl.__tablename__)
    else:
        sess.commit()
        log.trace("Update ({})", tbl.__tablename__)


def upsert_row(tbl, sess, which: dict, payload, name : str, *,
            do_update=False, test=False) -> DeclarativeBase:
    """
    Update the database by inserting or updating a record.
    Args:
        which dict:     The criteria to check if the record already exists.
        payload:        The object to insert to the table.
        name str:       Name or ID of the object, for logging purposes.
        update bool:    Whether to update the record if already exists.
    """

    # select existing record by "which" criteria
    x = first_row(tbl, sess, which)

    # set the foreign keys
    payload.__dict__.update(which)

    if x is None:
        sa.insert(tbl, sess, test=test)
    else:
        if do_update:
            sa.update(tbl, sess, payload, test=test)
        else:
            log.trace(f"{tbl.__tablename__} ok: {name}")

    return first_row(tbl, sess, which)


def _column_windows(session, column, size):
    q = session.query(column, sa.func.row_number().over(
                    order_by=column).label('rownum')).from_self(column)
    if size > 1:
        q = q.filter(sa.text("rownum %% %d=1" % size))

    intervals = [id for id, in q]
    while intervals:
        start = intervals.pop(0)
        if intervals:
            yield sa.and_(column >= start, column < intervals[0])
        else:
            yield column >= start


def iter_rows(tbl, sess, column : str, size=1000) -> DeclarativeBase:
    """"Break a Query into windows of size on a given column."""
    column = getattr(tbl.__class__, column)
    for wc in _column_windows(sess, column, size):
        for row in sess.query(
                tbl.__class__).filter(wc).order_by(column):
            yield row

