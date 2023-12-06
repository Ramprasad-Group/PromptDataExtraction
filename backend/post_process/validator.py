import pylogg
from tqdm import tqdm
from backend import postgres, sett
from backend.postgres import checkpoint, persist

log = pylogg.New("data_valid")

class DataValidator:
    def __init__(self, db, method, filter_on, table_name, filter_name) -> None:
        """ Base class to insert into filtered_data table.
            Handles running individual filters.
        """
        self.db = db
        self.method = method
        self.filter_on      = filter_on
        self.table_name     = table_name
        self.filter_name    = filter_name
        
        self.ckpt_info = {
            'user'  : sett.Run.userName,
            'method': self.method.name,
            'data'  : self.filter_on
        }
        self.ckpt_name = None


    def _get_last_ckpt(self) -> int:
        """ Returns the id of last processed row from table_cursor. """
        last = checkpoint.get_last(
            self.db, self.ckpt_name, self.table_name, self.ckpt_info)
        return last
  

    def _get_records(self, query, last = 0) -> list:
        t2 = log.info("Querying list of non-processed '{}' {} items.",
            self.filter_name, self.filter_on)
        log.info("Last checkpoint: {}", last)

        records = postgres.raw_sql(query,
            data = self.filter_on,
            table = self.table_name,
            filter = self.filter_name,
            mid=self.method.id, last=last)

        t2.note("Found {} '{}' items not processed.", len(records),
                self.filter_name)

        if len(records):
            log.info("Unprocessed Row IDs: {} to {}",
                    records[0].id, records[-1].id)
        return records


    def _delete_existing(self):
        query = self._get_existing_sql()
        postgres.raw_sql(
            query, commit=True, mid=self.method.id,
            data=self.filter_on, filter=self.filter_name, table=self.table_name
        )
        log.warn("Deleted existing '{}' {} items from filtered_data.",
                 self.filter_name, self.filter_on)


    def _get_existing_sql(self) -> str:
        """ Return the SQL to delete existing rows of current filter. """
        return """
            DELETE FROM filtered_data fd 
            WHERE EXISTS (
                SELECT 1 FROM extracted_properties ep 
                WHERE ep.method_id = :mid
                AND ep.id = fd.table_row
            )
            AND fd.filter_on = :data
            AND fd.table_name = :table
            AND fd.filter_name = :filter;
        """


    def _get_record_sql(self) -> str:
        raise NotImplementedError(self.filter_name)


    def _check_filter(self, row) -> bool:
        """ Return True if row passes the filter. """
        raise NotImplementedError(self.filter_name)


    def process_items(self, limit : int = None, redo : bool = False,
                      remove : bool = True):

        assert self.filter_on
        assert self.filter_name
        assert self.table_name

        # Init variables
        self.ckpt_name = \
            f"data_{self.filter_name}_{self.method.id}_{self.filter_name}"

        # Remove the existing items
        if remove:
            redo = True
            self._delete_existing()

        # Get the SQL and last processed row.
        sql = self._get_record_sql()
        if redo:
            last = 0
        else:
            last = self._get_last_ckpt()

        # Get the rows that need to be processed.
        records = self._get_records(sql, last)

        if len(records) == 0:
            return

        n = 0
        p = 0

        # Process each row.
        for row in tqdm(records):
            n += 1

            # Row passed?
            if self._check_filter(row):
                p += 1
                persist.add_data_filter(
                    self.db,
                    filter_on=self.filter_on,
                    filter_name=self.filter_name,
                    table_name=self.table_name,
                    table_row=row.id
                )
                log.trace("Pass: {} ({})", self.filter_name, row.id)

            # Commit every 100 items
            if not (n % 100):
                self.db.commit()

            last = row.id

            if not (n % 500) or n == len(records) or n == limit:
                log.info(
                    "Processed {} '{}' filter items for {}, "
                    "Passed {}, Failed {}.",
                    n, self.filter_name, self.filter_on, p, n-p)

            if limit and n > limit:
                break

        # Store the last processed id.
        checkpoint.add_new(
            self.db, self.ckpt_name, self.table_name, last, self.ckpt_info)
        
        self.db.commit()

