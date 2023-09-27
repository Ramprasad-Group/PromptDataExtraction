import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase

import pylogg
log = pylogg.New('postgres')


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

    def exists(self, session, criteria = {}, **kwargs) -> DeclarativeBase:
        """ Get the ID of the first element from current table using
            a criteria. Returns None if not found. """
        kwargs.update(dict(criteria))
        return get_id(self, session, kwargs)

    def get_one(self, session, criteria = {}) -> DeclarativeBase:
        """ Get the first row using a criteria ."""
        return first_row(self.table, session, criteria)

    def get_n(self, session, n : int, criteria = {}) -> DeclarativeBase:
        """ Get the first n rows using a criteria ."""
        return first_n_rows(self.table, session, criteria, n)

    def get_all(self, session, criteria = {}) -> list[DeclarativeBase]:
        """ Get all the elements from current table using a criteria ."""
        return all_rows(self.table, session, criteria)

    def iter(self, session, column : str = 'id', size=1000):
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

def get_id(tbl, sess, criteria):
    """ Get the ID of the first element from a table using a criteria ."""
    row = sess.query(tbl.__class__.id).filter_by(**criteria).first()
    return row if row is None else row[0]

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
    try:
        sess.add(tbl)
        sess.flush()
    except Exception as err:
        log.error("Insert ({}) - {}", tbl.__tablename__, err)
    if test:
        sess.rollback()
        log.trace("Insert ({}) - rollback", tbl.__tablename__)
    else:
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
        sess.execute(sa.insert(tbl.__class__), serialize(payload))
    else:
        if do_update:
            #@todo: test this if works
            for k, v in serialize(payload):
                setattr(x, k, v)
        else:
            log.trace(f"{tbl.__tablename__} ok: {name}")

    return first_row(tbl, sess, which)


def windowed_query(session, stmt, column, windowsize) -> [sa.Result[any]]:
    """Given a Session and Select() object, organize and execute the statement
    such that it is invoked for ordered chunks of the total result.   yield
    out individual sa.Result objects for each chunk.

    """

    # add the column we will window / sort on to the statement
    stmt = stmt.add_columns(column).order_by(column)
    last_id = None

    while True:
        subq = stmt

        # filter the statement on the previous "last id" we got, if any
        if last_id is not None:
            subq = subq.filter(column > last_id)

        # execute the query
        result: sa.Result = session.execute(subq.limit(windowsize))

        # turn the sa.Result into a FrozenResult that we can peek at the data
        # first, then spin off new sa.Result objects
        frozen_result = result.freeze()

        # get the raw data
        chunk = frozen_result().all()

        if not chunk:
            break

        # count how many columns we have and also get the "last id" fetched
        result_width = len(chunk[0])
        last_id = chunk[-1][-1]

        # get a new, unconsumed sa.Result back from the FrozenResult
        yield_result: sa.Result = frozen_result()

        # split off the last column (sa.Result could use a slice method here)
        yield_result = yield_result.columns(*list(range(0, result_width - 1)))

        # yield it out
        yield from yield_result.scalars()


def iter_rows(tbl, sess, column : str = 'id', size=1000) -> [DeclarativeBase]:
    """"Break a Query into windows of size on a given column."""
    stmt = sa.select(tbl.__class__)
    column = getattr(tbl.__class__, column)

    for result in windowed_query(sess, stmt, column, size):
        yield result

