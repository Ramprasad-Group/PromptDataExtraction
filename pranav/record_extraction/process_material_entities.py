"""Process all material entities identified in text"""
from base_classes import RecordProcessor, MaterialMention, EntityList
from itertools import combinations
import Levenshtein

import re


class ProcessMaterialEntities(RecordProcessor):
    def __init__(self, grouped_spans, text, material_mentions, abbreviation_pairs, normalization_dataset, logger=None):
        """
        Calls all the submodules in order process material_mentions and return a processed version of it
        parameters
        ---------------
        grouped_spans: List[NamedTuple]
            List each entry of which is a Namedtuple containing the token and its label
        material_mentions: dataclass[EntityList]
            Contains all material mentions in text
        abbreviation_pairs: List[tuple]
            Contains a list of tuples of all abbreviations found in text
        
        Returns
        ---------------
        material_mentions: List[dict]
            Contains all material mentions in text with some metadata added to it
        """
        super(ProcessMaterialEntities, self).__init__()
        self.grouped_spans = grouped_spans
        self.text = text
        self.material_mentions = material_mentions
        self.abbreviation_pairs = abbreviation_pairs
        self.normalization_dataset = normalization_dataset
        self.logger = logger
        self.solvents = ['NMP', 'DMAc', 'toluene', 'DMF', 'N-methyl-2-pyrrolidone', 'dimethylformamide', 'dimethyl formamide', 'dimethylacetamide', 'dimethyl acetamide', 'm-xylene']
        self.material_categories = ['composite', 'additive', 'plasticiz', 'quaterni', 'crosslink', 'cross-link', 'graft', 'doping', 'doped', 'dopant', 'hydrogel', 'oligomer', 'star', 'filler', 'initia', 'catalys', 'inhib', 'oxidiz', 'solven', 'ligan']
        self.copolymer_indicator = ['g-', 'g‐','co‐', 'co-','(co)', 'copoly','b-','b‐', 'star-', '-stat-','stat‐', 'block', 'ipn-', '-ran']

    def coreference_material_entities(self):
        """Combine entities by abbreviation or by case"""
        # Normalize material entities found close together. Remove the latter and add as a coreferent

        # Normalize if abbreviations found together
        delete_index = set()
        
        for abbr in self.abbreviation_pairs:
            for material_entity1, material_entity2 in combinations(self.material_mentions.entity_list, 2):
                material_index_1 = self.material_mentions.entity_list.index(material_entity1)
                material_index_2 = self.material_mentions.entity_list.index(material_entity2)
                if material_entity1.entity_name==abbr[0] and material_entity2.entity_name==abbr[1]:
                    material_entity2.coreferents.append(abbr[0])
                    delete_index.add(material_index_1)
                elif material_entity1.entity_name==abbr[1] and material_entity2.entity_name==abbr[0]:
                    material_entity1.coreferents.append(abbr[0])
                    delete_index.add(material_index_2)
        # Normalize if polymer entity found adjacent to another

        # Keep the lower case version and add coreferents
        self.material_mentions.delete_entries(delete_index)
        delete_index = set()

        for material_entity1, material_entity2 in combinations(self.material_mentions.entity_list, 2):
            if material_entity2.entity_name.lower() == material_entity1.entity_name or \
                (len(material_entity2.entity_name)>1 and material_entity2.entity_name[0].lower()+material_entity2.entity_name[1:] == material_entity1.entity_name):
                material_entity1.coreferents.extend(material_entity2.coreferents)
                delete_index.add(self.material_mentions.entity_list.index(material_entity2))
            elif material_entity2.entity_name == material_entity1.entity_name.lower() or \
                (len(material_entity1.entity_name)>1 and material_entity1.entity_name[0].lower()+material_entity1.entity_name[1:] == material_entity2.entity_name):
                material_entity2.coreferents.extend(material_entity1.coreferents)
                delete_index.add(self.material_mentions.entity_list.index(material_entity1))
        
        self.material_mentions.delete_entries(delete_index)
        delete_index = set()
        for material_entity1, material_entity2 in combinations(self.material_mentions.entity_list, 2):
            material_index_1 = self.material_mentions.entity_list.index(material_entity1)
            material_index_2 = self.material_mentions.entity_list.index(material_entity2)
            if material_entity2.entity_name in material_entity1.entity_name and \
               material_entity1.polymer_type != 'copolymer' and \
               not self.coreference_exception(material_entity2.entity_name, material_entity1.entity_name) and \
               material_entity2.material_class==material_entity1.material_class and len(material_entity2.entity_name)>=self.avg_abbr_length:
                material_entity2.coreferents.extend(material_entity1.coreferents)
                delete_index.add(material_index_1)
            elif material_entity1.entity_name in material_entity2.entity_name and \
                 material_entity2.polymer_type != 'copolymer' and \
                 not self.coreference_exception(material_entity2.entity_name, material_entity1.entity_name) and \
                 material_entity2.material_class==material_entity1.material_class and len(material_entity2.entity_name)>=self.avg_abbr_length: # last condition ensures same entity doesn't go into multiple records
                material_entity1.coreferents.extend(material_entity2.coreferents)
                delete_index.add(material_index_2)
        
        # Find abbreviations not detected by ChemDataExtractor by looking for adjacent tokens with same label with abbreviation
        # Upper bounded in length or preceded by a left bracket token
        self.material_mentions.delete_entries(delete_index)
        delete_index = set()
        span_length = len(self.grouped_spans)
        i=0
        while i < span_length:
            current_label = self.grouped_spans[i].label
            if current_label in self.material_entities:
                current_entity_name = self.grouped_spans[i].text
                for p in range(self.coreference_proximity):
                    i+=1
                    if i<span_length and self.grouped_spans[i].text in ['/', ':', 'into']:
                        i+=self.coreference_proximity-p
                        break
                    # We assume the an abbreviation follows the material entity and typically has a bounded length or if not that the previous token was a bracket
                    # The second condition might be needed if the abbreviation refers to some long copolymer
                    if i<span_length and self.grouped_spans[i].label == current_label and (len(self.grouped_spans[i].text)<=self.avg_abbr_length or self.grouped_spans[i-1].text=='('):
                        coreferenced_entity = ''
                        for k, entity in enumerate(self.material_mentions.entity_list):
                            added_in_loop=False
                            if entity.entity_name == self.grouped_spans[i].text and not self.coreference_exception(entity.entity_name, current_entity_name):
                                coreferenced_entity = entity
                                delete_index.add(k)
                                added_in_loop=True
                                break

                        for l, entity in enumerate(self.material_mentions.entity_list):
                            if entity.entity_name == current_entity_name and coreferenced_entity and coreferenced_entity.entity_name not in entity.coreferents:
                                entity.coreferents.extend(coreferenced_entity.coreferents)
                                break
                        else:
                            if added_in_loop: delete_index.remove(k)
                i-=self.coreference_proximity
            i+=1 # Do a look ahead and then skip a token and then move forward
            
        # Delete here if using case normalization as Levenshtein normalization can be equivalent to case normalization

        self.material_mentions.delete_entries(delete_index)
        delete_index = set()
        # Normalize based on Levenshtein distance, compare based on length of number of coreferents
        for material_entity1, material_entity2 in combinations(self.material_mentions.entity_list, 2):
            if material_entity2.material_class!=material_entity1.material_class:
                continue
            if len(material_entity1.coreferents) >= len(material_entity2.coreferents):
                mat_to_compare = material_entity1
                mat_other = material_entity2
            else:
                mat_to_compare = material_entity1
                mat_other = material_entity2
            for coreferent1 in mat_to_compare.coreferents:
                if Levenshtein.distance(coreferent1, mat_other.entity_name)<=1 and not self.coreference_exception(coreferent1, mat_other.entity_name): # Exceptions for cases where similarly written materials get normalized
                    mat_to_compare.coreferents.extend(material_entity2.coreferents)
                    delete_index.add(self.material_mentions.entity_list.index(material_entity2))
                    break

        # Check other entities in material mentions, if there is a repetition, delete it
        self.material_mentions.delete_entries(delete_index)

    def coreference_exception(self, mat1, mat2):
        reg_exp1 = f'{mat1}[,]? and {mat2}'
        reg_exp2 = f'{mat2}[,]? and {mat1}'
        try:
            return (f'{mat1}, {mat2}' in self.text) or \
                   (f'{mat2}, {mat1}' in self.text) or \
                   (re.findall(reg_exp1, self.text)) or \
                   (re.findall(reg_exp2, self.text)) or \
                   (f'{mat1}/{mat2}' in self.text) or \
                   (f'{mat2}/{mat1}' in self.text) or \
                   (f'{mat1}:{mat2}' in self.text) or \
                   (f'{mat2}:{mat1}' in self.text)
        except:
            return False
            # This handles cases where there are unbalanced paranthesis in one or the other material entity
    
    def detect_material_role(self, sentence, labels):
        # Check for materials which have singleton roles like crosslinkers and grafts
        # covered_tokens = []
        for i, span in enumerate(sentence):
                if any([category in span.text for category in self.material_categories]):
                    j=0
                    while i+j<len(sentence) or i-j>=0:
                        if i+j<len(sentence) and sentence[i+j].label in ['ORGANIC', 'INORGANIC', 'POLYMER']:
                            for material_entity in self.material_mentions.entity_list:
                                if sentence[i+j].text in material_entity.coreferents:
                                    material_entity.role = span.text
                            break
                        elif i-j>=0 and sentence[i-j].label in ['ORGANIC', 'INORGANIC', 'POLYMER']:
                            for material_entity in self.material_mentions.entity_list:
                                if sentence[i-j].text in material_entity.coreferents:
                                    material_entity.role = span.text
                            break
                        j+=1

    def detect_polymer_type(self):
        """Based on cues in the polymer name, detect the type of the polymer"""
        for material_entity in self.material_mentions.entity_list:
            if material_entity.material_class == 'POLYMER':
                material_name = material_entity.entity_name
                if 'star' in material_name:
                    material_entity.polymer_type='star_polymer'
                elif any([subword in material_name for subword in self.copolymer_indicator]) or material_name.count('poly')>1 or ('-' in material_name and material_name.upper()==material_name):
                    material_entity.polymer_type='copolymer'
                else:
                    material_entity.polymer_type='homopolymer'

    def normalize_record(self):
        """After material record is extracted, normalize the name of the obtained polymers"""
        # Might extend this to name of extracted property names and other organic / inorganic entities
        for material_entity in self.material_mentions.entity_list:
            if material_entity.material_class=='POLYMER' and material_entity.polymer_type=='homopolymer':
                material_name = material_entity.entity_name
                for common_polymer_name, values in self.normalization_dataset.items():
                    if any([coreferent in values["coreferents"] or coreferent[0].upper()+coreferent[1:] in values["coreferents"] or coreferent[0].lower()+coreferent[1:] in values["coreferents"] or coreferent.lower() in values['coreferents'] or coreferent.upper() in values['coreferents'] for coreferent in material_entity.coreferents]):
                        material_entity.normalized_material_name = common_polymer_name # Use IUPAC_structure based name for normalization if possible
                        break
            
    def detect_blend_constituents(self, sentence, labels):
        """Check if the text has keywords that would tell us whether a blend or composite is being referred to"""
        blend_terms = ['blend']
        # Check for entities in the vicinity of the word blend
        blend_dict = None
        for i, span in enumerate(sentence):
            if any([entity in span.text for entity in blend_terms]):
                blend_dict = MaterialMention()
                # Need to initialized blend_dict from base class to avoid having to initialize all assumed variables
                blend_dict.material_class = 'blend'
                delete_index = set()
                j=1
                # Constraint of role not being in material_mention is removed
                while i+j<len(sentence) or i-j>=0:
                    if i+j<len(sentence) and sentence[i+j].label in ['POLYMER', 'ORGANIC']:
                        for k, material_entity in enumerate(self.material_mentions.entity_list):
                            if sentence[i+j].text in material_entity.coreferents and k not in delete_index:
                                blend_dict.components.append(material_entity)
                                delete_index.add(k)
                                break
                    elif i-j>=0 and sentence[i-j].label in ['POLYMER', 'ORGANIC']:
                        for k, material_entity in enumerate(self.material_mentions.entity_list):
                            if sentence[i-j].text in material_entity.coreferents and k not in delete_index:
                                blend_dict.components.append(material_entity)
                                delete_index.add(k)
                                break
                    j+=1
                
                if blend_dict and len(blend_dict.components)>1:
                    self.material_mentions.entity_list.append(blend_dict)
                    self.material_mentions.delete_entries(delete_index)

    def detect_copolymer_constituents(self, sentence, labels):
        """Check if the text has keywords that would tell us whether a blend or composite is being referred to"""
        copolymer_terms = ['copolymer']
        copolymer_dict = None
        for i, span in enumerate(sentence):
            if any([entity in span.text for entity in copolymer_terms]):
                copolymer_dict = MaterialMention()
                copolymer_dict.material_class = 'copolymer'
                delete_index = set()
                j=i+1
                while j<len(sentence):
                    if sentence[j].label in ['POLYMER', 'ORGANIC']:
                        for k, material_entity in enumerate(self.material_mentions.entity_list):
                            if sentence[j].text in material_entity.coreferents and k not in delete_index:
                                copolymer_dict.components.append(material_entity)
                                delete_index.add(k)
                                break
                    j+=1
                    
                if copolymer_dict and len(copolymer_dict.components)>1:
                    self.material_mentions.entity_list.append(copolymer_dict)
                    self.material_mentions.delete_entries(delete_index)

    def final_material_processing(self):
        self.monomers = EntityList()
        self.polymer_family = EntityList()
        delete_index = set()
        for k, material_entity in enumerate(self.material_mentions.entity_list):
            # Remove monomers and separate into a separate list
            if material_entity.material_class == 'MONOMER':
                self.monomers.entity_list.append(material_entity)
                delete_index.add(k)
            # Store polymer family in a separate list
            elif material_entity.material_class == 'POLYMER_FAMILY':
                self.polymer_family.entity_list.append(material_entity)
            # Remove solvent entries
            if any([solvent in material_entity.coreferents for solvent in self.solvents]):
                # self.solvents.append(material_entity)
                delete_index.add(k)
        
        # Delete monomers and solvents
        self.material_mentions.delete_entries(delete_index)

    def run(self):
        """Returns material_mentions after final processing"""
        self.detect_polymer_type()
        self.coreference_material_entities()
        self.process_sentence(self.grouped_spans, self.detect_material_role)
        # Normalize polymer named entities before they get clubbed
        # Get normalization_dataset from outside
        self.normalize_record()
        self.process_sentence(self.grouped_spans, self.detect_copolymer_constituents, sentence_limit=2)
        self.process_sentence(self.grouped_spans, self.detect_blend_constituents, sentence_limit=2)
        self.final_material_processing()