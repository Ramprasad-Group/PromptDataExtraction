""" Extract property value pairs and post process them to obtain a single property record """
import re
import pylogg
from backend.record_extraction import utils
from backend.postgres.orm import PropertyMetadata
from backend.record_extraction.base_classes import PropertyValuePair


log = pylogg.New('llm')

ADDITIONAL_UNITS = [
    # Order matters. Keep the longer ones first.
    "° C", "°C", " ° C", " °C", " S cm^{-1}",
    " Pa s", " mPa s", " MPa",
    " cm²/s", " mm^{2}/s",
    " vol %", " mol %", " wt %", " %", " K", " kcal mol^{-1}",
    " nm^3", " nm",
    " kg mol^{-1}", " g mol^{-1}", " g/mol", " g mol^-1", " g/m^2/day",
    " mmol/g", " dL/g", " g/dL", " mg mL^{-1}",
    " erg/cm^2", " g/cm^3", " m^2/g", " cm^{3} g^{-1}",
    " kJ mol^{-1}", " kcal mol^{-1}", " J g^{-1}", 
    " cd A^{-1}", 
]


REGEX_MATCHES = {
    "for-and-for": (
        r"(\d+.+)\sfor\s.+and\s(.+\d+.+)\sfor\s",
    )
}


class PropertyDataExtractor:
    RE_NUMBER = r'[+-]?\d+[.]?\d*(?:\s?±\s?\d+[.]?\d*)?(?:x10\^{[-]?\d*})?'
    RE_EXP = r'10\^{[-]?\d*}'
    RE_EXP_UNIT = r'([a-zA-Z]+\^{[-]?\d*})'
    property_value_descriptor_list = [
        '<', '>', '~', '=', 'and', '≈', 'to', '-'
    ]

    def __init__(self, db, prop_metadata_file : str):
        self.db = db
        self.prop_records_metadata = \
            utils.load_property_metadata(prop_metadata_file)
        
        self.unitlist = self._load_unit_list(db) + ADDITIONAL_UNITS
        self.convert_fraction_to_percentage = [
            v['property_list'] for k, v in self.prop_records_metadata.items()
            if v['unit_list'][0] == '%'
        ]
        log.trace("Initialized {}", self.__class__.__name__)

    def parse_property(self, property_name : str,
                       property_value : str) -> PropertyValuePair:
        assert type(property_value) == str

        prop = PropertyValuePair(
            entity_name=property_name, property_value=property_value)

        self._process_entity(prop)
        self._normalize_unit(prop)

        return None if prop.property_numeric_value is None else prop


    def _process_entity(self, prop : PropertyValuePair):
        name = prop.entity_name
        value = prop.property_value

        if not value or not name:
            return

        # for and for
        match = re.search(r"(.*\d+.+)\sfor\s(.+)\sand\s(.*\d+.+)\sfor\s(.+)",
                          value)
        if match:
            self._parse_double_values(prop, match.group(1), match.group(3))
            prop.condition_str = f"avg for {match.group(2)} and {match.group(4)}"
            return

        # Fallback to original NER type parsing.
        return self._process_entity_ner(prop)


    def _parse_double_values(self, prop : PropertyValuePair,
                             val1 : str, val2 : str):
        """ Parse and set the average number, error and unit
        from two property value strings. """
        n1, u1, e1 = self._parse_num_unit(val1)
        n2, u2, e2 = self._parse_num_unit(val2)

        prop.property_numeric_value = None
        if n1 is not None:
            prop.property_numeric_value = n1

        if n2 is not None:
            prop.property_numeric_value += n2
            prop.property_numeric_value /= 2
            prop.property_value_avg = True

        if e1 is not None:
            prop.property_numeric_error = e1

        if e2 is not None:
            prop.property_numeric_error += e2
            prop.property_numeric_error /= 2

        if (u1 == u2) or (u1 is None and u2):
            prop.property_unit = u2


    def _parse_num_unit(self, value : str) -> tuple:
        """ Given a value string with single number, try to parse
            the number, error and unit.
        """
        num, err, unit = None, None, None
        unit = self._get_unit(value)
        if unit:
            value = value.rstrip(unit)

        if '±' in value:
            values = value.split('±')
            num = self._get_numeric(values[0].strip())
            err = self._get_numeric(values[-1].strip())
        elif '+/-' in value:
            values = value.split('+/-')
            num = self._get_numeric(values[0].strip())
            err = self._get_numeric(values[-1].strip())
        else:
            try:
                num = self._get_numeric(value)
            except:
                num = None
        return num, unit, err

    def _get_unit(self, text : str) -> str | None:
        # Match against the list of known units
        for item in self.unitlist:
            if text.endswith(item):
                return item
        return None


    def _process_entity_ner(self, prop : PropertyValuePair):
        property_value = prop.property_value

        if not property_value:
            return

        # If there is no number, return
        if re.search(r'\d+', property_value) is None:
            prop.property_numeric_value = None
            return

        # Normalize the double numbers.
        property_value = re.sub(r'(\d)-(\d)', '\\1 - \\2', property_value)
        property_value = re.sub(r'(\d) (\d)', '\\1\\2', property_value)
        property_value = re.sub(r'(\d) x (\d)', '\\1x\\2', property_value)

        units_to_replace = re.findall(self.RE_EXP_UNIT, property_value)

        units_dict = dict()
        for i, unit in enumerate(units_to_replace):
            units_dict[f'AAA{chr(i+64)}'] = unit
            property_value = property_value.replace(unit, f'AAA{chr(i+64)}')

        numeric_values = re.findall(self.RE_NUMBER, property_value)

        for value in numeric_values:
            if '±' in value:
                values = value.split('±')
                prop.property_numeric_value = \
                    self._get_numeric(values[0].strip())
                prop.property_numeric_error = \
                    self._get_numeric(values[-1].strip())
                break
            if '+/-' in value:
                values = value.split('+/-')
                prop.property_numeric_value = \
                    self._get_numeric(values[0].strip())
                prop.property_numeric_error = \
                    self._get_numeric(values[-1].strip())
                break
        else:
            if numeric_values:
                prop.property_numeric_value = \
                    sum([self._get_numeric(num) for num in numeric_values])
                prop.property_numeric_value /= (len(numeric_values))
            else:
                prop.property_numeric_value = ''

        # Deal with cases like 10^{7} not covered by our regular expressions.
        if '10^{' in property_value and \
            not any(['10^{' in value for value in numeric_values]):
            
            numeric_values = re.findall(self.RE_EXP, property_value)
            if numeric_values:
                prop.property_numeric_value = sum([self._get_numeric(
                    num) for num in numeric_values])/(len(numeric_values))
            else:
                prop.property_numeric_value = ''

        prop.property_value_avg = len(numeric_values) > 1
        leftover_str = property_value
        for value in numeric_values:
            leftover_str = leftover_str.replace(value, '')

        # Replace units back
        prop.property_value_descriptor = ''

        for str_item in self.property_value_descriptor_list:
            if str_item in leftover_str:
                prop.property_value_descriptor = prop.property_value_descriptor+str_item
                leftover_str = leftover_str.replace(str_item, '')

        self._find_unit(prop)

    def _find_unit(self, prop : PropertyValuePair):
        # Try to detect the unit.
        property_value = prop.property_value
        property_value = property_value.replace("° C", "°C")

        # Match against the list of known units
        for item in self.unitlist:
            if property_value.endswith(item):
                prop.property_unit = item
                return

        unit = ''
        numbers = list(re.finditer(self.RE_NUMBER, property_value))

        if len(numbers) == 1:
            # single value, assume unit is the first word after the value.
            rightstr = property_value[numbers[0].span()[1]:]
            words = rightstr.split()
            if len(words):
                unit = words[0]

        elif len(numbers) == 2:
            # double numbers. Unit can be present after the first number.
            middlestr = property_value[numbers[0].span()[1]:numbers[1].span()[0]]
            middlestr = middlestr.strip()
            middlewords = middlestr.split()

            if middlestr == ".":
                # Decimal point, unit should be the first word
                # after the last number.
                rightstr = property_value[numbers[-1].span()[1]:]
                words = rightstr.split()
                if len(words):
                    unit = words[0]

            elif " at " in middlestr:
                # Second number is condition
                # Unit should be the first word after the first number.
                rightstr = property_value[numbers[0].span()[1]:]
                words = rightstr.split()
                if len(words):
                    unit = words[0]

                # Override previous calculations
                prop.property_numeric_value = self._get_numeric(numbers[0])
                prop.property_value_descriptor = property_value.split(" at ")[1]

            elif len(middlewords) == 1 and \
                middlestr in self.property_value_descriptor_list:
                # and, to, - etc.
                if prop.property_value_descriptor == '':
                    prop.property_value_descriptor = middlestr

                # Unit should be the first word after the last number.
                rightstr = property_value[numbers[-1].span()[1]:]
                words = rightstr.split()
                if len(words):
                    unit = words[0]

            # If two or more words in the middle, take the first one.
            elif len(middlewords) >= 2:
                unit = middlewords[0]
        else:
            # is_scientific = "^{" in property_value and "}" in property_value
            # Unit should be the first word after the last number.
            rightstr = property_value[numbers[-1].span()[1]:]
            words = rightstr.split()
            if len(words):
                unit = words[0]

        prop.property_unit = unit

    def _load_unit_list(self, db) -> list[str]:
        units = []
        for prop in PropertyMetadata().get_all(db):
            units += prop.other_names
        return units

    def _get_numeric(self, value : str) -> float:
        """ Convert string to float. Handle scientific notations. """
        if '^{' in value and '}' in value and 'x' in value:
            mantissa, exponent = value.split('x')[0].strip(), value.split(
                'x')[1].strip().replace('10^{', '').replace('}', '')
            numeric_value = float(mantissa)*10**(float(exponent))
            return numeric_value
        elif '^{' in value and '}' in value and 'x' not in value:
            exponent = value.strip().replace('10^{', '').replace('}', '')
            numeric_value = 10**(float(exponent))
            return numeric_value
        else:
            return float(value)

    def _normalize_unit(self, prop : PropertyValuePair):
        """ Convert units for a predefined list of entries
            into a predefined standard.
        """
        # Add more units to this
        if prop.property_unit and prop.property_unit[-1] in ['.']:
            prop.property_unit = prop.property_unit[:-1].strip()

        if prop.property_numeric_value:
            if prop.property_unit == 'K':
                prop.property_numeric_value -= 273
                prop.property_unit = '°C'
            elif prop.property_unit in ['kPa', 'KPa']:
                prop.property_numeric_value /= 1000
                prop.property_numeric_error /= 1000
                prop.property_unit = 'MPa'
            elif prop.property_unit == 'GPa':
                prop.property_numeric_value *= 1000
                prop.property_numeric_error *= 1000
                prop.property_unit = 'MPa'
            elif prop.property_unit in ['mS/cm', 'mS cm^{-1}', 'mS / cm', 'mS*cm^{-1}']:
                prop.property_numeric_value /= 1000
                prop.property_numeric_error /= 1000
                prop.property_unit = 'S/cm'
            elif prop.property_unit in ['S/m', 'S m^{-1}']:
                prop.property_numeric_value /= 100
                prop.property_numeric_error /= 100
                prop.property_unit = 'S cm^{-1}'
            elif prop.property_unit in ['mV']:
                prop.property_numeric_value /= 1000
                prop.property_numeric_error /= 1000
                prop.property_unit = 'V'
            elif prop.property_unit in ['kg/mol', 'kg mol^{-1}', 'KDa', 'kDa']:
                prop.property_numeric_value *= 1000
                prop.property_numeric_error *= 1000
                prop.property_unit = 'g/mol'
            elif prop.property_unit in ['mW/mK', 'mW m^{-1} K^{-1}', 'mW/m*K', 'mW*m^{-1}*K^{-1}', 'mW/(m*K)', 'mW/m K', 'mW/m * K']:
                prop.property_numeric_value /= 1000
                prop.property_numeric_error /= 1000
                prop.property_unit = 'W m^{-1} K^{-1}'
            elif prop.property_unit in ['kW kg^{-1}', 'kW/kg', 'kW*kg^{-1}', 'W g^{-1}']:
                prop.property_numeric_value *= 1000
                prop.property_numeric_error *= 1000
                prop.property_unit = 'W kg^{-1}'
            elif prop.property_unit in ['kW g^{-1}']:
                prop.property_numeric_value *= 1000000
                prop.property_numeric_error *= 1000000
                prop.property_unit = 'W kg^{-1}'
            elif prop.property_unit in ['mA g^{-1}', 'mA/g', 'mA*g^{-1}', 'mAg^{-1}']:
                prop.property_numeric_value /= 1000
                prop.property_numeric_error /= 1000
                prop.property_unit = 'A g^{-1}'
            elif prop.property_unit in ['μA cm^{-2}', 'μA/cm^{2}', 'μA*cm^{-2}', 'uA cm^{-2}']:
                prop.property_numeric_value /= 1000
                prop.property_numeric_error /= 1000
                prop.property_unit = 'mA cm^{-2}'
            elif prop.property_unit in ['mA m^{-2}', 'mA/m^{2}']:
                prop.property_numeric_value /= 10000
                prop.property_numeric_error /= 10000
                prop.property_unit = 'mA cm^{-2}'
            elif prop.property_unit in ['A/m^{2}', 'A m^{-2}']:
                prop.property_numeric_value /= 10
                prop.property_numeric_error /= 10
                prop.property_unit = 'mA cm^{-2}'
            elif prop.property_unit in ['nA/cm^{2}', 'nA cm^{-2}']:
                prop.property_numeric_value /= 1000000
                prop.property_numeric_error /= 1000000
                prop.property_unit = 'mA cm^{-2}'
            elif prop.property_unit in ['A*cm^{-2}', 'A cm^{-2}']:
                prop.property_numeric_value *= 1000
                prop.property_numeric_error *= 1000
                prop.property_unit = 'mA cm^{-2}'
            elif prop.property_unit in ['mW m^{-2}', 'mW/m^{2}', 'mW*m^{-2}', 'mWm^{-2}']:
                prop.property_numeric_value /= 10000
                prop.property_numeric_error /= 10000
                prop.property_unit = 'mW cm^{-2}'
            elif prop.property_unit in ['W cm^{-2}', 'W/cm^{2}', 'Wcm^{-2}']:
                prop.property_numeric_value *= 1000
                prop.property_numeric_error *= 1000
                prop.property_unit = 'mW cm^{-2}'
            elif prop.property_unit in ['μW cm^{-2}', 'μW/cm^{2}', 'uW cm^{-2}', 'μW*cm^{-2}', 'μWcm^{-2}', 'uW/cm^{2}', 'μ W/cm^{2}']:
                prop.property_numeric_value /= 1000
                prop.property_numeric_error /= 1000
                prop.property_unit = 'mW cm^{-2}'
            elif prop.property_unit in ['W/m^{2}', 'W m^{-2}', 'μW.mm^{-2}', 'μW mm^{-2}']:
                prop.property_numeric_value /= 10
                prop.property_numeric_error /= 10
                prop.property_unit = 'mW cm^{-2}'
            elif prop.property_unit in ['mW/mm^{2}']:
                prop.property_numeric_value *= 100
                prop.property_numeric_error *= 100
                prop.property_unit = 'mW cm^{-2}'
            elif prop.property_unit in ['kW/cm^{2}']:
                prop.property_numeric_value *= 1000000
                prop.property_numeric_error *= 1000000
                prop.property_unit = 'mW cm^{-2}'
            elif prop.property_unit in ['cm^{3}(STP) cm/cm^{2} s cmHg', 'cm^{3}(STP) cm/(cm^{2} s cmHg)']:
                prop.property_numeric_value *= 10**10
                prop.property_numeric_error *= 10**10
                prop.property_unit = 'Barrer'
            elif prop.property_unit in ['mol m m^{-2} s^{-1} Pa^{-1}( barrer)', 'mol m m^{-2} s^{-1} Pa^{-1}']:
                prop.property_numeric_value *= float(10**16)/3.35
                prop.property_numeric_error *= float(10**16)/3.35
                prop.property_unit = 'Barrer'
            elif prop.property_unit in ['μg g^{-1}', 'μg/g']:
                prop.property_numeric_value /= 1000
                prop.property_numeric_error /= 1000
                prop.property_unit = 'mg/g'
            elif prop.property_unit in ['g g^{-1}', 'g/g', 'g/ g']:
                prop.property_numeric_value *= 1000
                prop.property_numeric_error *= 1000
                prop.property_unit = 'mg/g'
            elif prop.property_unit in ['kg m^{-3}', 'kg/m^{3}']:
                prop.property_numeric_value /= 1000
                prop.property_numeric_error /= 1000
                prop.property_unit = 'g/cm^{3}'
            elif prop.property_unit in ['μM', 'uM', 'μmol L^{-1}']:
                prop.property_numeric_value /= 10**6
                prop.property_numeric_error /= 10**6
                prop.property_unit = 'M'
            elif prop.property_unit in ['nM', 'nmol L^{-1}']:
                prop.property_numeric_value /= 10**9
                prop.property_numeric_error /= 10**9
                prop.property_unit = 'M'
            elif prop.property_unit in ['pM',]:
                prop.property_numeric_value /= 10**15
                prop.property_numeric_error /= 10**15
                prop.property_unit = 'M'
            elif prop.property_unit in ['mM',]:
                prop.property_numeric_value /= 10**3
                prop.property_numeric_error /= 10**3
                prop.property_unit = 'M'
            elif prop.property_unit in ['mg/cm^{3}', 'mg cm^{-3}', 'g/dm^{3}', 'g/L', 'mg/cc', 'kg*m^{-3}', 'mg*cm^{-3}', 'kgm^{-3}']:
                prop.property_numeric_value /= 10**3
                prop.property_numeric_error /= 10**3
                prop.property_unit = 'g/cm^{3}'
            elif prop.property_unit in ['kcal/mol', 'kcal mol^{-1}', 'kcal/mole']:
                prop.property_numeric_value *= 4.18
                prop.property_numeric_error *= 4.18
                prop.property_unit = 'kJ/mol'
            elif prop.property_unit in ['μA μM^{-1} cm^{-2}', 'μA cm^{-2} μM^{-1}', 'uA uM^{-1} cm^{-2}', 'mA mM^{-1} cm^{-2}', 'mA cm^{-2} mM^{-1}', 'μAμM^{-1}cm^{-2}']:
                prop.property_numeric_value *= 1000
                prop.property_numeric_error *= 1000
                prop.property_unit = 'μA mM^{-1} cm^{-2}'
            elif prop.property_unit in ['nA mM^{-1} cm^{-2}']:
                prop.property_numeric_value /= 1000
                prop.property_numeric_error /= 1000
                prop.property_unit = 'μA mM^{-1} cm^{-2}'
            elif prop.property_unit in ['Pa*s', 'Pa.s', 'Pa s', 'Pas', 'Pa s^{-1}']:
                prop.property_numeric_value *= 1000
                prop.property_numeric_error *= 1000
                prop.property_unit = 'mPa s'
            elif prop.property_unit in ['kΩ/sq', 'kΩ/ #', 'kΩ sq^{-1}', 'kΩ/square']:
                prop.property_numeric_value *= 1000
                prop.property_numeric_error *= 1000
                prop.property_unit = 'Ω/sq'
            elif prop.property_unit in ['MV/cm']:
                prop.property_numeric_value *= 1000
                prop.property_numeric_error *= 1000
                prop.property_unit = 'kV/mm'
            elif prop.property_unit in ['kV/cm']:
                prop.property_numeric_value /= 10
                prop.property_numeric_error /= 10
                prop.property_unit = 'kV/mm'
            elif prop.property_unit in ['Pa']:
                prop.property_numeric_value /= 1000000
                prop.property_numeric_error /= 1000000
                prop.property_unit = 'MPa'
            elif prop.property_unit in ['μΩ cm', 'μΩ*cm', 'μΩcm']:
                prop.property_numeric_value /= 1000000
                prop.property_numeric_error /= 1000000
                prop.property_unit = 'Ω cm'
            elif prop.property_unit in ['Ω m', 'Ωm']:
                prop.property_numeric_value *= 100
                prop.property_numeric_error *= 100
                prop.property_unit = 'Ω cm'
            elif prop.property_unit in ['L m^{-2} h^{-1} MPa^{-1}', 'L*m^{-2}*h^{-1}*MPa^{-1}']:
                prop.property_numeric_value *= 100
                prop.property_numeric_error *= 100
                prop.property_unit = 'Ω cm'
            elif prop.property_unit in ['μW cm^{-1} K^{-2}', 'uW cm^{-1} K^{-2}', 'μW/cm⋅K^{2}', 'uW/cmK^{2}', 'μWcm^{-1} K^{-2}', 'μWcm^{-1}K^{-2}']:
                prop.property_numeric_value *= 100
                prop.property_numeric_error *= 100
                prop.property_unit = 'μW m^{-1} K^{-2}'
            elif prop.property_unit == '' and prop.property_numeric_value <= 1.0 and prop.property_numeric_value >= 0.0 and prop.entity_name in self.convert_fraction_to_percentage:
                prop.property_numeric_value *= 100
                prop.property_unit = '%'