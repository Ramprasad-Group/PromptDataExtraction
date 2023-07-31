""" Extract property value pairs and post process them to obtain a single property record """
from record_extraction.base_classes import EntityList, PropertyValuePair, RecordProcessor
from collections import Counter, deque
import itertools
import re
import json


class PropertyExtractor(RecordProcessor):
    def __init__(self, grouped_spans=None, text=None, property_mentions=None, abbreviation_pairs=None, print_spans=False, logger=None):
        """
        Calls all the submodules in order to process grouped_spans and return a list of property_value_pairs
        ---------------
        grouped_spans: List[NamedTuple]
            List each entry of which is a Namedtuple containing the token and its label
        abbreviation_pairs: List[tuple]
            Contains a list of tuples of all abbreviations found in text

        Returns
        ---------------
        property_value_pairs: List[dict]
            Contains all property value pairs in text with some metadata added to it
        """
        super(PropertyExtractor, self).__init__()
        self.grouped_spans = grouped_spans
        self.text = text
        self.print_spans = print_spans
        self.abbreviation_pairs = abbreviation_pairs
        self.logger = logger
        self.RE_NUMBER = r'[+-]?\d+[.]?\d*(?:\s?±\s?\d+[.]?\d*)?(?:x10\^{[-]?\d*})?'
        self.RE_EXP = r'10\^{[-]?\d*}'
        self.RE_EXP_UNIT = r'([a-zA-Z]+\^{[-]?\d*})'
        self.property_value_descriptor_list = ['<', '>', '~', '=', 'and', '≈', 'to', '-']
        self.property_mentions = property_mentions
        self.property_value_pairs = EntityList()
        property_metadata_file = '' # Metadata file that contains relevant information about each property such as units and coreferents
        with open(property_metadata_file, 'r', encoding='utf-8') as fi:
            self.prop_records_metadata = json.load(fi)
        self.convert_fraction_to_percentage = [value['property_list'] for key, value in self.prop_records_metadata.items() if value['unit_list'][0]=='%']
    
    def property_extraction(self, sentence, labels):
        # Can use the code/logic for processing single sentences that we tried last year
        # Examine single sentence analysis code/dependency parsing from last year
        # Might also feed in all sentences to this code so that information from adjacent sentences can be utilized if necessary
        category_counts = Counter(labels)
        # Sentence may have more than 2 values reported and respectively might occur more than once 
        # The below condition takes care of cases like 'polymer has Tg and Tm of 23 deg. C and 50 deg. C respectively'
        if category_counts.get('PROP_VALUE', 0)>=2 and category_counts.get('PROP_NAME', 0)>=2 and any([span.text=='respectively' for span in sentence]):
            # prop_value_indices = []
            # prop_name_indices = []
            # first_property = False
            # The below logic is very specific to when respectively occurs in a sentence
            for i, span in enumerate(sentence):
                if self.print_spans: print(span)
                if span.text == 'respectively':
                    j=i-1
                    prop_value_queue = deque()
                    while j>=0:
                        if sentence[j].label=='PROP_VALUE':
                            prop_value_queue.append(sentence[j])
                        elif sentence[j].label=='PROP_NAME':
                            if self.property_value_pairs.entity_list and sentence[j].text not in self.property_value_pairs.entity_list[-1].coreferents and prop_value_queue:
                                prop_value = prop_value_queue.popleft()
                                self.property_value_pairs.entity_list.append(PropertyValuePair(entity_name=sentence[j].text, entity_start=sentence[j].token_start, entity_end=sentence[j].token_end,
                                                                                               property_value=prop_value.text, property_value_start=prop_value.token_start, property_value_end=prop_value.token_end,
                                                                                               coreferents=self.find_property_coreferents(sentence[j].text)))
                        j-=1
                    if not prop_value_queue and self.logger:
                        self.logger.warning(f'For {" ".join([sent.text for sent in sentence])} the queue is non-empty')
        else:
            for i, span in enumerate(sentence):
                if self.print_spans: print(span)
                if span.label == 'PROP_VALUE':
                    j=i-1
                    while j>=0:
                        if sentence[j].label=='PROP_NAME':
                            property_dict = PropertyValuePair(entity_name=sentence[j].text, entity_start=sentence[j].token_start, entity_end=sentence[j].token_end,
                                                              property_value=span.text, property_value_start=span.token_start, property_value_end=span.token_end,
                                                              coreferents=self.find_property_coreferents(sentence[j].text))
                                             # No default material name and amount included to be consistent with the previous case

                            material_entities = ['ORGANIC', 'POLYMER', 'INORGANIC', 'POLYMER_FAMILY', 'MONOMER']
                            increment = 1
                            while j+increment<len(sentence) or j-increment>=0:
                                if j-increment>0 and sentence[j-increment].label == 'MATERIAL_AMOUNT':
                                    if sentence[j-increment+1].label in material_entities:
                                        property_dict.material_amount = sentence[j-increment].text
                                        property_dict.material_amount_entity = sentence[j-increment+1].text
                                    elif sentence[j-increment-1].label in material_entities:
                                        property_dict.material_amount = sentence[j-increment].text
                                        property_dict.material_amount_entity = sentence[j-increment-1].text

                                    break
                                if j+increment<len(sentence) and sentence[j+increment].label == 'MATERIAL_AMOUNT':
                                    if sentence[j+increment+1].label in material_entities:
                                        property_dict.material_amount = sentence[j+increment].text
                                        property_dict.material_amount_entity = sentence[j+increment+1].text
                                    elif sentence[j+increment-1].label in material_entities:
                                        property_dict.material_amount = sentence[j+increment].text
                                        property_dict.material_amount_entity = sentence[j+increment-1].text
                                    break
                                increment+=1

                            increment = 1
                            while j+increment<len(sentence) or j-increment>=0:
                                if j-increment>0 and sentence[j-increment].label in material_entities and sentence[j-increment].text!=property_dict.material_amount_entity:
                                    property_dict.material_name = sentence[j-increment].text
                                    break
                                if j+increment<len(sentence) and sentence[j+increment].label in material_entities and sentence[j+increment].text!=property_dict.material_amount_entity:
                                    property_dict.material_name = sentence[j+increment].text
                                    break
                                increment += 1
                            self.property_value_pairs.entity_list.append(property_dict)
                            break
                        j-=1
                # Put in logging code to report property names that did not have an adjacent property value

                # iterate backwards till you hit a prop_name
        sentence_str = (' '.join([span.text for span in sentence]))#.replace('° C', '°C')
        # Extraction of temperature conditions only, can generalize this code block for other conditions
        temperature_list = re.findall('\d+ ° C', sentence_str) # Only considering one unit for temperature
        for temperature_value in temperature_list:
            # Using exact equal might cause issues. There might be temperature ranges reported for conditions we might miss
            if not any([temperature_value in property_dict.property_value for property_dict in self.property_value_pairs.entity_list]):
                for property_dict in self.property_value_pairs.entity_list:
                    if property_dict.entity_name in sentence_str:
                        property_dict.temperature_condition=temperature_value
                break
        # Can repeat this for frequency for dielectric constant
        frequency_list = re.findall('\d+ \w?Hz', sentence_str)
        frequency_list+= re.findall('10\^{\d\s?} Hz', sentence_str)
        dielectric_properties = ['dielectric loss', 'dielectric constant', 'relative permittivity']
        for frequency_value in frequency_list:
            # Using exact equal might cause issues. There might be temperature ranges reported for conditions we might miss
            if not any([property_dict.property_value==frequency_value for property_dict in self.property_value_pairs.entity_list]):
                for property_dict in self.property_value_pairs.entity_list:
                    if property_dict.entity_name in dielectric_properties and property_dict.entity_name in sentence_str:
                        property_dict.frequency_condition=frequency_value.replace(' }', '}')
                break


    def find_property_coreferents(self, property_name):
        """Find the coreferents of a property entity given the entity"""
        for i, property_entity in enumerate(self.property_mentions.entity_list):
            if property_name in property_entity.coreferents:
                return property_entity.coreferents
        
        return []
    
    def coreference_property_names(self):
        """Combine entities by abbreviation or by case"""
        # Might normalize property values as well later on if required
        # Normalize material entities found close together. Remove the latter and add as a coreferent

        # Normalize if abbreviations found together
        for i, property_entity in enumerate(self.property_mentions.entity_list):
            property_name = property_entity.entity_name
            for abbr in self.abbreviation_pairs:
                if abbr[1] == property_name:
                    property_entity.coreferents.append(abbr[0])
                elif abbr[0] == property_name:
                    property_entity.coreferents.append(abbr[1])
        
        # Find abbreviations not detected by ChemDataExtractor by looking for adjacent tokens with same label with abbreviation
        # Upper bounded in length or preceded by a left bracket token
        i = 0
        span_length = len(self.grouped_spans)

        while i < span_length:
            current_label = self.grouped_spans[i].label
            if current_label== 'PROP_NAME':
                property_name = self.grouped_spans[i].text
                coreference_proximity = 2
                for j in range(coreference_proximity):
                    i+=1
                    # We assume the an abbreviation follows the property name and typically has a bounded length or if not that the previous token was a bracket
                    # The second condition might be needed if the abbreviation refers to some long copolymer
                    if i<span_length and self.grouped_spans[i].label == current_label and (len(self.grouped_spans[i].text)<=self.avg_abbr_length or self.grouped_spans[i-1].text=='('):
                        for k, property_entity in enumerate(self.property_mentions.entity_list):
                            if property_entity.entity_name.lower() == property_name.lower() and property_name not in property_entity.coreferents:
                                property_entity.coreferents.append(property_name)
                            # Exceptions to the below clause are possible open-circuit voltage and PCE
                            elif property_entity.entity_name.lower() == property_name.lower() and self.grouped_spans[i].text not in property_entity.coreferents and not self.coreference_exception(property_name, self.grouped_spans[i].text):
                                property_entity.coreferents.append(self.grouped_spans[i].text)
                            
            i+=1
        delete_index = []
        for prop_entity1, prop_entity2 in itertools.combinations(self.property_mentions.entity_list, 2):
            prop_index_1 = self.property_mentions.entity_list.index(prop_entity1)
            prop_index_2 = self.property_mentions.entity_list.index(prop_entity2)
            if prop_entity1.entity_name in prop_entity2.coreferents or prop_entity2.entity_name in prop_entity1.coreferents:
                if len(prop_entity1.coreferents) > len(prop_entity2.coreferents):
                    delete_index.append(prop_index_2)
                else:
                    delete_index.append(prop_index_1)
        
        self.property_mentions.delete_entries(delete_index)
    
    def coreference_exception(self, prop1, prop2):
        reg_exp1 = f'{prop1}[,]? and {prop2}'
        reg_exp2 = f'{prop2}[,]? and {prop1}'
        try:
            return (f'{prop1}, {prop2}' in self.text) or \
                   (f'{prop2}, {prop1}' in self.text) or \
                   (re.findall(reg_exp1, self.text)) or \
                   (re.findall(reg_exp2, self.text))
                   
        except:
            return False

         
    def property_value_postprocessing(self):
        for property_entity in self.property_value_pairs.entity_list:
            self.single_property_entity_postprocessing(property_entity)
        
        # This block takes care of cases where 2 property values are mentioned consecutively with a single property name and units are mentioned for the second but not the first property value
        for i, property_entity in enumerate(self.property_value_pairs.entity_list):
            if property_entity.property_unit=='':
                if i<len(self.property_value_pairs.entity_list)-1 and property_entity.entity_name==self.property_value_pairs.entity_list[i+1].entity_name \
                                                                  and self.property_value_pairs.entity_list[i+1].property_unit != '':
                    property_entity.property_unit = self.property_value_pairs.entity_list[i+1].property_unit


    def single_property_entity_postprocessing(self, property_entity):
        """Process a single property_entity. Split out in this manner so that it can be exposed to other classes"""
        property_value = property_entity.property_value
        # Property value needs some pre-processing to replace exponents in units that could match a number
        # Might also have to split on - to capture the negative sign
        property_value = re.sub(r'(\d)-(\d)', '\\1 - \\2', property_value)
        property_value = re.sub(r'(\d) (\d)', '\\1\\2', property_value)
        property_value = re.sub(r'(\d) x (\d)', '\\1x\\2', property_value)
        units_to_replace = re.findall(self.RE_EXP_UNIT, property_value)
        units_dict = dict()
        for i, unit in enumerate(units_to_replace):
            units_dict[f'AAA{chr(i+64)}'] = unit
            property_value = property_value.replace(unit, f'AAA{chr(i+64)}')

        numeric_values = re.findall(self.RE_NUMBER, property_value)
        # print(numeric_values)
        for value in numeric_values:
            if '±' in value:
                values = value.split('±')
                property_entity.property_numeric_value = self.process_numeric_values(values[0].strip())
                property_entity.property_numeric_error = self.process_numeric_values(values[-1].strip())
                break
        else:
            if numeric_values:
                property_entity.property_numeric_value = sum([self.process_numeric_values(num) for num in numeric_values])/(len(numeric_values))
            else:
                property_entity.property_numeric_value = ''
        
        # Deal with cases like 10^{7} not covered by our regular expressions.. Hack solution, find a way to integrate this with our regular expression
        if '10^{' in property_value and not any(['10^{' in value for value in numeric_values]):
            numeric_values = re.findall(self.RE_EXP, property_value)
            if numeric_values:
                property_entity.property_numeric_value = sum([self.process_numeric_values(num) for num in numeric_values])/(len(numeric_values))
            else:
                property_entity.property_numeric_value = ''

        
        property_entity.numeric_value_avg = len(numeric_values)>1
        leftover_str = property_value
        for value in numeric_values:
            leftover_str = leftover_str.replace(value, '')
        # Replace units back
        property_entity.property_value_descriptor = ''

        for str_item in self.property_value_descriptor_list:
            if str_item in leftover_str:
                property_entity.property_value_descriptor = property_entity.property_value_descriptor+str_item
                leftover_str = leftover_str.replace(str_item, '')

        for key, value in units_dict.items():
            leftover_str = leftover_str.replace(key, value)

        property_entity.property_unit = leftover_str.strip()
        self.unit_conversion(property_entity)
    
    def process_numeric_values(self, value):
        if '^{' in value and '}' in value and 'x' in value:
            mantissa, exponent = value.split('x')[0].strip(), value.split('x')[1].strip().replace('10^{', '').replace('}', '')
            numeric_value = float(mantissa)*10**(float(exponent))
            return numeric_value
        elif '^{' in value and '}' in value and 'x' not in value:
            exponent = value.strip().replace('10^{', '').replace('}', '')
            numeric_value = 10**(float(exponent))
            return numeric_value
        else:
            return float(value)

    def unit_conversion(self, property_entity):
        """Convert units for a predefined list of entries into a predefined standard"""
        # Add more units to this
        if property_entity.property_unit and property_entity.property_unit[-1] in ['.']:
            property_entity.property_unit = property_entity.property_unit[:-1].strip()

        if property_entity.property_numeric_value:
            if property_entity.property_unit == 'K':
                property_entity.property_numeric_value -= 273
                property_entity.property_unit = '° C'
            elif property_entity.property_unit in ['kPa', 'KPa']:
                property_entity.property_numeric_value /= 1000
                property_entity.property_numeric_error /= 1000
                property_entity.property_unit = 'MPa'
            elif property_entity.property_unit == 'GPa':
                property_entity.property_numeric_value *= 1000
                property_entity.property_numeric_error *= 1000
                property_entity.property_unit = 'MPa'
            elif property_entity.property_unit in ['mS/cm', 'mS cm^{-1}', 'mS / cm', 'mS*cm^{-1}']:
                property_entity.property_numeric_value /= 1000
                property_entity.property_numeric_error /= 1000
                property_entity.property_unit = 'S/cm'
            elif property_entity.property_unit in ['S/m', 'S m^{-1}']:
                property_entity.property_numeric_value /= 100
                property_entity.property_numeric_error /= 100
                property_entity.property_unit = 'S cm^{-1}'
            elif property_entity.property_unit in ['mV']:
                property_entity.property_numeric_value /= 1000
                property_entity.property_numeric_error /= 1000
                property_entity.property_unit = 'V'
            elif property_entity.property_unit in ['kg/mol', 'kg mol^{-1}','KDa', 'kDa']:
                property_entity.property_numeric_value *= 1000
                property_entity.property_numeric_error *= 1000 
                property_entity.property_unit = 'g/mol'
            elif property_entity.property_unit in ['mW/mK', 'mW m^{-1} K^{-1}', 'mW/m*K', 'mW*m^{-1}*K^{-1}', 'mW/(m*K)', 'mW/m K', 'mW/m * K']:
                property_entity.property_numeric_value /= 1000
                property_entity.property_numeric_error /= 1000
                property_entity.property_unit = 'W m^{-1} K^{-1}'
            elif property_entity.property_unit in ['kW kg^{-1}', 'kW/kg', 'kW*kg^{-1}', 'W g^{-1}']:
                property_entity.property_numeric_value *= 1000
                property_entity.property_numeric_error *= 1000
                property_entity.property_unit = 'W kg^{-1}'
            elif property_entity.property_unit in ['kW g^{-1}']:
                property_entity.property_numeric_value *= 1000000
                property_entity.property_numeric_error *= 1000000
                property_entity.property_unit = 'W kg^{-1}'
            elif property_entity.property_unit in ['mA g^{-1}', 'mA/g', 'mA*g^{-1}', 'mAg^{-1}']:
                property_entity.property_numeric_value /= 1000
                property_entity.property_numeric_error /= 1000
                property_entity.property_unit = 'A g^{-1}'
            elif property_entity.property_unit in ['μA cm^{-2}', 'μA/cm^{2}', 'μA*cm^{-2}', 'uA cm^{-2}']:
                property_entity.property_numeric_value /= 1000
                property_entity.property_numeric_error /= 1000
                property_entity.property_unit = 'mA cm^{-2}'
            elif property_entity.property_unit in ['mA m^{-2}', 'mA/m^{2}']:
                property_entity.property_numeric_value /= 10000
                property_entity.property_numeric_error /= 10000
                property_entity.property_unit = 'mA cm^{-2}'
            elif property_entity.property_unit in ['A/m^{2}', 'A m^{-2}']:
                property_entity.property_numeric_value /= 10
                property_entity.property_numeric_error /= 10
                property_entity.property_unit = 'mA cm^{-2}'
            elif property_entity.property_unit in ['nA/cm^{2}', 'nA cm^{-2}']:
                property_entity.property_numeric_value /= 1000000
                property_entity.property_numeric_error /= 1000000
                property_entity.property_unit = 'mA cm^{-2}'
            elif property_entity.property_unit in ['A*cm^{-2}', 'A cm^{-2}']:
                property_entity.property_numeric_value *= 1000
                property_entity.property_numeric_error *= 1000
                property_entity.property_unit = 'mA cm^{-2}'
            elif property_entity.property_unit in ['mW m^{-2}', 'mW/m^{2}', 'mW*m^{-2}', 'mWm^{-2}']:
                property_entity.property_numeric_value /= 10000
                property_entity.property_numeric_error /= 10000
                property_entity.property_unit = 'mW cm^{-2}'
            elif property_entity.property_unit in ['W cm^{-2}', 'W/cm^{2}', 'Wcm^{-2}']:
                property_entity.property_numeric_value *= 1000
                property_entity.property_numeric_error *= 1000
                property_entity.property_unit = 'mW cm^{-2}'
            elif property_entity.property_unit in ['μW cm^{-2}', 'μW/cm^{2}', 'uW cm^{-2}', 'μW*cm^{-2}', 'μWcm^{-2}', 'uW/cm^{2}', 'μ W/cm^{2}']:
                property_entity.property_numeric_value /= 1000
                property_entity.property_numeric_error /= 1000
                property_entity.property_unit = 'mW cm^{-2}'
            elif property_entity.property_unit in ['W/m^{2}', 'W m^{-2}', 'μW.mm^{-2}', 'μW mm^{-2}']:
                property_entity.property_numeric_value /= 10
                property_entity.property_numeric_error /= 10
                property_entity.property_unit = 'mW cm^{-2}'
            elif property_entity.property_unit in ['mW/mm^{2}']:
                property_entity.property_numeric_value *= 100
                property_entity.property_numeric_error *= 100
                property_entity.property_unit = 'mW cm^{-2}'
            elif property_entity.property_unit in ['kW/cm^{2}']:
                property_entity.property_numeric_value *= 1000000
                property_entity.property_numeric_error *= 1000000
                property_entity.property_unit = 'mW cm^{-2}'
            elif property_entity.property_unit in ['cm^{3}(STP) cm/cm^{2} s cmHg', 'cm^{3}(STP) cm/(cm^{2} s cmHg)']:
                property_entity.property_numeric_value *= 10**10
                property_entity.property_numeric_error *= 10**10
                property_entity.property_unit = 'Barrer'
            elif property_entity.property_unit in ['mol m m^{-2} s^{-1} Pa^{-1}( barrer)', 'mol m m^{-2} s^{-1} Pa^{-1}']:
                property_entity.property_numeric_value *= float(10**16)/3.35
                property_entity.property_numeric_error *= float(10**16)/3.35
                property_entity.property_unit = 'Barrer'
            elif property_entity.property_unit in ['μg g^{-1}', 'μg/g']:
                property_entity.property_numeric_value /= 1000
                property_entity.property_numeric_error /= 1000
                property_entity.property_unit = 'mg/g'
            elif property_entity.property_unit in ['g g^{-1}', 'g/g', 'g/ g']:
                property_entity.property_numeric_value *= 1000
                property_entity.property_numeric_error *= 1000
                property_entity.property_unit = 'mg/g'
            elif property_entity.property_unit in ['kg m^{-3}', 'kg/m^{3}']:
                property_entity.property_numeric_value /= 1000
                property_entity.property_numeric_error /= 1000
                property_entity.property_unit = 'g/cm^{3}'
            elif property_entity.property_unit in ['μM', 'uM', 'μmol L^{-1}']:
                property_entity.property_numeric_value /= 10**6
                property_entity.property_numeric_error /= 10**6
                property_entity.property_unit = 'M'
            elif property_entity.property_unit in ['nM', 'nmol L^{-1}']:
                property_entity.property_numeric_value /= 10**9
                property_entity.property_numeric_error /= 10**9
                property_entity.property_unit = 'M'
            elif property_entity.property_unit in ['pM',]:
                property_entity.property_numeric_value /= 10**15
                property_entity.property_numeric_error /= 10**15
                property_entity.property_unit = 'M'
            elif property_entity.property_unit in ['mM',]:
                property_entity.property_numeric_value /= 10**3
                property_entity.property_numeric_error /= 10**3
                property_entity.property_unit = 'M'
            elif property_entity.property_unit in ['mg/cm^{3}', 'mg cm^{-3}', 'g/dm^{3}', 'g/L', 'mg/cc', 'kg*m^{-3}', 'mg*cm^{-3}', 'kgm^{-3}']:
                property_entity.property_numeric_value /= 10**3
                property_entity.property_numeric_error /= 10**3
                property_entity.property_unit = 'g/cm^{3}'
            elif property_entity.property_unit in ['kcal/mol', 'kcal mol^{-1}', 'kcal/mole']:
                property_entity.property_numeric_value *= 4.18
                property_entity.property_numeric_error *= 4.18
                property_entity.property_unit = 'kJ/mol'
            elif property_entity.property_unit in ['μA μM^{-1} cm^{-2}', 'μA cm^{-2} μM^{-1}', 'uA uM^{-1} cm^{-2}', 'mA mM^{-1} cm^{-2}', 'mA cm^{-2} mM^{-1}', 'μAμM^{-1}cm^{-2}']:
                property_entity.property_numeric_value *= 1000
                property_entity.property_numeric_error *= 1000
                property_entity.property_unit = 'μA mM^{-1} cm^{-2}'
            elif property_entity.property_unit in ['nA mM^{-1} cm^{-2}']:
                property_entity.property_numeric_value /= 1000
                property_entity.property_numeric_error /= 1000
                property_entity.property_unit = 'μA mM^{-1} cm^{-2}'
            elif property_entity.property_unit in ['Pa*s', 'Pa.s', 'Pa s', 'Pas', 'Pa s^{-1}']:
                property_entity.property_numeric_value *= 1000
                property_entity.property_numeric_error *= 1000
                property_entity.property_unit = 'mPa s'
            elif property_entity.property_unit in ['kΩ/sq', 'kΩ/ #', 'kΩ sq^{-1}', 'kΩ/square']:
                property_entity.property_numeric_value *= 1000
                property_entity.property_numeric_error *= 1000
                property_entity.property_unit = 'Ω/sq'
            elif property_entity.property_unit in ['MV/cm']:
                property_entity.property_numeric_value *= 1000
                property_entity.property_numeric_error *= 1000
                property_entity.property_unit = 'kV/mm'
            elif property_entity.property_unit in ['kV/cm']:
                property_entity.property_numeric_value /= 10
                property_entity.property_numeric_error /= 10
                property_entity.property_unit = 'kV/mm'
            elif property_entity.property_unit in ['Pa']:
                property_entity.property_numeric_value /= 1000000
                property_entity.property_numeric_error /= 1000000
                property_entity.property_unit = 'MPa'
            elif property_entity.property_unit in ['μΩ cm', 'μΩ*cm', 'μΩcm']:
                property_entity.property_numeric_value /= 1000000
                property_entity.property_numeric_error /= 1000000
                property_entity.property_unit = 'Ω cm'
            elif property_entity.property_unit in ['Ω m', 'Ωm']:
                property_entity.property_numeric_value *= 100
                property_entity.property_numeric_error *= 100
                property_entity.property_unit = 'Ω cm'
            elif property_entity.property_unit in ['L m^{-2} h^{-1} MPa^{-1}', 'L*m^{-2}*h^{-1}*MPa^{-1}']:
                property_entity.property_numeric_value *= 100
                property_entity.property_numeric_error *= 100
                property_entity.property_unit = 'Ω cm'
            elif property_entity.property_unit in ['μW cm^{-1} K^{-2}', 'uW cm^{-1} K^{-2}', 'μW/cm⋅K^{2}', 'uW/cmK^{2}', 'μWcm^{-1} K^{-2}', 'μWcm^{-1}K^{-2}']:
                property_entity.property_numeric_value *= 100
                property_entity.property_numeric_error *= 100
                property_entity.property_unit = 'μW m^{-1} K^{-2}'
            elif property_entity.property_unit == '' and property_entity.property_numeric_value<=1.0 and property_entity.property_numeric_value>=0.0 and property_entity.entity_name in self.convert_fraction_to_percentage:
                property_entity.property_numeric_value *= 100
                property_entity.property_unit = '%'
            
            
            

    def run(self):
        """Calls all methods in order to process data"""
        self.coreference_property_names()
        self.process_sentence(self.grouped_spans, self.property_extraction)
        self.property_value_postprocessing()