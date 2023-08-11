from . import conn
from .base import ORMBase
from .ops import Operation
from .utils import new_unique_key

__version__ = "0.0.1"
__author__ = "Akhlak Mahmood"

ENG = None
SSH = None
SES = None

import sett
ssh_host = sett.PostGres.ssh_host
ssh_port = 21 if sett.PostGres.ssh_port is None else sett.PostGres.ssh_port
ssh_user = sett.PostGres.ssh_user
ssh_pass = sett.PostGres.ssh_pass

db_host = sett.PostGres.db_host
db_port = sett.PostGres.db_port
db_user = sett.PostGres.db_user
db_pass = sett.PostGres.db_pswd
db_name = sett.PostGres.db_name


def connect():
    global SSH, ENG, SES
    if SSH is None:
        SSH = conn.ssh_tunnel(
            ssh_host, ssh_port, ssh_user, ssh_pass, db_host, db_port)
    if ENG is None:
        ENG = conn.setup_engine(
            db_host, db_port, db_user, db_pass, db_name, proxy=SSH)
    if SES is None:
        SES = conn.new_session(ENG)
    return SES

def disconnect():
    global SSH, ENG, SES
    if SES is not None:
        SES.close()
    if SSH is not None:
        SSH.stop()

def engine():
    connect()
    return ENG
