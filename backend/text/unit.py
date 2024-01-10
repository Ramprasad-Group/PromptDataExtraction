"""
Module for unit normalization.

"""
from backend.types import Property

# List of properties to convert to percentage.
convert_fraction_to_pct = []

def normalize_unit(prop : Property) -> Property:
    """ Normalize the unit and value of a Property.

        @Todo: add more units to this.
    """

    # Remove trailing period
    if prop.unit and prop.unit[-1] in ['.']:
        prop.unit = prop.unit[:-1].strip()

    if prop.value is not None:
        assert type(prop.value) == float, "Property value must be float"

        if prop.unit == 'K':
            prop.value -= 273
            prop.unit = '° C'
        elif prop.unit in ['kPa', 'KPa']:
            prop.value /= 1000
            prop.property_numeric_error /= 1000
            prop.unit = 'MPa'
        elif prop.unit == 'GPa':
            prop.value *= 1000
            prop.property_numeric_error *= 1000
            prop.unit = 'MPa'
        elif prop.unit in ['mS/cm', 'mS cm^{-1}', 'mS / cm', 'mS*cm^{-1}']:
            prop.value /= 1000
            prop.property_numeric_error /= 1000
            prop.unit = 'S/cm'
        elif prop.unit in ['S/m', 'S m^{-1}']:
            prop.value /= 100
            prop.property_numeric_error /= 100
            prop.unit = 'S cm^{-1}'
        elif prop.unit in ['mV']:
            prop.value /= 1000
            prop.property_numeric_error /= 1000
            prop.unit = 'V'
        elif prop.unit in ['kg/mol', 'kg mol^{-1}','KDa', 'kDa']:
            prop.value *= 1000
            prop.property_numeric_error *= 1000 
            prop.unit = 'g/mol'
        elif prop.unit in ['mW/mK', 'mW m^{-1} K^{-1}', 'mW/m*K', 'mW*m^{-1}*K^{-1}', 'mW/(m*K)', 'mW/m K', 'mW/m * K']:
            prop.value /= 1000
            prop.property_numeric_error /= 1000
            prop.unit = 'W m^{-1} K^{-1}'
        elif prop.unit in ['kW kg^{-1}', 'kW/kg', 'kW*kg^{-1}', 'W g^{-1}']:
            prop.value *= 1000
            prop.property_numeric_error *= 1000
            prop.unit = 'W kg^{-1}'
        elif prop.unit in ['kW g^{-1}']:
            prop.value *= 1000000
            prop.property_numeric_error *= 1000000
            prop.unit = 'W kg^{-1}'
        elif prop.unit in ['mA g^{-1}', 'mA/g', 'mA*g^{-1}', 'mAg^{-1}']:
            prop.value /= 1000
            prop.property_numeric_error /= 1000
            prop.unit = 'A g^{-1}'
        elif prop.unit in ['μA cm^{-2}', 'μA/cm^{2}', 'μA*cm^{-2}', 'uA cm^{-2}']:
            prop.value /= 1000
            prop.property_numeric_error /= 1000
            prop.unit = 'mA cm^{-2}'
        elif prop.unit in ['mA m^{-2}', 'mA/m^{2}']:
            prop.value /= 10000
            prop.property_numeric_error /= 10000
            prop.unit = 'mA cm^{-2}'
        elif prop.unit in ['A/m^{2}', 'A m^{-2}']:
            prop.value /= 10
            prop.property_numeric_error /= 10
            prop.unit = 'mA cm^{-2}'
        elif prop.unit in ['nA/cm^{2}', 'nA cm^{-2}']:
            prop.value /= 1000000
            prop.property_numeric_error /= 1000000
            prop.unit = 'mA cm^{-2}'
        elif prop.unit in ['A*cm^{-2}', 'A cm^{-2}']:
            prop.value *= 1000
            prop.property_numeric_error *= 1000
            prop.unit = 'mA cm^{-2}'
        elif prop.unit in ['mW m^{-2}', 'mW/m^{2}', 'mW*m^{-2}', 'mWm^{-2}']:
            prop.value /= 10000
            prop.property_numeric_error /= 10000
            prop.unit = 'mW cm^{-2}'
        elif prop.unit in ['W cm^{-2}', 'W/cm^{2}', 'Wcm^{-2}']:
            prop.value *= 1000
            prop.property_numeric_error *= 1000
            prop.unit = 'mW cm^{-2}'
        elif prop.unit in ['μW cm^{-2}', 'μW/cm^{2}', 'uW cm^{-2}', 'μW*cm^{-2}', 'μWcm^{-2}', 'uW/cm^{2}', 'μ W/cm^{2}']:
            prop.value /= 1000
            prop.property_numeric_error /= 1000
            prop.unit = 'mW cm^{-2}'
        elif prop.unit in ['W/m^{2}', 'W m^{-2}', 'μW.mm^{-2}', 'μW mm^{-2}']:
            prop.value /= 10
            prop.property_numeric_error /= 10
            prop.unit = 'mW cm^{-2}'
        elif prop.unit in ['mW/mm^{2}']:
            prop.value *= 100
            prop.property_numeric_error *= 100
            prop.unit = 'mW cm^{-2}'
        elif prop.unit in ['kW/cm^{2}']:
            prop.value *= 1000000
            prop.property_numeric_error *= 1000000
            prop.unit = 'mW cm^{-2}'
        elif prop.unit in ['cm^{3}(STP) cm/cm^{2} s cmHg', 'cm^{3}(STP) cm/(cm^{2} s cmHg)']:
            prop.value *= 10**10
            prop.property_numeric_error *= 10**10
            prop.unit = 'Barrer'
        elif prop.unit in ['mol m m^{-2} s^{-1} Pa^{-1}( barrer)', 'mol m m^{-2} s^{-1} Pa^{-1}']:
            prop.value *= float(10**16)/3.35
            prop.property_numeric_error *= float(10**16)/3.35
            prop.unit = 'Barrer'
        elif prop.unit in ['μg g^{-1}', 'μg/g']:
            prop.value /= 1000
            prop.property_numeric_error /= 1000
            prop.unit = 'mg/g'
        elif prop.unit in ['g g^{-1}', 'g/g', 'g/ g']:
            prop.value *= 1000
            prop.property_numeric_error *= 1000
            prop.unit = 'mg/g'
        elif prop.unit in ['kg m^{-3}', 'kg/m^{3}']:
            prop.value /= 1000
            prop.property_numeric_error /= 1000
            prop.unit = 'g/cm^{3}'
        elif prop.unit in ['μM', 'uM', 'μmol L^{-1}']:
            prop.value /= 10**6
            prop.property_numeric_error /= 10**6
            prop.unit = 'M'
        elif prop.unit in ['nM', 'nmol L^{-1}']:
            prop.value /= 10**9
            prop.property_numeric_error /= 10**9
            prop.unit = 'M'
        elif prop.unit in ['pM',]:
            prop.value /= 10**15
            prop.property_numeric_error /= 10**15
            prop.unit = 'M'
        elif prop.unit in ['mM',]:
            prop.value /= 10**3
            prop.property_numeric_error /= 10**3
            prop.unit = 'M'
        elif prop.unit in ['mg/cm^{3}', 'mg cm^{-3}', 'g/dm^{3}', 'g/L', 'mg/cc', 'kg*m^{-3}', 'mg*cm^{-3}', 'kgm^{-3}']:
            prop.value /= 10**3
            prop.property_numeric_error /= 10**3
            prop.unit = 'g/cm^{3}'
        elif prop.unit in ['kcal/mol', 'kcal mol^{-1}', 'kcal/mole']:
            prop.value *= 4.18
            prop.property_numeric_error *= 4.18
            prop.unit = 'kJ/mol'
        elif prop.unit in ['μA μM^{-1} cm^{-2}', 'μA cm^{-2} μM^{-1}', 'uA uM^{-1} cm^{-2}', 'mA mM^{-1} cm^{-2}', 'mA cm^{-2} mM^{-1}', 'μAμM^{-1}cm^{-2}']:
            prop.value *= 1000
            prop.property_numeric_error *= 1000
            prop.unit = 'μA mM^{-1} cm^{-2}'
        elif prop.unit in ['nA mM^{-1} cm^{-2}']:
            prop.value /= 1000
            prop.property_numeric_error /= 1000
            prop.unit = 'μA mM^{-1} cm^{-2}'
        elif prop.unit in ['Pa*s', 'Pa.s', 'Pa s', 'Pas', 'Pa s^{-1}']:
            prop.value *= 1000
            prop.property_numeric_error *= 1000
            prop.unit = 'mPa s'
        elif prop.unit in ['kΩ/sq', 'kΩ/ #', 'kΩ sq^{-1}', 'kΩ/square']:
            prop.value *= 1000
            prop.property_numeric_error *= 1000
            prop.unit = 'Ω/sq'
        elif prop.unit in ['MV/cm']:
            prop.value *= 1000
            prop.property_numeric_error *= 1000
            prop.unit = 'kV/mm'
        elif prop.unit in ['kV/cm']:
            prop.value /= 10
            prop.property_numeric_error /= 10
            prop.unit = 'kV/mm'
        elif prop.unit in ['Pa']:
            prop.value /= 1000000
            prop.property_numeric_error /= 1000000
            prop.unit = 'MPa'
        elif prop.unit in ['μΩ cm', 'μΩ*cm', 'μΩcm']:
            prop.value /= 1000000
            prop.property_numeric_error /= 1000000
            prop.unit = 'Ω cm'
        elif prop.unit in ['Ω m', 'Ωm']:
            prop.value *= 100
            prop.property_numeric_error *= 100
            prop.unit = 'Ω cm'
        elif prop.unit in ['L m^{-2} h^{-1} MPa^{-1}', 'L*m^{-2}*h^{-1}*MPa^{-1}']:
            prop.value *= 100
            prop.property_numeric_error *= 100
            prop.unit = 'Ω cm'
        elif prop.unit in ['μW cm^{-1} K^{-2}', 'uW cm^{-1} K^{-2}', 'μW/cm⋅K^{2}', 'uW/cmK^{2}', 'μWcm^{-1} K^{-2}', 'μWcm^{-1}K^{-2}']:
            prop.value *= 100
            prop.property_numeric_error *= 100
            prop.unit = 'μW m^{-1} K^{-2}'
        elif prop.unit == '' and prop.value<=1.0 and prop.value>=0.0 and prop.name in convert_fraction_to_pct:
            prop.value *= 100
            prop.unit = '%'
        
    return prop
