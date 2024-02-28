""" Download the dois for the latest journal articles
    Using cross-ref API.
"""
## --------- * --------------------- * -----------------------------------------
USESSH  = False                          # Create ssh tunnel to db

# Name of the publisher to download papers from.
PUBLISHER = 'Wiley'

# Settings for PG database connection.
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
from tqdm import tqdm
from datetime import datetime
from playwright.sync_api import sync_playwright

outdir = 'data/papers/'

publishers_directory = {
    'Wiley': 'wiley',
    'Springer Science and Business Media LLC': 'springer',
    'Rubber Division, ACS': 'acs', 
    'Institute of Electrical and Electronics Engineers (IEEE)': 'ieee',
    'Royal Society of Chemistry': 'rsc', 
    'Springer Netherlands': 'springer',
    'The Electrochemical Society': 'ecs',
    'AIP Publishing': 'aip',
    'Springer Nature' : 'springer', 
    'Royal Society of Chemistry (RSC)': 'rsc',
    'Elsevier': 'elsevier',
    'Elsevier BV': 'elsevier', 
    'Springer International Publishing': 'springer',
    'Springer Singapore': 'springer', 
    'Springer-Verlag': 'springer',
    'Informa UK Limited': 'informa_uk',
    'IEEE': 'ieee', 
    'Springer US': 'springer',
    'Hindawi Limited': 'hindawi', 
    'Springer Berlin Heidelberg': 'springer',
    'Wiley-VCH Verlag GmbH & Co. KGaA': 'wiley', 
    'IOP Publishing': 'iop_publishing',
    'American Chemical Society (ACS)': 'acs'
}


assert PUBLISHER in publishers_directory, f"{PUBLISHER} not listed as a known publisher."

if USESSH and db.ssh_tunnel(
    database.db_port, database.ssh_rpt, database.ssh_usr):
    exit(1)

db.connect(database)


sql = f"""
SELECT doi FROM crossref_papers
WHERE publisher = %(pub)s
AND status <> 'downloaded';
"""

rows = db.raw_sql(sql, pub=PUBLISHER)

print("Found %d rows in DB." %len(rows))

p = sync_playwright().start()
browser = p.chromium.launch()

if os.path.isfile('state.json'):
    # Create a new context with the saved storage state.
    context = browser.new_context(storage_state="state.json")
    print("Load OK: state.json")
else:
    context = browser.new_context()

page = context.new_page()

for row in tqdm(rows):
    doi = row.doi
    url = "https://doi.org/" + doi
    fname = doi.replace("/", "@")
    directory = publishers_directory[PUBLISHER]

    os.makedirs(outdir + directory, exist_ok=True)
    outfile = os.path.join(directory, fname + ".html")
    outpath = os.path.join(outdir, outfile)

    print(doi, " ==> ", outfile)

    # Download the file.
    page.goto(url)
    print(page.title())
    page.wait_for_timeout(60*1000)

    print(page.title())
    with open(outpath, 'w') as fp:
        fp.write(page.content())
        print("Save OK:", outpath)

    # Save storage state into the file.
    context.storage_state(path="state.json")
    break

browser.close()
p.stop()

print("Bye!")

