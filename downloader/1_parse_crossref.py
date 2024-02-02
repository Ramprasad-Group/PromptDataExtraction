""" Download the dois for the latest journal articles
    Using cross-ref API.
"""
## --------- * --------------------- * -----------------------------------------
QUERY   = 'ring opening metathesis'      # Crossref search query
CUTOFF  = '2022-01-01'                   # Crossref from cutoff yyyy-mm-dd
USESSH  = False                          # Create ssh tunnel to db

class database:
    db_host = 'localhost'
    db_port = 5460
    db_name = 'polylet'
    db_user = 'akhlak'
    db_pswd = open('db_pass.txt').read().strip()
    ssh_rpt = 5454
    ssh_usr = 'akhlak@tyrion2.mse.gatech.edu'

## --------- * --------------------- * -----------------------------------------

import os
import db
import time
from datetime import datetime

if USESSH and not db.ssh_tunnel(
    database.db_port, database.ssh_rpt, database.ssh_usr):
    exit(1)

db.connect(database)
os.environ['CR_API_AGENT'] = "crossref-commons/0.0.7 (https://ramprasad.mse.gatech.edu/; mailto:amahmood45@gatech.edu) Ramprasad Research Group"

tabl = db.Table("crossref_papers",
    query       = "varchar NOT NULL",
    cutoff_date = "timestamptz NOT NULL",
    publisher   = "varchar NOT NULL",
    doi         = "varchar NOT NULL UNIQUE",
    title       = "varchar NOT NULL",
    pub_date    = "timestamptz NOT NULL",
    crossref_member = "varchar NULL",
    journal     = "varchar NULL",
    status      = "varchar NULL",
    filepath    = "varchar NULL",
)

# tabl.index('doi', 'varchar')
# tabl.create_all(drop_existing=False)

from crossref_commons.iteration import iterate_publications_as_json

filters = {'from-pub-date': CUTOFF, 'type': 'journal-article'}
queries = {'query': QUERY, 'sort': 'published'}

i = 0
for p in iterate_publications_as_json(max_results=4000, filter=filters, queries=queries):
    i += 1
    print(i, p['DOI'], p['title'], p['created']['date-time'])
    # print(p)

    sql = f"SELECT id FROM {tabl._tblname} WHERE doi=%(doi)s;"
    if db.raw_sql(sql, doi=p['DOI']):
        print("Already exists in DB.")
        continue

    tabl.insert_row(
        query       = QUERY,
        cutoff_date = datetime.strptime(CUTOFF, '%Y-%m-%d'),
        publisher   = p.get('publisher', 'Unknown'),
        doi         = p['DOI'],
        pub_date    = datetime.strptime(p['created']['date-time'], '%Y-%m-%dT%H:%M:%S%z'),
        title       = p.get('title', ['NO TITLE'])[0],
        crossref_member = p.get('member'),
        journal     = None,
        status      = "crossref",
        filepath    = None,
    )
    print("Added to DB.")
