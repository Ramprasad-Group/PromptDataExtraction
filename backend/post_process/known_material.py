import pylogg as log
from backend.post_process.validator import DataValidator

class PolymerValidator(DataValidator):
    def __init__(self, db, method) -> None:
        super().__init__(db, method)

        # Set required parameters
        self.filter_name = 'is_polymer'
        self.table_name = 'extracted_properties'


    def _get_record_sql(self) -> str:
        return """
            SELECT * FROM (
                SELECT
                    ep.id
                FROM extracted_properties ep
                -- get material class
                JOIN extracted_materials em ON em.id = ep.material_id 
                -- filter with extraction method
                WHERE ep.method_id = :mid
                -- only the known polymers
                AND em.material_class = 'POLYMER'
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
        return True

