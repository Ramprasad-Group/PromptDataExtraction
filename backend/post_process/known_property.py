import pylogg as log
from backend.post_process.validator import DataValidator

class NameValidator(DataValidator):
    def __init__(self, db, method, meta) -> None:
        super().__init__(db, method)

        # Set required parameters
        self.filter_name = 'invalid_property_name'
        self.table_name = 'extracted_properties'
        self.prop_meta = meta


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
                AND fd.target_table = :table
                AND fd.target_id = ft.id
            );
        """
    
    def _check_filter(self, row) -> bool:
        """ Return True if row passes the filter. """
        if row.entity_name in self.prop_meta.other_names:
            return False
        
        log.warn("Invalid property name: {} ({})", row.entity_name, row.id)
        return True


class RangeValidator(DataValidator):
    def __init__(self, db, method, meta) -> None:
        super().__init__(db, method)

        # Set required parameters
        self.filter_name = 'out_of_range'
        self.table_name = 'extracted_properties'
        self.prop_meta = meta


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
                AND fd.target_table = :table
                AND fd.target_id = ft.id
            );
        """
    
    def _check_filter(self, row) -> bool:
        """ Return True if row passes the filter. """

        criteria = [
            row.value <= self.prop_meta.upper_limit,
            row.value >= self.prop_meta.lower_limit,
        ]

        if all(criteria):
            return False
        
        log.warn("Out of range property value: {} ({})", row.value, row.id)
        return True


class UnitValidator(DataValidator):
    def __init__(self, db, method, meta) -> None:
        super().__init__(db, method)

        # Set required parameters
        self.filter_name = 'invalid_property_unit'
        self.table_name = 'extracted_properties'
        self.prop_meta = meta


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
                AND fd.target_table = :table
                AND fd.target_id = ft.id
            );
        """
    
    def _check_filter(self, row) -> bool:
        """ Return True if row passes the filter. """

        criteria = [
            row.value in self.prop_meta.units,
            # no unit
            len(row.value.strip()) == 0 and len(self.prop_meta.units) == 0
        ]

        if any(criteria):
            return False
        
        log.warn("Invalid property unit: {} ({})", row.value, row.id)
        return True
