"""Contains base classes and abstract data types which are inherited by various modules"""

from dataclasses import dataclass, field
from typing import List

GROUPED_SPAN_COLUMNS = ["text", "label", "token_start", "token_end"]

class RecordProcessor:
    def __init__(self):
        self.coreference_proximity = 2
        self.avg_abbr_length = 4
        self.material_entities = ['POLYMER', 'POLYMER_FAMILY', 'MONOMER', 'ORGANIC', 'INORGANIC']
    
    def process_sentence(self, grouped_spans, callback, sentence_limit=None):
        # Associate property values with the closest property name in the same sentence
        # Operate on grouped_entities
        # Use dot to determine sentence boundary
        # Need to include material amount existence and material_name existence in loop
        # Creates a single sentence out of grouped spans
        if grouped_spans:
            len_span = len(grouped_spans)
            i = 0
            sentence_num = 0
            while i < len_span:
                current_token = grouped_spans[i].text
                current_sentence = []
                labels = [] # Labels stored separately in order to do a quick scan of the sentence while processing it
                while (current_token != '.') and i < len_span: # Assuming that . at the end of a token can only be a tokenization error
                    # The above solution is one simple way of fixing this, the other way is to test a deeper tokenization model
                    # We could also impose the additional constraint that the second condition only happen for recognized entity types 
                    # since that is where there is likely to be parsing failure
                    current_token = grouped_spans[i].text
                    current_sentence.append(grouped_spans[i])
                    labels.append(grouped_spans[i].label) # Might remove
                    i+=1
                    if not current_token:
                        print(f'Blank current_token found = {current_token}')
                    if current_token[-1]=='.': # Assumes that a . at the end of a token must belong to a period. It could also belong to an abbreviation that we cannot disambiguate through this.
                        break
                    # if i < len_span: current_token = grouped_spans[i].text
                callback(current_sentence, labels)
                # This condition takes care of cases when consecutive periods occur in a sentence
                if current_token == '.' and i < len_span and grouped_spans[i].text == '.':
                    i+=1
                if sentence_limit and sentence_num>sentence_limit:
                    break
                sentence_num+=1
                # Process the sentence to extract propery value pairs


@dataclass
class MaterialMention:
    entity_name: str = ''
    material_class: str = ''
    role: str = ''
    polymer_type: str = ''
    normalized_material_name : str = ''
    coreferents: List = field(default_factory=lambda: [])
    components: List = field(default_factory=lambda: [])

    def return_dict(self, verbose=False):
        return {'entity_name': self.entity_name,
                'material_class': self.material_class,
                'role': self.role,
                'polymer_type': self.polymer_type,
                'normalized_material_name': self.normalized_material_name,
                'coreferents': self.coreferents,
                'components': [item.return_dict() for item in self.components if item]} # Only if components is non-empty, Set type of component as List of MaterialMention

@dataclass
class PropertyMention:
    entity_name: str = ''
    coreferents: List = field(default_factory=lambda: [])

    def return_dict(self, verbose=False):
        return {'entity_name': self.entity_name,
                'coreferents': self.coreferents,
                }


@dataclass
class EntityList(RecordProcessor):
    entity_list: List = field(default_factory=lambda: [])
    
    def delete_entries(self, index_set):
        for index in sorted(index_set, reverse=True):
            del self.entity_list[index]
    
    def return_list_dict(self, verbose=False):
        return [item.return_dict(verbose) for item in self.entity_list]


@dataclass
class PropertyValuePair:
    entity_name: str = ''
    entity_start: int = 0
    entity_end: int = 0
    property_value: str = ''
    property_value_start: int = 0
    property_value_end: int = 0
    coreferents: List = field(default_factory=lambda: [])
    material_name: str = ''
    material_amount_entity: str = ''
    material_amount: str = ''
    property_numeric_value: float = 0.0
    property_numeric_error: float = 0.0
    property_value_avg: bool = False
    property_value_descriptor: str = ''
    property_unit: str = ''
    temperature_condition: str = ''
    frequency_condition: str = ''
    
    def return_dict(self, verbose=False):
        if verbose:
            return {'entity_name': self.entity_name,
                    'entity_start': self.entity_start,
                    'entity_end': self.entity_end,
                'property_value': self.property_value,
                'property_value_start': self.property_value_start,
                'property_value_end': self.property_value_end,
                'coreferents': self.coreferents,
                'property_numeric_value': self.property_numeric_value,
                'property_numeric_error': self.property_numeric_error,
                'property_value_avg': self.property_value_avg,
                'property_value_descriptor': self.property_value_descriptor,
                'property_unit': self.property_unit,
                'temperature_condition': self.temperature_condition,
                'frequency_condition': self.frequency_condition}
        else:   
            return {'entity_name': self.entity_name,
                    'property_value': self.property_value,
                    'coreferents': self.coreferents,
                    'property_numeric_value': self.property_numeric_value,
                    'property_numeric_error': self.property_numeric_error,
                    'property_value_avg': self.property_value_avg,
                    'property_value_descriptor': self.property_value_descriptor,
                    'property_unit': self.property_unit,
                    'temperature_condition': self.temperature_condition,
                    'frequency_condition': self.frequency_condition}


@dataclass
class MaterialAmount:
    entity_name: str = ''
    material_amount: str = ''

    def return_dict(self, verbose=False):
        return {'entity_name': self.entity_name,
                'material_amount': self.material_amount}