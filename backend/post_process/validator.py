import pylogg
from tqdm import tqdm
from backend import postgres, sett
from backend.postgres import checkpoint, persist
from backend.postgres.orm import ExtractedProperties

log = pylogg.New("data_valid")

class DataValidator:
    def __init__(self, db, method) -> None:
        self.filter_name = None
        self.table_name = None
        self.ckpt_name = None
        
        self.db = db
        self.method = method

        self.ckpt_info = {
            'user': sett.Run.userName,
            'method': self.method.name,
        }


    def _get_last_ckpt(self) -> int:
        # Last processed row.
        last = checkpoint.get_last(
            self.db, self.ckpt_name, self.table_name, self.ckpt_info)
        log.info("Last run row ID: {}", last)
        return last
    

    def _get_records(self, query, last = 0) -> list:
        t2 = log.info(
            "Querying list of non-processed '{}' items.", self.filter_name)

        records = postgres.raw_sql(
            query, filter = self.filter_name, mid=self.method.id, last=last)

        t2.note("Found {} items not processed.", len(records))

        if len(records):
            log.info("Unprocessed Row IDs: {} to {}",
                    records[0].id, records[-1].id)
        return records
    

    def _get_record_sql(self) -> str:
        raise NotImplementedError(self.filter_name)


    def _check_filter(self, row) -> bool:
        """ Return True if row passes the filter. """
        raise NotImplementedError(self.filter_name)


    def process_items(self, limit : int = None):
        assert self.filter_name
        assert self.table_name

        # Init variables
        self.ckpt_name = f"data_{self.filter_name}_{self.method.id}"

        # Run the pipeline.
        sql = self._get_record_sql()
        last = self._get_last_ckpt()
        records = self._get_records(sql, last)

        n = 0
        p = 0
        # Process each item.
        for row in tqdm(records):
            n += 1

            # Row passed?
            if self._check_filter(row):
                p += 1
                persist.add_data_filter(
                    self.db, self.filter_name, self.table_name, row.id)
                log.trace("Pass: {} ({})", self.filter_name, row.id)

            # Commit every 100 items
            if n % 100 == 0:
                self.db.commit()

            last = row.id
            if not (n % 500) or n == len(records) or n == limit:
                log.info("Processed {} paragraphs.", n)

            if limit and n > limit:
                break

        # Store the last processed id.
        checkpoint.add_new(
            self.db, self.ckpt_name, self.table_name, last, self.ckpt_info)
        
        self.db.commit()

