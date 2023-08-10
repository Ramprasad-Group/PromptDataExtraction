import property_extraction, process_material_entities, material_amount_extraction, pre_processing, utils
import time
from chemdataextractor.doc import Paragraph

class RelationExtraction:
    def __init__(self, text, spans, normalization_dataset, polymer_filter=True, logger=None, verbose=False):
        """
        Calls all the submodules in order and returns the output from processing a single document
        Parameters
        ---------------
        text: string
            Plain text of document pre-processed and normalized by melda
        spans: List[NamedTuple]
            List each entry of which is a Namedtuple containing the token and its label
        verbose: boolean
            Return the token spans of property_name and property_value if True
        
        Needs normalization dataset as input and passed to ProcessMaterialEntities

        Returns
        ---------------
        output: dict
            Contains parsed version of all material property records for given document
        """
        self.text = text
        self.spans = spans
        self.normalization_dataset = normalization_dataset
        self.polymer_filter = polymer_filter
        self.logger = logger
        self.verbose = verbose

    def check_relevance(self):
        """Check if input document is relevant by checking the presence of relevant entity labels"""
        truth_value_prop = False
        truth_value_mat_entity = False
        truth_value_prop_name = False
        for item in self.spans:
            if item.label=='PROP_VALUE':
                truth_value_prop = True
            elif item.label=='PROP_NAME':
                truth_value_prop_name = True
            elif self.polymer_filter and item.label in ['POLYMER', 'MONOMER', 'POLYMER_FAMILY']:
                truth_value_mat_entity = True
            elif not self.polymer_filter and item.label in ['POLYMER', 'MONOMER', 'POLYMER_FAMILY', 'ORGANIC', 'INORGANIC']:
                truth_value_mat_entity = True
        return (truth_value_prop and truth_value_mat_entity and truth_value_prop_name)

    def link_records(self):
        """Create a set of material records from the document"""
        material_records = []
        for property_entity in self.prop_processor.property_value_pairs.entity_list:
            material_record = {}
            if property_entity.material_name:
                for material_entity in self.material_entity_processor.material_mentions.entity_list:
                    if material_entity.material_class in ['blend', 'copolymer']:
                        for component in material_entity.components:
                            if  property_entity.material_name in component.coreferents:
                                material_record['material_name'] = [component.return_dict()]
                                break

                    elif property_entity.material_name in material_entity.coreferents:
                        material_record['material_name'] = [material_entity.return_dict()]
                        break
            
                if property_entity.material_amount:
                    material_record['material_amount'] = {}
                    material_record['material_amount']['entity_name'] = property_entity.material_amount_entity
                    material_record['material_amount']['material_amount'] = property_entity.material_amount
                material_record['property_record'] = property_entity.return_dict(verbose=self.verbose) # Convert to dictionary and remove the 2 entries
            
            else:
                material_record['material_name'] = self.material_entity_processor.material_mentions.return_list_dict()
                material_record['material_amount'] = self.mat_amount_processor.material_amounts.return_list_dict()
                material_record['property_record'] = property_entity.return_dict(verbose=self.verbose)
            material_records.append(material_record)
        return material_records
    
    def process_document(self):
        """Call all individual modules and processes the input text to return a material property record"""
        if self.check_relevance():
            timer = {'pre_processing': 0, 'abbreviations': 0,  'material_entities': 0, 'property_values': 0, 'material_amount': 0, 'link_records': 0}
            begin = time.time()
            pre_processor = pre_processing.GroupTokens(self.spans, self.logger)
            self.grouped_spans, material_mentions, property_mentions = pre_processor.group_tokens()
            timer['pre_processing']=time.time()-begin
            begin = time.time()
            abbreviation_pairs = find_abbreviations(self.text)
            timer['abbreviations']=time.time()-begin
            begin = time.time()
            self.material_entity_processor = process_material_entities.ProcessMaterialEntities(self.grouped_spans, self.text, material_mentions, abbreviation_pairs, self.normalization_dataset, self.logger)
            self.material_entity_processor.run()
            timer['material_entities']=time.time()-begin
            begin = time.time()
            self.prop_processor = property_extraction.PropertyExtractor(self.grouped_spans, self.text, property_mentions, abbreviation_pairs, logger=self.logger)
            self.prop_processor.run()
            timer['property_values']=time.time()-begin
            begin = time.time()
            self.mat_amount_processor = material_amount_extraction.MaterialAmountExtractor(self.grouped_spans, self.logger)
            self.mat_amount_processor.run()
            timer['material_amount'] = time.time()-begin
            begin = time.time()
            material_records = self.link_records()
            cumulative_output_data = {'polymer_family': self.material_entity_processor.polymer_family.return_list_dict(), # Convert EntityList to list of dictionaries
                                    'monomers': self.material_entity_processor.monomers.return_list_dict(), # Convert EntityList to list of dictionaries
                                    'material_records': material_records}
            timer['link_records'] = time.time()-begin
            return cumulative_output_data, timer
        else:
            return False, None


def find_abbreviations(text):
    p = Paragraph(text)
    return [(tuple_entity[0][0], utils.token_post_processing(' '.join(tuple_entity[1]))) for tuple_entity in p.abbreviation_definitions]