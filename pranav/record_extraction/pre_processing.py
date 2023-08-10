"""Contains pre processing code to merge input tokens and parse material mentions while parsing the text"""

import utils
from base_classes import MaterialMention, RecordProcessor, EntityList, PropertyMention, GROUPED_SPAN_COLUMNS
from collections import namedtuple

class GroupTokens(RecordProcessor):
    def __init__(self, spans, logger=None):
        """
        Groups consecutive tokens having the same label
        Parameters
        ---------------
        spans: List[NamedTuple]
            List each entry of which is a Namedtuple containing the token and its label

        Returns
        ---------------
        grouped_spans: List[NamedTuple]
            List each entry of which is a Namedtuple containing the token and its label which adjacent tokens with the same label merged
        material_mentions: List[dict]
            Contains all material mentions in text with some metadata initialized from base class
        """
        super(GroupTokens, self).__init__()
        self.spans = spans
        self.logger = logger
    
    def group_tokens(self):
        """Group all consecutive tokens that have the same entity label"""
        span_length = len(self.spans)
        grouped_spans = []
        # Output grouped token format includes information on start and end of original tokens - Useful for computing performance metrics
        token_label = namedtuple('token_label', GROUPED_SPAN_COLUMNS)
        i = 0
        material_names = []
        property_names = []
        material_mentions = EntityList()
        property_mentions = EntityList()
        string_numbers = [str(i) for i in range(10)]
        offset=0
        while i < span_length:
            current_label = self.spans[i].label
            token_start = i+offset
            if current_label != 'O' and i<span_length-1:
                # start = i
                cumulative_token = [self.spans[i].text]
                if i < span_length-1: next_label = self.spans[i+1].label
                i+=1
                while next_label == current_label and i < span_length:
                    cumulative_token.append(self.spans[i].text)
                    if i < span_length-1: next_label = self.spans[i+1].label
                    i+=1
                token_end = i-1+offset
                joined_token = utils.token_post_processing(' '.join(cumulative_token)) # This will create a case in some cases where there is not a space as an artifice or tokenization as 1.80% will become 1.80 %
                # Check for abbreviations and handle coreferencing
                if current_label in self.material_entities and joined_token not in material_names:
                    if '/' in joined_token or (':' in joined_token and not (len(joined_token)>=3 and joined_token.index(':')!= len(joined_token)-1 and joined_token[joined_token.index(':')+1] in string_numbers)): # Condition handles cases where : part of IUPAC name
                        token_list = []
                        token=''
                        for chr in joined_token:
                            if chr != ':' and chr != '/':
                                token+=chr
                            else:
                                if token: token_list.append(token)
                                token_list.append(chr)
                                token=''
                        if token: token_list.append(token)
                        for j, token in enumerate(token_list):
                            if token in [':', '/']:
                                grouped_spans.append(token_label(token, 'O', token_start+j, token_start+j))
                            else:
                                for mat_mention in material_mentions.entity_list:
                                    if mat_mention.entity_name==token:
                                        mat_label=mat_mention.material_class
                                        grouped_spans.append(token_label(token, mat_label, token_start+j, token_start+j))
                                        break
                                else:
                                    material_names.append(token)
                                    material_mentions.entity_list.append(MaterialMention(entity_name=token, material_class=mat_label, coreferents=[token]))
                                    grouped_spans.append(token_label(token, current_label, token_start+j, token_start+j))
                        offset+=len(token_list)-1
            
                    else:
                        if joined_token in [')', '}']: # A material token cannon be a single bracket so this must happen when there is a tokenization issue
                            offset-=1 # This is taken care of in post-processing and hence we skip over this token
                        else:
                            material_names.append(joined_token)
                            # Initialize one material record from base class
                            material_mentions.entity_list.append(MaterialMention(entity_name=joined_token, material_class=current_label, coreferents=[joined_token]))
                            grouped_spans.append(token_label(joined_token, current_label, token_start, token_end))
                
                elif current_label=='PROP_NAME' and joined_token not in property_names:
                    property_names.append(joined_token)
                    # Initialize one material record from base class
                    property_mentions.entity_list.append(PropertyMention(entity_name=joined_token, coreferents=[joined_token]))
                    grouped_spans.append(token_label(joined_token, current_label, token_start, token_end))
                elif joined_token[-1]=='.': # Assumption, there is never a good reason for a token to end in a dot, if this is an abbreviation, by convention we split the dot to a different token
                    grouped_spans.append(token_label(joined_token[:-1], current_label, token_start, token_end)) # The dot is being separated out into a different token
                    grouped_spans.append(token_label(joined_token[-1], 'O', token_end+1, token_end+1)) # Implicitly assumes length of string greater than 1
                    offset+=1
                else:
                    grouped_spans.append(token_label(joined_token, current_label, token_start, token_end))
            
            else:
                grouped_spans.append(token_label(self.spans[i].text, self.spans[i].label, token_start, token_start))
                i+=1
        return grouped_spans, material_mentions, property_mentions
    