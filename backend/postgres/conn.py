from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

import pylogg
log = pylogg.New('db')

try:
    from sshtunnel import SSHTunnelForwarder
    _remote_access = True
except ImportError:
    _remote_access = False


def ssh_tunnel(host, port, user, pswd,
               fwd_host, fwd_port) -> SSHTunnelForwarder | None:
    """Create a SSH tunnel to a remove host and port. """

    if _remote_access and len(host) > 0:
        server = SSHTunnelForwarder((host, port),
            ssh_username=user,
            ssh_password=pswd,
            remote_bind_address=(fwd_host, fwd_port),
        )
        server.start()
        log.note("SSH tunnel established.")
        return server
    else:
        log.trace("SSH tunnel skipped.")
        return None


def setup_engine(host, port, user, pswd, name,
        *, proxy : SSHTunnelForwarder = None, db_url = None):
    if db_url is None:
        if proxy is None:
            db_url = "postgresql+psycopg2://{}:{}@{}:{}/{}".format(
                user, pswd, host, port, name)
        else:
            db_url = "postgresql+psycopg2://{}:{}@{}:{}/{}".format(
                user, pswd, proxy.local_bind_host, proxy.local_bind_port, name)
    engine = create_engine(db_url)
    log.trace("DB engine created.")
    return engine


def new_session(engine) -> scoped_session:
    connection = engine.connect()
    session = scoped_session(
        sessionmaker(autocommit=False, autoflush=False, bind=connection)
    )
    log.trace("DB connected.")
    return session

