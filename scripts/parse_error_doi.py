import os
import sys
import sett
import json
import pylogg as log

from backend.data import mongodb

from backend import postgres
from backend.postgres.orm import FilteredPapers, PaperTexts, Papers

from backend.utils.frame import Frame
from backend.parser import PaperParser
from backend.parser.document import DocumentParser
from backend.parser.paragraph import ParagraphParser

import re


sett.load_settings()
postgres.load_settings()
db = postgres.connect()

publishers_directory = {'SAGE Publications': None, 'American Physical Society (APS)': None , 'Springer New York': 'springer', 
                'American Association for the Advancement of Science (AAAS)': None, 'Maney Publishing': None, 
                'Wiley': 'wiley', 'Springer Science and Business Media LLC': 'springer', 'Rubber Division, ACS': 'acs', 
                'Institute of Electrical and Electronics Engineers (IEEE)':None, 'Royal Society of Chemistry': 'rsc', 
                'Springer Netherlands': 'springer', 'The Electrochemical Society': 'ecs', 'Mark Allen Group': None,
                'AIP Publishing': 'aip', 'Pleiades Publishing Ltd': None, 'Springer Nature' : ['springer', 'nature'], 
                'Society for Mining, Metallurgy and Exploration Inc.': None, 
                'Royal Society of Chemistry (RSC)': 'rsc', 'Elsevier': 'elsevier', 'Elsevier BV': 'elsevier', 
                'Springer International Publishing': 'springer', 'Springer Singapore': 'springer', 
                'Island Press': None, 'Springer-Verlag': 'springer', 'Informa UK Limited': 'informa_uk', 'IEEE': None, 
                'Oxford University Press (OUP)': None, 'Springer US': 'springer', 'Hindawi Limited': 'hindawi', 
                'Springer Berlin Heidelberg': 'springer', 'Wiley-VCH Verlag GmbH & Co. KGaA': 'wiley', 
                'IOP Publishing': 'iop_publishing', 'American Chemical Society (ACS)': 'acs'}


def filename2doi(doi : str):
    doi = doi.replace("@", "/").rstrip('.html')
    doi = doi.rstrip(".xml")
    return doi


def doi2filename(doi, publisher):
    """Convert DOI to a file_name"""
    extension='.html'
    if publisher.lower()=='elsevier' or publisher.lower()=='acs':
        extension='.xml'
    doi = doi.replace('/', '@') + extension
    return doi

def remove_parentheses(word):
    return re.sub(r'\(|\)', '', word)


def add_to_postgres(paper : Papers, publisher : str, doctype : str,
                    para : ParagraphParser):
    """ Add a paragraph text to postgres if it already does not
        exist in the database.
    """

    paragraph = PaperTexts().get_one(db, {'doi': paper.doi, 'text': para.text})
    if paragraph is not None:
        log.trace(f"Paragraph in PostGres: {para.text}. Skipped.")
        return False
    
    paragraph = PaperTexts()
    paragraph.pid = paper.id
    paragraph.pub = publisher
    paragraph.doi = paper.doi
    paragraph.doctype = doctype
    paragraph.section = None
    paragraph.tag = None
    paragraph.text = para.text
    paragraph.insert(db)

    log.trace(f"Added to PostGres: {para.text}")

    return True


def parse_file(filepath, root = "") -> DocumentParser | None:    
    # Keep count of added items for statistics
    pg =  0

    filename = os.path.basename(filepath)
    formatted_name = filepath.replace(root, "")

    doi = filename2doi(filename)
    publisher = filepath.split("/")[-2]

    doc = PaperParser(publisher, filepath)
    if doc is None:
        log.warn(f"Ignore: {formatted_name} (Parser not found)")
        return None, pg

    try:
        doc.parse(parse_tables=False)
        log.trace("Parsed document: {}", filepath)
        log.trace("Found {} paragraphs", len(doc.paragraphs))
    except Exception as err:
        log.error("Failed to parse: {} ({})", formatted_name, err)
        return None, pg

    if sett.FullTextParse.debug:
        for para in doc.paragraphs:
            print("\t", "-" * 50)
            print("\t", para.text, flush=True)

    if sett.FullTextParse.add2postgres:
        # get the foreign key
        paper = Papers().get_one(db, {'doi': doi})

        for para in doc.paragraphs:
            if paper is None:
                log.warn(f"{doi} not found in postgres.")
                break

            elif add_to_postgres(paper, publisher, doc.doctype, para):
                pg += 1

        db.commit()

    return doc, pg


def walk_publisher_files(parse_pub: str):
    """ Recursively walk a directory containing literature files.
        Create a CSV list by parsing meta information.
    """
    outcsv = sett.FullTextParse.runName + "/parse_papers" + '_' + parse_pub + '.csv'
    directory = sett.FullTextParse.paper_corpus_root_dir + '/' + parse_pub

    # How many files to parse
    max_files = sett.FullTextParse.debugCount \
        if sett.FullTextParse.debug else -1

    log.info(f'Walking files that were not parsed correctly belonging to publisher: {parse_pub}' )
    df = Frame()

    # Recursively crawl the wrongly parsed files 
    with open('poly_error_doi.json', 'r') as file:
        data = json.load(file)
    
    n = 1
    total_pg = 0

    for item in data:

        if publishers_directory[item['publisher']] == parse_pub:

            log.info(f'-----------looking at doi {item["doi"]}')

            filename =  doi2filename(item['doi'], publisher= publishers_directory[item['publisher']])
            found_file_path = None

            for root, dirs, files in os.walk(directory):
    
                if filename in files:
                    found_file_path = os.path.join(root, filename)
                    break  

            if found_file_path:
                log.note(f'File "{item["doi"]}" found at: {found_file_path}')
                doc, pg = parse_file(found_file_path, directory)

                if doc is None:
                    continue

                df.add(filename=filename, filepath=doc.docpath, ftype=doc.doctype,
                        publisher=doc.publisher, npara=len(doc.paragraphs),
                        postgres_added=pg)
                
                # Not more than max_files per directory
                # Use -1 for no limit.

                n += 1
                total_pg += pg

                if (n-1) % 50 == 0:
                    log.info("Processed {} papers. Added {} paragraphs to Postgres.",
                            n-1, total_pg)

                if max_files > 0 and n > max_files:
                    log.note("Processed maximum {} papers.", n-1)
                    log.info("Added {} paragraphs to Postgres, ", total_pg)
                    break

            else:
                log.note(f'File "{item["doi"]}" not found in the directory.')


    # save the file list
    df.save(outcsv)



def publisher_check():

    directory_path = '/data/pranav/prod/structured_files'

    with open('doi_error.json', 'r') as file:
        data = json.load(file)

    found_file_paths = []

    for itm in data[:10]:
        file_html, file_xml = doi2filename(itm['doi'])
        # publisher = itm['publisher'].split()
        # pub = [remove_parentheses(word) for word in publisher]
        found_file_path = None
        directory = None

        for root, dirs, files in os.walk(directory_path):

            if file_html in files:
                directory = root.split('/')[-1]
                found_file_path = os.path.join(root, file_html)
                break  
            elif file_xml in files:
                directory = root.split('/')[-1]
                found_file_path = os.path.join(root, file_xml)
                break

        if found_file_path:
            log.note(f'File "{itm["doi"]}" found at: {found_file_path}')

        else:
            log.note(f'File "{itm["doi"]}" not found in the directory.')
        
        found_file_paths.append({'doi': itm['doi'], 'publisher': itm['publisher'],
                                'file_path': found_file_path, 'directory': directory})
 

    with open("error_doi_paths_test.json", "w") as json_file:
        json.dump(found_file_paths, json_file, indent=2)



def log_run_info():
    """
        Log run information for reference purposes.
        Returns a log Timer.
    """
    t1 = log.note("FullTextParse Run: {}", sett.FullTextParse.runName)
    log.info("CWD: {}", os.getcwd())
    log.info("Host: {}", os.uname())

    if sett.FullTextParse.debug:
        log.note("Debug run. Will parse maximum {} files.",
                 sett.FullTextParse.debugCount)
    else:
        log.note("Production run. Will parse all files in {}",
                 sett.FullTextParse.paper_corpus_root_dir)

    log.info("Using loglevel = {}", sett.FullTextParse.loglevel)

    if not sett.FullTextParse.add2mongo:
        log.warn("Will not be adding to mongodb.")
    else:
        log.note("Will be adding to mongo collection: {}",
                 sett.FullTextParse.mongodb_collection)

    return t1


if __name__ == '__main__':
    
    os.makedirs(sett.FullTextParse.runName, exist_ok=True)
    log.setFile(open(sett.FullTextParse.runName+"/parse_papers_wiley.log", "w+"))
    log.setLevel(sett.FullTextParse.loglevel)
    log.setFileTimes(show=True)
    log.setConsoleTimes(show=True)

    t1 = log_run_info()

    if len(sys.argv) > 1:
        parse_file(sys.argv[1])
    else:
        walk_publisher_files(parse_pub= 'wiley')

    t1.done("All Done.")


