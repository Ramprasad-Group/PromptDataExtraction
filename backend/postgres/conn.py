from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sshtunnel import SSHTunnelForwarder

import pylogg
log = pylogg.New('postgres')


def ssh_tunnel(host, port, user, pswd,
               fwd_host, fwd_port) -> SSHTunnelForwarder | None:
    """Create a SSH tunnel to a remove host and port. """

    if len(host) > 0:
        server = SSHTunnelForwarder((host, port),
            ssh_username=user,
            ssh_password=pswd,
            remote_bind_address=(fwd_host, fwd_port),
        )
        server.start()
        log.info("SSH tunnel established.")
        return server
    else:
        log.trace("SSH tunnel skipped.")
        return None


def setup_engine(host, port, user, pswd, name,
        *, proxy : SSHTunnelForwarder = None, db_url = None):
    t2 = log.trace("Connecting to PostGres.")
    if db_url is None:
        if proxy is None:
            db_url = "postgresql+psycopg2://{}:{}@{}:{}/{}".format(
                user, pswd, host, port, name)
        else:
            db_url = "postgresql+psycopg2://{}:{}@{}:{}/{}".format(
                user, pswd, proxy.local_bind_host, proxy.local_bind_port, name)
    engine = create_engine(db_url)
    t2.note("Connected to PostGres DB: {}", name)
    return engine


def new_session(engine) -> scoped_session:
    connection = engine.connect()
    session = scoped_session(
        sessionmaker(
            autocommit=False, autoflush=False, expire_on_commit=False,
            bind=connection)
    )
    return session

