"""Compute benchmark metrics for the model"""

# Compute F1 score of the binary classification task and the information retrieval task

# Compute score of information retrieval on data extracted by the system


relevant_properties = ['Tg', 'Bandgap']

import argparse
import debugpy

import pandas as pd

from collections import defaultdict, namedtuple
import ast

# from create_dataset import CreatePSCDataset
from utils import jaccard

from itertools import combinations

parser = argparse.ArgumentParser()

parser.add_argument(
    "--debug",
    help="Display debugging print statements",
    action="store_true",
)

parser.add_argument(
    "--use_debugpy",
    help="Use remote debugging",
    action="store_true",
)

parser.add_argument(
    "--align_tuples",
    help="Align tuples using hash for 3-tuple and 2-tuple comparison",
    action="store_true",
)

parser.add_argument(
    "--nlp_generated_file",
    help="Location of curated file",
    default='/home/pranav/projects/PSC_data_analysis/output/polymer_solar_cell_extracted_data.csv',
)

parser.add_argument(
    "--ground_truth_file",
    help="Location of curated file",
    default='/home/pranav/projects/PSC_data_analysis/output/polymer_solar_cell_extracted_data_curated2.xlsx',
)

# TODO: What would tests of this function look like?

# TODO: Specify types in the signature of each function such as tuple, named tuple etc

# TODO: Hash has some kind of overflow error due to their being 18 digits and causes NLP and curated hashes to be read in differently. Affects last 4 digits. 
# Hack solution is to truncate the hash to 13 digits 

#TODO: deduplicate the similar code in nlp_tuple and compute_metrics

# TODO: Modify this code for use in the Tg case

class PSCEval:
    def __init__(self, args) -> None:
        """Compare NLP generated material property value pairs to curated ones and compute statistics accordingly"""
        self.ground_truth_file = args.ground_truth_file
        self.nlp_generated_file = args.nlp_generated_file
        self.debug = args.debug
        self.align_tuples = args.align_tuples # Not used presently
        # self.create_dataset = CreatePSCDataset()
        # initialize dictionary of values used for NLP evaluation
        self.extracted_tuple = namedtuple('extracted_tuple', ['donor', 'acceptor', 'donor_coreferents', 'acceptor_coreferents', 'property_name', 'property_value'])
        self.performance_metrics = {'4-tuple': {'tp': 0, 'fp': 0, 'fn': 0, 'precision': 0, 'recall': 0, 'F1': 0},
                                    '3-tuple': {'tp': 0, 'fp': 0, 'fn': 0, 'precision': 0, 'recall': 0, 'F1': 0},
                                    '2-tuple': {'tp': 0, 'fp': 0, 'fn': 0, 'precision': 0, 'recall': 0, 'F1': 0},
                                    'soft_metric': {'tp': 0, 'fp': 0, 'fn': 0, 'precision': 0, 'recall': 0, 'F1': 0}
                                    }
        self.tuple_entries = ['donor', 'acceptor', 'property_name', 'property_value']
    
    
    def tuple_metrics(self, nlp_tuples, curated_tuples, mode):
        """Compare for each document the extracted tuples"""
        # assert len(curated_tuples[0]) == len(nlp_tuples[0])
        # self.performance_metrics[mode]['tp'] += [all([]) for curated_tuple in nlp_tuples for nlp_tuple in curated_tuples]
        for curated_tuple in curated_tuples:
            for nlp_tuple in nlp_tuples:
                # print(curated_tuple, nlp_tuple)
                if all([entry_curated == entry_nlp for entry_curated, entry_nlp in zip(curated_tuple, nlp_tuple)]):
                    self.performance_metrics[mode]['tp'] += 1
                    break
            else:
                self.performance_metrics[mode]['fn'] += 1
        
        for nlp_tuple in nlp_tuples:
            for curated_tuple in curated_tuples:
                if all([entry_curated == entry_nlp for entry_curated, entry_nlp in zip(curated_tuple, nlp_tuple)]):
                    break
            else:
                self.performance_metrics[mode]['fp'] += 1
    
    def compute_overall_metrics(self):
        for mode in self.performance_metrics:
            self.performance_metrics[mode]['precision'] =  self.performance_metrics[mode]['tp']/(self.performance_metrics[mode]['tp']+self.performance_metrics[mode]['fp']+1E-10)
            self.performance_metrics[mode]['recall'] =  self.performance_metrics[mode]['tp']/(self.performance_metrics[mode]['tp']+self.performance_metrics[mode]['fn']+1E-10)
            self.performance_metrics[mode]['F1'] = 2*self.performance_metrics[mode]['recall']*self.performance_metrics[mode]['precision']/(self.performance_metrics[mode]['recall']+self.performance_metrics[mode]['precision']+1E-10)
    
    def tuple_comparison(self, nlp_tuples, curated_tuples):
        """Compare 4-tuples, 3-tuples and 2-tuples for extracted and ground truth data"""
        # Compare all 4 entries of tuple in ground and curated to obtain 4-tuple true positives and false positives
        # Create all 4-tuples, check if they match exactly
        nlp_4_tuples = [(prop.donor, prop.acceptor, prop.property_name, prop.property_value) for hash, prop_list in nlp_tuples.items() for prop in prop_list]
        curated_4_tuples = [(prop.donor, prop.acceptor, prop.property_name, prop.property_value) for hash, prop_list in curated_tuples.items() for prop in prop_list]
        self.tuple_metrics(nlp_4_tuples, curated_4_tuples, '4-tuple')
        for hash, prop_list in curated_tuples.items():
            if hash in nlp_tuples:
                nlp_3_tuples = [(getattr(property_tuple, entry1), getattr(property_tuple, entry2), getattr(property_tuple, entry3)) for property_tuple in nlp_tuples[hash] for entry1, entry2, entry3 in combinations(self.tuple_entries, 3)]
                curated_3_tuples = [(getattr(property_tuple, entry1), getattr(property_tuple, entry2), getattr(property_tuple, entry3)) for property_tuple in curated_tuples[hash] for entry1, entry2, entry3 in combinations(self.tuple_entries, 3)]
                self.tuple_metrics(nlp_3_tuples, curated_3_tuples, '3-tuple')
                # Construct all 3-tuples and 2-tuples
                nlp_2_tuples = [(getattr(property_tuple, entry1), getattr(property_tuple, entry2)) for property_tuple in nlp_tuples[hash] for entry1, entry2 in combinations(self.tuple_entries, 2)]
                curated_2_tuples = [(getattr(property_tuple, entry1), getattr(property_tuple, entry2)) for property_tuple in curated_tuples[hash] for entry1, entry2 in combinations(self.tuple_entries, 2)]
                self.tuple_metrics(nlp_2_tuples, curated_2_tuples, '2-tuple')
        # Use hash to align 4-tuples during the iteration and compute 2-tuples and 3-tuples and compute metrics
        # Compute all possible 3-tuples and 2-tuples for aligned and non-aligned case and compare, need external argument for the same 
        # For each hash, compute all possible 3 tuples and feed to tuple comparison metric, alternately do this for the sum total of 3-tuples from a document as well depending on external flag


    def soft_metrics(self, nlp_tuples, curated_tuples):
        """Compute soft precision and soft recall according to the below formula using all extracted material entities"""
        # Align using hash and compute soft precision and soft recall
        for hash, prop_list in curated_tuples.items():
            if hash and hash in nlp_tuples:
                for curated_prop_tuple in prop_list:
                    for nlp_prop_tuple in nlp_tuples[hash]:
                        if nlp_prop_tuple.property_name == curated_prop_tuple.property_name and nlp_prop_tuple.property_value == curated_prop_tuple.property_value:
                            nlp_material_list = nlp_prop_tuple.donor_coreferents+nlp_prop_tuple.acceptor_coreferents
                            curated_material_list = curated_prop_tuple.donor_coreferents+curated_prop_tuple.acceptor_coreferents
                            # Need to come up with some metric of overlap between 2 lists
                            if self.debug:
                                print(f'NLP material list is: {nlp_material_list}')
                                print(f'curated material list is: {curated_material_list}\n')
                            self.performance_metrics['soft_metric']['tp'] += jaccard(nlp_material_list, curated_material_list)
                            break
                    else:
                        self.performance_metrics['soft_metric']['fn'] += 1
            else:
                self.performance_metrics['soft_metric']['fn'] += len(prop_list)
            
        for hash, prop_list in nlp_tuples.items():
            if hash and hash in curated_tuples:
                for nlp_prop_tuple in prop_list:
                    for curated_prop_tuple in curated_tuples[hash]:
                        if nlp_prop_tuple.property_name == curated_prop_tuple.property_name and nlp_prop_tuple.property_value == curated_prop_tuple.property_value:
                            break
                    else:
                        self.performance_metrics['soft_metric']['fp'] += 1
            else:
                self.performance_metrics['soft_metric']['fp'] += len(prop_list)
    
    def nlp_tuple(self, df_nlp, prev_doi, curated_tuples):
        df_DOI = df_nlp[df_nlp['DOI']==prev_doi]
        nlp_tuples = defaultdict(list)
        for index_DOI, row_DOI in df_DOI.iterrows():
            # Find all information from NLP extracted data and send both to the evaluation code
            # Can be a named_tuple
            if row_DOI['donor_coreferents']:
                donor_coreferents = ast.literal_eval(row_DOI['donor_coreferents'])
            else:
                donor_coreferents = [row_DOI['donor']]
            if row_DOI['acceptor_coreferents']:
                acceptor_coreferents = ast.literal_eval(row_DOI['acceptor_coreferents'])
            else:
                acceptor_coreferents = [row_DOI['acceptor']]

            if not donor_coreferents:
                donor_coreferents = [row_DOI['donor']]
            if not acceptor_coreferents:
                acceptor_coreferents = [row_DOI['acceptor']]
            for property_name in relevant_properties:
                if row_DOI[property_name]:
                    nlp_tuples[str(row_DOI['hash'])[:13]].append(self.extracted_tuple(row_DOI['donor'],
                                                    row_DOI['acceptor'],
                                                    donor_coreferents, 
                                                    acceptor_coreferents,
                                                    property_name,
                                                    row_DOI[property_name].replace('"', '').replace('=', '')
                                                    ))
        # Do evaluation of curated and nlp tuples
        # 4-tuple comparison

        # For each DOI in curated, compute list of 4-tuples and compute true positives and false positive
        if self.debug:
            print(f'NLP extracted: {nlp_tuples}')
            # print(f'Entry of curated data: {row}')
            print(f'Curated data tuples: {curated_tuples}\n')
        self.tuple_comparison(nlp_tuples, curated_tuples)
        # compute soft metrics in the same loop
        self.soft_metrics(nlp_tuples, curated_tuples)

    
    def compute_metrics(self, df_ground, df_nlp):
        """Take 2 dataframes as inputs and compute the relevant nlp metrics"""
        df_ground_filter = df_ground[df_ground['curated']==1]
        # doi_parsed = False
        prev_doi = df_ground_filter['DOI'][0] # Assumes 0 index entry is curated
        curated_tuples = defaultdict(list)
        for count, (index, row) in enumerate(df_ground_filter.iterrows()):
            doi = row['DOI']
            row['donor'] = str(row['donor'])
            row['acceptor'] = str(row['acceptor'])
            if doi!=prev_doi:
                self.nlp_tuple(df_nlp, prev_doi, curated_tuples)
                curated_tuples = defaultdict(list)

            # Find all curated information
            for property_name in relevant_properties:
                if row[property_name] and not (type(row[property_name]) is str and row[property_name].startswith("='") and row[property_name].endswith("'")): # Accounting for conditions where full text data is added
                    if row['hash'] == '':
                        row['hash'] = hash((doi, row['donor'], row['acceptor']))

                    if row['donor_coreferents']:
                        donor_coreferents = ast.literal_eval(row['donor_coreferents'])
                    else:
                        donor_coreferents = [row['donor']]
                    if row['acceptor_coreferents']:
                        acceptor_coreferents = ast.literal_eval(row['acceptor_coreferents'])
                    else:
                        acceptor_coreferents = [row['acceptor']]
                    if not donor_coreferents:
                        donor_coreferents = [row['donor']]
                    if not acceptor_coreferents:
                        acceptor_coreferents = [row['acceptor']]
                    # print(row['donor'], row['acceptor'])
                    if not (row['donor'].startswith("='") and row['donor'].endswith("'")) and \
                         not (row['acceptor'].startswith("='") and row['acceptor'].endswith("'")) and \
                              row['donor'] and row['acceptor']:
                        curated_tuples[str(row['hash'])[:13]].append(self.extracted_tuple(row['donor'],
                                                        row['acceptor'],
                                                        donor_coreferents,
                                                        acceptor_coreferents,
                                                        property_name,
                                                        str(row[property_name])
                                                        ))

            prev_doi = doi
        
        self.nlp_tuple(df_nlp, prev_doi, curated_tuples)
        self.compute_overall_metrics()
        print(f'4-tuple metrics: {self.performance_metrics["4-tuple"]}')
        print(f'3-tuple metrics: {self.performance_metrics["3-tuple"]}')
        print(f'2-tuple metrics: {self.performance_metrics["2-tuple"]}')
        print(f'soft metric: {self.performance_metrics["soft_metric"]}') 

    
    def run(self):
        # Load each file as a dataframe
        df_curated = pd.read_excel(self.ground_truth_file, sheet_name="Sheet1", keep_default_na=False)
        # df_curated = pd.read_csv(self.ground_truth_file, sep=";", keep_default_na=False)
        # print(df_curated)
        df_nlp = pd.read_csv(self.nlp_generated_file, keep_default_na=False)
        self.compute_metrics(df_curated, df_nlp)


if __name__ == '__main__':
    args = parser.parse_args()
    if args.use_debugpy:
        debugpy.listen(5678)
        debugpy.wait_for_client()
        debugpy.breakpoint()

    psc_nlp_eval = PSCEval(args)
    psc_nlp_eval.run()