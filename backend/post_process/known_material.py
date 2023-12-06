from backend.post_process.validator import DataValidator

class PolymerSelector(DataValidator):
    def __init__(self, db, method, prop_meta) -> None:
        """ For a specific extraction method and property, identify the rows of
        extracted_properties having known polymer names.
        """
        self.prop_meta = prop_meta
        super().__init__(
            db, method, self.prop_meta.property, 'extracted_properties',
            'is_polymer')


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
                AND fd.filter_on = :data
                AND fd.table_name = :table
                AND fd.table_row = ft.id
            );
        """


    def _check_filter(self, row) -> bool:
        """ Return True if row passes the filter. """
        return True

