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
                AND em.material_class ILIKE 'polymer'

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
        """ Return True if row passes the is_polymer filter. """
        return True



class SelectedPolymerSelector(DataValidator):
    def __init__(self, db, method, prop_meta) -> None:
        """ For a specific extraction method and property, identify the rows of
        extracted_properties having known polymer names.
        """
        self.prop_meta = prop_meta
        self.source_filter = 'valid_property_name'
        super().__init__(
            db, method, self.prop_meta.property, 'extracted_properties',
            'is_polymer')


    def _get_record_sql(self) -> str:
        assert self.source_filter
        return f"""
            SELECT * FROM (
                SELECT  ep.id
                FROM filtered_data fd
                JOIN    extracted_properties ep ON ep.id = fd.table_row 
                JOIN    extracted_materials em ON em.id = ep.material_id 
                WHERE   ep.method_id    = :mid
                AND     fd.filter_name 	= '{self.source_filter}'
                AND     fd.table_name 	= 'extracted_properties'
                AND     fd.filter_on 	= :data
                AND     em.material_class ILIKE 'polymer'
                AND     ep.id > :last ORDER BY ep.id
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
        """ Return True if row passes the is_polymer filter. """
        return True

