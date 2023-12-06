import re
import pylogg as log
from backend.post_process.validator import DataValidator

class TableValidator(DataValidator):
    def __init__(self, db, method, prop_meta) -> None:
        """ For a specific extraction method and property, identify the rows of
        extracted_properties where source text might be a table.
        """
        self.prop_meta = prop_meta
        super().__init__(
            db, method, self.prop_meta.property, 'extracted_properties',
            'is_table')


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
                AND fd.filter_on = :data
                AND fd.table_name = :table
                AND fd.table_row = ft.id
            );
        """
    
    def _check_filter(self, row) -> bool:
        """ Return True if row passes the filter. """

        # Consecutive digits seperated by whitespace
        needle = r"\s?\d+\s+\d+[%\s]?"

        # Distance between two consecutive digits.
        dist = 20

        m = 0
        last = -dist
        for match in re.finditer(needle, row.text):
            start = match.span()[0]
            if start - last < dist:
                m += 1
            if m >= 3:
                log.warn("Table detected: {}", row.id)
                return True
            last = match.span()[1]

        return False

