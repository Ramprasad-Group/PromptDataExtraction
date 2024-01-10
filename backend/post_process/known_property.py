import pylogg as log
from backend.post_process.validator import DataValidator

class NameValidator(DataValidator):
    def __init__(self, db, method, prop_meta) -> None:
        """ For a specific extraction method and property, identify the rows of
        extracted_properties having invalid property names.
        """
        self.prop_meta = prop_meta
        self.namelist = [n.lower() for n in self.prop_meta.other_names]
        super().__init__(
            db, method, self.prop_meta.property, 'extracted_properties',
            'invalid_property_name')

    def _get_record_sql(self) -> str:
        return """
            SELECT * FROM (
                SELECT
                    ep.id,
                    ep.entity_name
                FROM extracted_properties ep
                -- filter with extraction method
                WHERE ep.method_id = :mid
                AND ep.id > :last ORDER BY ep.id
            ) AS ft
            -- Ignore previously processed ones
            WHERE NOT EXISTS (
                SELECT 1 FROM filtered_data fd 
                WHERE fd.filter_name = :filter
                AND fd.filter_on = :data
                AND fd.table_name = :table
                AND fd.table_row = ft.id
            );
        """
    
    def _check_filter(self, row) -> bool:
        """ Returns True if row passes the invalid name filter. """

        # Lowercase
        name = row.entity_name.lower()
        
        if name in self.namelist:
            return False

        log.warn("Invalid property name: {} ({})", row.entity_name, row.id)
        return True


class RangeValidator(DataValidator):
    def __init__(self, db, method, prop_meta) -> None:
        """ For a specific extraction method and property, identify the rows of
        extracted_properties having out of range values.
        """
        self.prop_meta = prop_meta
        super().__init__(
            db, method, self.prop_meta.property, 'extracted_properties',
            'out_of_range')


    def _get_record_sql(self) -> str:
        return """
            SELECT * FROM (
                SELECT
                    ep.id,
                    ep.numeric_value as value
                FROM extracted_properties ep
                -- filter with extraction method
                WHERE ep.method_id = :mid
                AND ep.id > :last ORDER BY ep.id
            ) AS ft
            -- Ignore previously processed ones
            WHERE NOT EXISTS (
                SELECT 1 FROM filtered_data fd 
                WHERE fd.filter_name = :filter
                AND fd.filter_on = :data
                AND fd.table_name = :table
                AND fd.table_row = ft.id
            );
        """
    
    def _check_filter(self, row) -> bool:
        """ Return True if row passes the out of range filter. """

        criteria = [
            row.value <= self.prop_meta.upper_limit,
            row.value >= self.prop_meta.lower_limit,
        ]

        if all(criteria):
            return False
        
        log.warn("Out of range property value: {} ({})", row.value, row.id)
        return True


class UnitValidator(DataValidator):
    def __init__(self, db, method, prop_meta) -> None:
        """ For a specific extraction method and property, identify the rows of
        extracted_properties having invalid property unit.
        """
        self.prop_meta = prop_meta
        super().__init__(
            db, method, self.prop_meta.property, 'extracted_properties',
            'invalid_property_unit')


    def _get_record_sql(self) -> str:
        return """
            SELECT * FROM (
                SELECT
                    ep.id,
                    ep.unit as value
                FROM extracted_properties ep
                -- filter with extraction method
                WHERE ep.method_id = :mid
                AND ep.id > :last ORDER BY ep.id
            ) AS ft
            -- Ignore previously processed ones
            WHERE NOT EXISTS (
                SELECT 1 FROM filtered_data fd 
                WHERE fd.filter_name = :filter
                AND fd.filter_on = :data
                AND fd.table_name = :table
                AND fd.table_row = ft.id
            );
        """
    
    def _check_filter(self, row) -> bool:
        """ Return True if row passes the invalid unit filter. """

        # Handle None, lowercase
        unit = row.value.lower() if row.value else ""
        unitlist = [u.lower() for u in self.prop_meta.units]

        criteria = [
            unit in unitlist,
            # no unit
            len(unit) == 0 and len(unitlist) == 0
        ]

        if any(criteria):
            return False
        
        log.warn("Invalid property unit: {} ({})", unit, row.id)
        return True


class NameSelector(DataValidator):
    def __init__(self, db, method, prop_meta) -> None:
        """ For a specific extraction method and property, identify the rows of
        extracted_properties having matching property names.
        """
        self.prop_meta = prop_meta
        self.namelist = [n.lower() for n in self.prop_meta.other_names]

        super().__init__(
            db, method, self.prop_meta.property, 'extracted_properties',
            'valid_property_name')


    def _get_record_sql(self) -> str:
        return """
            SELECT * FROM (
                SELECT
                    ep.id,
                    ep.entity_name
                FROM extracted_properties ep
                -- filter with extraction method
                WHERE ep.method_id = :mid
                AND ep.id > :last ORDER BY ep.id
            ) AS ft
            -- Ignore previously processed ones
            WHERE NOT EXISTS (
                SELECT 1 FROM filtered_data fd 
                WHERE fd.filter_name = :filter
                AND fd.filter_on = :data
                AND fd.table_name = :table
                AND fd.table_row = ft.id
            );
        """
    
    def _check_filter(self, row) -> bool:
        """ Returns True if row passes the matching name filter. """

        # Lowercase
        name = row.entity_name.lower()

        if name in self.namelist:
            log.info("Matching property name: {} ({})", row.entity_name, row.id)
            return True

        return False



class SelectedUnitValidator(DataValidator):
    def __init__(self, db, method, prop_meta) -> None:
        """ For a specific extraction method and property, identify the existing
        rows of filtered_data having invalid property unit.
        """
        self.prop_meta = prop_meta
        self.source_filter = 'valid_property_name'
        self.unitlist = [u.lower() for u in self.prop_meta.units]

        super().__init__(
            db, method, self.prop_meta.property, 'extracted_properties',
            'invalid_property_unit')


    def _get_record_sql(self) -> str:
        assert self.source_filter
        return f"""
            SELECT * FROM (
                SELECT
                    ep.id,
                    ep.unit as value
                -- filter the data that has been filtered before
                FROM filtered_data fd
                JOIN extracted_properties ep ON ep.id = fd.table_row 
                WHERE ep.method_id      = :mid
                AND   fd.table_name 	= 'extracted_properties'
                -- match by previous filter name
                AND   fd.filter_name 	= '{self.source_filter}'
                AND   fd.filter_on 		= :data
                AND   ep.id > :last ORDER BY ep.id
            ) AS ft
            -- Ignore previously processed ones
            WHERE NOT EXISTS (
                SELECT 1 FROM filtered_data fd 
                WHERE fd.filter_name = :filter
                AND fd.filter_on  = :data
                AND fd.table_name = :table
                AND fd.table_row  = ft.id
            );
        """
    
    def _check_filter(self, row) -> bool:
        """ Return True if row passes the invalid unit filter. """

        # Handle None, lowercase
        unit = row.value.lower() if row.value else ""

        criteria = [
            unit in self.unitlist,
            # no unit
            len(unit) == 0 and len(self.unitlist) == 0
        ]

        if any(criteria):
            return False
        
        log.warn("Invalid property unit: {} ({})", unit, row.id)
        return True



class SelectedRangeValidator(DataValidator):
    def __init__(self, db, method, prop_meta) -> None:
        """ For a specific extraction method and property, identify the existing
        rows of filtered_data having invalid property unit.
        """
        self.prop_meta = prop_meta
        self.source_filter = 'valid_property_name'
        self.unitlist = [u.lower() for u in self.prop_meta.units]

        super().__init__(
            db, method, self.prop_meta.property, 'extracted_properties',
            'out_of_range')


    def _get_record_sql(self) -> str:
        assert self.source_filter
        return f"""
            SELECT * FROM (
                SELECT
                    ep.id,
                    ep.numeric_value as value
                -- filter the data that has been filtered before
                FROM filtered_data fd
                JOIN extracted_properties ep ON ep.id = fd.table_row 
                WHERE ep.method_id      = :mid
                AND   fd.table_name 	= 'extracted_properties'
                -- match by previous filter name
                AND   fd.filter_name 	= '{self.source_filter}'
                AND   fd.filter_on 		= :data
                AND   ep.id > :last ORDER BY ep.id
            ) AS ft
            -- Ignore previously processed ones
            WHERE NOT EXISTS (
                SELECT 1 FROM filtered_data fd 
                WHERE fd.filter_name = :filter
                AND fd.filter_on  = :data
                AND fd.table_name = :table
                AND fd.table_row  = ft.id
            );
        """
    
    def _check_filter(self, row) -> bool:
        """ Return True if row passes the out of range filter. """

        criteria = [
            row.value <= self.prop_meta.upper_limit,
            row.value >= self.prop_meta.lower_limit,
        ]

        if all(criteria):
            return False
        
        log.warn("Out of range property value: {} ({})", row.value, row.id)
        return True
