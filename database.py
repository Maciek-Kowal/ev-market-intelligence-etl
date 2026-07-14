import os
import logging
from dotenv import load_dotenv
from google.cloud import bigquery


class BigQueryLoader:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        load_dotenv()

        self.client = bigquery.Client()

    def upload_to_fact_table(self, data: list[dict], project_id: str, dataset_id: str):
        if not data:
            self.logger.warning("Brak danych do wysłania")
            return

        table_id = f"{project_id}.{dataset_id}.fact_listings"
        errors = self.client.insert_rows_json(table_id, data)

        if not errors:
            self.logger.info(f"Załadowano {len(data)} wierszy do {table_id}")
        else:
            self.logger.error(f"Napotkano błędy podczas ładowania: {errors}")