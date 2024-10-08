import sqlalchemy as sa
from sqlalchemy import exc
from collections import namedtuple
from sqlalchemy.orm import scoped_session

from . import conn



__version__ = "0.0.1"
__author__ = "Akhlak Mahmood"

SSH = None
ENG : sa.Engine = None
CON : sa.Connection = None

class ssh:
    host = ''
    port = 22
    user = ''
    pswd = ''

class db:
    host = 'localhost'
    port = 5254
    user = 'admin'
    pswd = ''
    name = 'postgres'

def load_settings():
    from .. import sett
    ssh.host = sett.PostGres.ssh_host
    ssh.port = 22 if sett.PostGres.ssh_port is None else sett.PostGres.ssh_port
    ssh.user = sett.PostGres.ssh_user
    ssh.pswd = sett.PostGres.ssh_pass
    db.host = sett.PostGres.db_host
    db.port = sett.PostGres.db_port
    db.user = sett.PostGres.db_user
    db.pswd = sett.PostGres.db_pswd
    try:
        db.name = sett.Run.databaseName
    except:
        db.name = sett.PostGres.db_name


def connect(database = None) -> scoped_session:
    global SSH, ENG, CON

    if database is not None:
        db.name = database

    if SSH is None:
        SSH = conn.ssh_tunnel(
            ssh.host, ssh.port, ssh.user, ssh.pswd, db.host, db.port)

    if ENG is None:
        ENG = conn.setup_engine(
            db.host, db.port, db.user, db.pswd, db.name, proxy=SSH)
        
    if CON is None or CON.closed:
        CON = ENG.connect()

    return conn.new_session(CON)


def disconnect():
    global SSH, CON
    if CON is not None:
        CON.close()

    if SSH is not None:
        SSH.stop()

def session() -> scoped_session:
    """ Connect and return a new SQLAlchemy session. """
    if CON is None:
        return connect()
    return conn.new_session(CON)


def engine():
    connect()
    return ENG


def raw_sql(query : str, params : dict = {}, commit = False, **kwargs) -> list[namedtuple]:
    """
        Execute a raw sql query on the database.
        
        Ex. result = raw_sql('SELECT * FROM my_table WHERE my_column = :val', {'val': 5})

        Returns a list of rows or results object
    """
    kwargs.update(dict(params))
    sess = session()
    results = sess.execute(sa.text(query), kwargs)
    if commit:
        sess.execute(sa.text("COMMIT"), kwargs)

    sess.close()

    try:
        Row = namedtuple('Row', results.keys())
        return [Row(*r) for r in results.fetchall()]
    except exc.ResourceClosedError:
        # Handle queries that don't return any result.
        return results
