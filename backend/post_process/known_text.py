import re
import pylogg as log
from backend.post_process.validator import DataValidator

class TableValidator(DataValidator):
    def __init__(self, db, method) -> None:
        super().__init__(db, method)

        # Set required parameters
        self.filter_name = 'is_table'
        self.table_name = 'extracted_properties'


    def _get_record_sql(self) -> str:
        return """
            SELECT * FROM (
                SELECT
                    ep.id,
                    pt."text"
                FROM extracted_properties ep
                -- get material
                JOIN extracted_materials em ON em.id = ep.material_id 
                -- get doi, text
                JOIN paper_texts pt ON pt.id = em.para_id
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

        # Consecutive digits seperated by whitespace
        needle = r"\s?\d+\s+\d+[%\s]?"
        matches = re.findall(needle, row.text)
        # matches = re.finditer()
        if len(matches) >= 3:
            breakpoint()
            log.note("Found table, consecutive digits in {}", row.id)
            return True

        return False

