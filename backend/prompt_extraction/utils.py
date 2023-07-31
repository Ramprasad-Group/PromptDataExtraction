import json
import spacy
import logging

from pymongo import MongoClient
from collections import namedtuple

logger = logging.getLogger()
logging.basicConfig()


def connect_database():
    """Connects to the database containing the text version of all our data"""
    db_name = 'corpus'
    client = MongoClient('localhost', port=5455)
    # client.admin.authenticate(user, pwd, source=db_name)
    db = client[db_name]
    return db


def connect_remote_database(user='admin', pwd='EntyWeSTEREc'):
    """Connects to the database containing the text version of all our data"""
    db_name = 'polymer_records'
    client = MongoClient('gaanam4.mse.gatech.edu', username=user, password=pwd, authSource=db_name, port=8161)
    # client.admin.authenticate(user, pwd, source=db_name)
    db = client[db_name]
    return db


def compute_metrics(ground_truth, extracted):
    """Compute the metrics for the extracted data"""
    tp, fp, fn, tn = 0, 0, 0, 0
    error_doi_set = set()
    for doi, item_list in ground_truth.items():
        extracted_list = extracted.get(doi, None)
        if extracted_list is not None:
            for record in item_list:
                material_coreferents = record['material_coreferents']
                property_value = str(record['property_value'])
                for item in extracted_list:
                    extracted_property_value = item['property_value']
                    if type(item['material']) is not str:
                        logger.info(f"material key is not a string for {doi} {item['material']}")
                        continue
                    if extracted_property_value is not None and extracted_property_value!='N/A':
                        extracted_property_value = extracted_value_postprocessing(extracted_property_value)
                        if extracted_property_value is None:
                            logger.info(f'Extracted property value is not a string or a well formed dict for {doi}: {extracted_property_value}')
                            continue
                        property_flag = compare_property_value(extracted_property_value, property_value)
                        material_flag = any([entity_postprocess(item['material']) in entity_postprocess(material) or entity_postprocess(material) in entity_postprocess(item['material']) for material in material_coreferents])
                        if material_flag and property_flag: # Fuzzier notion of matching
                            tp += 1
                            break
                        elif property_flag:
                            logger.info(f'For {doi} and {item["material"]} property value match {extracted_property_value} but material entity does not match. True coreferents {material_coreferents}')
                        elif material_flag:
                            logger.info(f'For {doi} material entities match: {item["material"]} but property value does not match. True property value: {property_value}; Extracted property value: {extracted_property_value}')
                    
                else:
                    fn += 1
                    error_doi_set.add(doi)
                    logger.info(f'False negative for DOI {doi}: {record}')
        else:
            fn += len(item_list)
            error_doi_set.add(doi)
            logger.info(f'False negative: {item_list}, DOI {doi} not in extracted dataset')
    
    for doi, item_list in extracted.items():
        ground_truth_list = ground_truth[doi]
        for item in item_list:
            # material = item['material']
            extracted_property_value = item['property_value']
            if extracted_property_value is not None and extracted_property_value!='N/A':
                extracted_property_value = extracted_value_postprocessing(extracted_property_value)
                if extracted_property_value is None:
                    logger.info(f'Extracted property value is not a string or a well formed dict for {doi}: {extracted_property_value}')
                    fp += 1
                    error_doi_set.add(doi)
                    continue
                # Check if the extracted data has the same material coreferents
                for record in ground_truth_list:
                    property_value = str(record['property_value'])
                    # break_flag = compare_property_value(extracted_property_value, property_value)
                    if any([entity_postprocess(item['material']) in entity_postprocess(material) or entity_postprocess(material) in entity_postprocess(item['material']) for material in record['material_coreferents']]):
                        if compare_property_value(extracted_property_value, property_value):
                            break
                else:
                    fp += 1
                    error_doi_set.add(doi)
                    logger.info(f'False positive: {item} for DOI {doi}')
            else:
                fp += 1
                error_doi_set.add(doi)
                logger.info(f'False positive: {item} for DOI {doi}')

    if tp+fp>=0:
        precision = tp / (tp + fp)
    else:
        precision = 0
    if tp+fn>=0:
        recall = tp / (tp + fn)
    else:
        recall = 0
    if precision+recall>0:
        f1 = 2 * (precision * recall) / (precision + recall)
    else:
        f1 = 0

    logger.info(f'Precision: {precision}')
    logger.info(f'Recall: {recall}')
    logger.info(f'F1: {f1}')

    return precision, recall, f1, list(error_doi_set)

def extracted_value_postprocessing(extracted_property_value):
    if type(extracted_property_value) is str:
        extracted_property_value = property_postprocessing(extracted_property_value)
    elif type(extracted_property_value) is dict and all([type(val) is str for val in extracted_property_value.values()]):
        logger.info(f'Extracted property value is dict: {extracted_property_value}')
        extracted_property_value = [property_postprocessing(val) for val in extracted_property_value.values()]
    elif type(extracted_property_value) is int or type(extracted_property_value) is float:
        extracted_property_value = str(extracted_property_value)
    elif type(extracted_property_value) is list and all([type(val) is str for val in extracted_property_value]):
        pass

    else:
        extracted_property_value = None

    return extracted_property_value

def property_postprocessing(property_value: str) -> str:
    property_value = property_value.replace('°C', '° C')
    return property_value

def entity_postprocess(entity: str) -> str:
    entity = entity.replace(' ', '').lower()
    return entity

def compare_property_value(extracted_property_value, property_value)->bool:
    break_flag = False
    if type(extracted_property_value) is str:
        if property_value in extracted_property_value or extracted_property_value in property_value:
            break_flag = True
    elif type(extracted_property_value) is list:
        for ex in extracted_property_value:
            if entity_postprocess(property_value) in entity_postprocess(ex) or entity_postprocess(ex) in entity_postprocess(property_value):
                break_flag = True
                break
    
    return break_flag

class LoadNormalizationDataset:
    def __init__(self, curated_normalized_data=None, test_normalized_data=None):
        if curated_normalized_data is None:
            self.curated_normalized_data = '/home/pranav/projects/materials_ml/data/normalized_polymer_dictionary.json'
        else:
            self.curated_normalized_data = curated_normalized_data
        if test_normalized_data is None:
            self.test_normalized_data = '/home/pranav/projects/supervised_clustering/data/test_dataset.json'
        else:
            self.test_normalized_data = test_normalized_data

    def process_normalization_files(self):
        """Read the json files associated with train and test for normalization and return them"""
        with open(self.curated_normalized_data, 'r') as fi:
            train_data_text = fi.read()
        with open(self.test_normalized_data, 'r') as fi:
            test_data_text = fi.read()
        train_data = json.loads(train_data_text)
        test_data = json.loads(test_data_text)

        return train_data, test_data


def ner_feed(seq_pred, text):
    """Convert outputs of the NER to a form usable by record extraction
        seq_pred: List of dictionaries
        text: str, text fed to sequence classification model
    """
    seq_index = 0
    text_len = len(text)
    seq_len = len(seq_pred)
    start_index = seq_pred[seq_index]["start"]
    end_index = seq_pred[seq_index]["end"]
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(text)
    len_doc = len(doc)
    token = ''
    token_labels = []
    token_label = namedtuple('token_label', ["text", "label"])
    i = 0
    char_index = -1
    while i < len_doc:
        token = doc[i].text
#         print(start_index, char_index)
        if char_index+1>=start_index and seq_index<seq_len:
            # Continue loop till end_index or end of word
            # increment index and values
            current_label = seq_pred[seq_index]["entity_group"]
            while char_index < end_index-1:
                token_labels.append(token_label(token, current_label))
                char_index+=len(token)
                if char_index<text_len-1 and text[char_index+1]==' ': char_index+=1
                i+=1
                if i < len_doc: token=doc[i].text
            seq_index+=1
            if seq_index < seq_len:
                start_index = seq_pred[seq_index]["start"]
                end_index = seq_pred[seq_index]["end"]
        else:
            token_labels.append(token_label(token, 'O'))
            i+=1
            char_index += len(token)
            if char_index<text_len-1 and text[char_index+1]==' ': char_index+=1
    
    return token_labels

def config_plots(mpl):
    mpl.rc('figure', titlesize=18, figsize=(7, 6.5))
    mpl.rc('font', family='Palatino Linotype', size=20, weight='bold')
    # mpl.rc('font', size=24)
    mpl.rc('xtick', labelsize=18, direction='in')
    #mpl.rcParams['xtick.major.size'] = 20
    #mpl.rcParams['xtick.major.width'] = 4
    mpl.rc('xtick.major', size=8, width=2)
    mpl.rc('ytick.major', size=8, width=2)
    mpl.rc('ytick', labelsize=18, direction='in')
    mpl.rc('axes', labelsize=18, linewidth=2.5, labelweight="bold")
    mpl.rc('savefig', bbox='tight', dpi=300)
    mpl.rc('lines', linewidth=1, markersize=5)
    mpl.rc('legend', fontsize=13)