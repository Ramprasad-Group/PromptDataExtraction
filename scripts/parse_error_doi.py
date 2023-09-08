#convert doi to filename 
#parse using appropriate parser

import os
import sys
import sett
import json
import pylogg as log
import re

from backend.data import mongodb

from backend.utils.frame import Frame
from backend.parser import PaperParser
from backend.parser.document import DocumentParser
from backend.parser.paragraph import ParagraphParser

sett.load_settings()

db = mongodb.connect()
collection = db[sett.FullTextParse.mongodb_collection]

publishers = {'SAGE Publications': None, 'American Physical Society (APS)': None , 'Springer New York': 'springer', 
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

def add_to_mongodb(doi : str, publisher : str, doctype : str, para : ParagraphParser):
    """ Add a paragraph text to new mongodb collection
    """

    if not sett.FullTextParse.add2mongo:
        return False

    itm = collection.find_one({'DOI': doi})
    if itm is None:
        log.error(f"{doi} not found in MongoDB.")
        return False
    
    fulltext = itm.get('full_text')
    newsection = {
        "type": 'paragraph',
        "pub": publisher,
        "format": doctype,
        "name": "main",
        "content": [para.text.strip()]
    }

    if fulltext is not None:
        for section in fulltext:
            if 'content' in section:
                if para.text.strip() in section['content']:
                    log.trace(f"Paragraph in MongoDB: {para.text}. Skipped.")
                    return False
        fulltext.append(newsection)
    else:
        fulltext = [newsection]

    record_id = itm.get('_id')
    collection.update_one({"_id": record_id}, {
            "$set": {
                "full_text": fulltext
            }
        }
    )

    log.trace(f"Add to MongoDB: {para.text}")
    return True

def parse_file(doi, filepath, publisher, root = "") -> DocumentParser | None:    
    # Keep count of added items for statistics
    mn = 0

    # filename = os.path.basename(filepath)
    # formatted_name = filepath.replace(root, "")

    # doi = filename2doi(filename)
    # publisher = filepath.split("/")[-2]

    doc = PaperParser(publisher, filepath)
    # if doc is None:
    #     log.warn(f"Ignore: {doi} (Parser not found)")
    #     return None, mn

    try:
        doc.parse(parse_tables=False)
        log.trace("Parsed document: {}", filepath)
        log.trace("Found {} paragraphs", len(doc.paragraphs))
    except Exception as err:
        log.error("Failed to parse: {} ({})", doi, err)
        return None

    for para in doc.paragraphs:
        if sett.FullTextParse.debug:
            print("\t", "-" * 50)
            print("\t", para.text, flush=True)

        if add_to_mongodb(doi, publisher, doc.doctype, para):
            mn += 1

    db.commit()

    return doc

def walk_json_list():
    """ Recursively walk a directory containing literature files.
        Create a CSV list by parsing meta information.
    """
    outcsv = sett.FullTextParse.runName + "/parse_papers__error_doi_info.csv"
    directory = sett.FullTextParse.paper_corpus_root_dir

    # How many files to parse
    max_files = sett.FullTextParse.debugCount \
        if sett.FullTextParse.debug else -1

    log.info("Walking error files " )
    df = Frame()

    # Recursively crawl the wrongly parsed files 
    with open('doi_error_paths.json', 'r') as file:
        data_paths = json.load(file)

    # new_collection = db["error_doi_fulltext"]

    # for item in data_paths:
    #     if item['file_path']:
    #         if item['directory']:
    #             log.note(f'Parsing file "{item["doi"]}" located in "{item["directory"]}".')
    #             doc = parse_file(item['doi'], item['file_path'], item['directory'])

    #             if doc is None:
    #                 continue

    #             df.add(filename=item['doi'], filepath=doc.docpath, ftype=doc.doctype,
    #                     publisher=doc.publisher, npara=len(doc.paragraphs))
    #         else:
    #             log.note(f'Directory "{item["directory"]}" not found.')
    #     else:
    #         log.note(f'File "{item["doi"]}" not found.')

    with open('doi_error.json', 'r') as file:
        data = json.load(file)

    
    for item in data:
        if publishers[item['publisher']] == None:
            log.note('Publisher not found. Skipped')
        else:
            file_html, file_xml = doi2filename(item['doi'])
            found_file_path = None
            directory = None
            for root, dirs, files in os.walk(directory):
    
                if file_html in files:
                    directory = root.split('/')[-1]
                    found_file_path = os.path.join(root, file_html)
                    break  

                elif file_xml in files:
                    directory = root.split('/')[-1]
                    found_file_path = os.path.join(root, file_xml)
                    break

            if found_file_path:
                log.note(f'File "{item["doi"]}" found at: {found_file_path}')
                doc = parse_file(found_file_path, directory)

            else:
                log.note(f'File "{item["doi"]}" not found in the directory.')
            

            
        # query = {'DOI': item['doi'],'publisher': item['publisher']}
        # res= collection.find(quer


    # for root, subdirs, files in os.walk(directory):
    #     n = 1
    #     total_pg = 0
    #     total_mn = 0
    #     log.trace("Entering: %s" %root)

    #     for filename in files:
    #         abs_path = os.path.join(root, filename)
    #         doc, pg, mn = parse_file(abs_path, directory)

    #         if doc is None:
    #             continue

    #         df.add(filename=filename, filepath=doc.docpath, ftype=doc.doctype,
    #                 publisher=doc.publisher, npara=len(doc.paragraphs),
    #                 postgres_added=pg, mongodb_added=mn)

    #         # Not more than max_files per directory
    #         # Use -1 for no limit.
    #         n += 1
    #         total_pg += pg
    #         total_mn += mn

    #         if (n-1) % 50 == 0:
    #             log.info("Processed {} papers. Added {} paragraphs to Postgres."
    #                      " Added {} paragraphs to MongoDB",
    #                      n-1, total_pg, total_mn)

    #         if max_files > 0 and n > max_files:
    #             log.note("Processed maximum {} papers.", n-1)
    #             log.info("Added {} paragraphs to Postgres, "
    #                      "{} paragraphs to MongoDB.", total_pg, total_mn)
    #             break

    # # save the file list
    # df.save(outcsv)


def filename2doi(doi : str):
    doi = doi.replace("@", "/").rstrip('.html')
    doi = doi.rstrip(".xml")
    return doi

def doi2filename(doi: str) -> str:
    # if "(" in doi or ")" in doi:
    #     doi = doi.replace("(", "\(").replace(")", "\)")
    doi_html = doi.replace("/", "@") + ".html"
    doi_xml = doi.replace("/", "@") + ".xml"
    return doi_html, doi_xml


def remove_parentheses(word):
    return re.sub(r'\(|\)', '', word)


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
            # match_found= False
            # for dir in dirs:
            #     subdir_path = os.path.join(root, dir)
            #     if any(word.lower() in dir.lower() for word in pub):
            #         directory = dir
            #         if os.path.exists(os.path.join(subdir_path, file_html)):
            #             found_file_path = os.path.join(subdir_path, file_html)
            #             match_found = True
            #             break
            #         elif os.path.exists(os.path.join(subdir_path, file_xml)):
            #             found_file_path = os.path.join(subdir_path, file_xml)
            #             match_found = True
            #             break
            #     if match_found:
            #         break

            # if not found_file_path:
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

    # if sett.FullTextParse.debug:
    #     log.note("Debug run. Will parse maximum {} files.",
    #              sett.FullTextParse.debugCount)
    # else:
    #     log.note("Production run. Will parse all files in {}",
    #              sett.FullTextParse.paper_corpus_root_dir)

    # log.info("Using loglevel = {}", sett.FullTextParse.loglevel)

    # if not sett.FullTextParse.add2mongo:
    #     log.warn("Will not be adding to mongodb.")
    # else:
    #     log.note("Will be adding to mongo collection: {}",
    #              sett.FullTextParse.mongodb_collection)

    return t1

def publisher_existance():

    with open('doi_error.json', 'r') as file:
        data = json.load(file)

    print(len(data))
    
    # doi_publisher = {}
    # for pub in publishers.keys():
    #     if publishers[pub] == None:
    #         doi_list = []
    #         for item in data:
    #             if item["publisher"] == pub:
    #                 doi_list.append(item["doi"])
    #                 if len(doi_list) >= 100:
    #                     print(pub, "doi_list made")
    #                     break

    #         doi_publisher[pub]= doi_list

    # directory_path = '/data/pranav/prod/structured_files'
    
    # found_file_paths = []
    # for key, value in doi_publisher.items():
    #     print("publisher: ", key)
        
    #     for doi in value[:50]:
    #         file_html, file_xml = doi2filename(doi)
    #         found_file_path = None
    #         directory = None
    #         for root, dirs, files in os.walk(directory_path):

    #             if file_html in files:
    #                 directory = root.split('/')[-1]
    #                 found_file_path = os.path.join(root, file_html)
    #                 break  
    #             elif file_xml in files:
    #                 directory = root.split('/')[-1]
    #                 found_file_path = os.path.join(root, file_xml)
    #                 break

    #         if found_file_path:
    #             log.note(f'File "{doi}" found at: {found_file_path}')
    #             publishers[pub] = directory

    #         else:
    #             log.note(f'File "{doi}" not found in the directory.')
                
    #         found_file_paths.append({'publisher': key, 'doi': doi,
    #                                 'file_path': found_file_path, 'directory': directory})

    #         with open("publisher_existence.json", "w") as json_file:
    #             json.dump(found_file_paths, json_file, indent=2)
     
    


if __name__ == '__main__':
    
    os.makedirs(sett.FullTextParse.runName, exist_ok=True)
    log.setFile(open(sett.FullTextParse.runName+"/parse_papers.log", "w+"))
    log.setLevel(sett.FullTextParse.loglevel)
    log.setFileTimes(show=True)
    log.setConsoleTimes(show=True)

    t1 = log_run_info()

    # publisher_check()
    publisher_existance()

#     if len(sys.argv) > 1:
#         parse_file(sys.argv[1])
#     else:
#         walk_directory()

    t1.done("All Done.")


