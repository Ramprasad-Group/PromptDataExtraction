import pylogg
from backend.post_process.validator import DataValidator

log = pylogg.New('known_property')

class Validator(DataValidator):
    def __init__(self, db, method, meta) -> None:
        super().__init__(db, method)

        # Set required parameters
        self.filter_name = 'known_property'
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
                AND fd.target_table = 'extracted_properties'
                AND fd.target_id = ft.id
            );
        """
    
    def _check_filter(self, row) -> bool:
        """ Return True if row passes the filter. """
        if row.entity_name in self.prop_meta.other_names:
            return True
        
        log.warn("Unknown property name: {} ({})", row.entity_name, row.id)
        return False
