import os
import logging
from dotenv import load_dotenv
from google.cloud import bigquery


class BigQueryLoader:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        load_dotenv()

        self.client = bigquery.Client()

    def is_already_scraped_today(self, project_id: str, dataset_id: str, today_str: str) -> bool:
        """Sprawdza, czy w tabeli są już rekordy z dzisiejszą datą."""
        table_id = f"{project_id}.{dataset_id}.fact_listings"

        query = f"SELECT COUNT(*) as cnt FROM `{table_id}` WHERE scrape_date = DATE('{today_str}')"

        try:
            query_job = self.client.query(query)
            for row in query_job.result():
                self.logger.info(f"[Sprawdzanie Daty] Znaleziono {row.cnt} rekordów z datą {today_str}")
                if row.cnt > 0:
                    return True
        except Exception as e:
            self.logger.error(f"Nie udało się sprawdzić daty w BigQuery: {e}")

        return False

    def get_next_snapshot_id(self, project_id: str, dataset_id: str) -> str:
        """Pobiera najwyższy snapshot_id, zamienia na int i dodaje 1."""
        table_id = f"{project_id}.{dataset_id}.fact_listings"
        query = f"SELECT MAX(CAST(snapshot_id AS INT64)) as max_id FROM `{table_id}`"

        try:
            query_job = self.client.query(query)
            for row in query_job.result():
                if row.max_id is not None:
                    return str(row.max_id + 1)
        except Exception as e:
            self.logger.warning(f"Błąd pobierania snapshot_id, Szczegóły: {e}")

        return "1"

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

    def get_known_ad_ids(self, project_id: str, dataset_id: str) -> set:
        """Pobiera zbiór wszystkich ad_id, które już mamy w tabeli pojazdów."""
        table_id = f"{project_id}.{dataset_id}.vehicles"
        known_ids = set()
        query = f"SELECT ad_id FROM `{table_id}`"

        try:
            query_job = self.client.query(query)
            for row in query_job.result():
                known_ids.add(row.ad_id)
        except Exception as e:
            self.logger.warning(f"Błąd pobierania znanych ad_id: {e}")

        return known_ids

    def upload_to_dim_table(self, data: list[dict], project_id: str, dataset_id: str):
        """Wysyła nowe pojazdy do tabeli vehicles."""
        if not data:
            return

        table_id = f"{project_id}.{dataset_id}.vehicles"
        errors = self.client.insert_rows_json(table_id, data)

        if errors:
            self.logger.error(f"Błędy przy ładowaniu vehicles: {errors}")
        else:
            self.logger.info(f"Pomyślnie załadowano {len(data)} nowych pojazdów do tabeli vehicles")