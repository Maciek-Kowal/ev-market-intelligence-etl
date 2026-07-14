import os
import logging
import asyncio
from datetime import date
from dotenv import load_dotenv

from config import load_manifest
from pipeline import ScrapingPipeline
from database import BigQueryLoader

load_dotenv()


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def enrich_data(raw_results: list[dict]) -> list[dict]:
    """Funkcja transformująca dane."""
    today_str = date.today().isoformat()

    for row in raw_results:
        row["scrape_date"] = today_str
        row["ad_id"] = int(row.get("ad_id", 0))
        row["price"] = float(row.get("price", 0))
        row["year"] = int(row.get("year", 0))
        row["mileage"] = int(row.get("mileage", 0))
        if "snapshot_id" in row:
            del row["snapshot_id"]

    return raw_results


if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger("Main")
    PROJECT_ID = os.getenv("GCP_PROJECT_ID")
    DATASET_ID = os.getenv("GCP_DATASET_ID")

    if not PROJECT_ID or not DATASET_ID:
        logger.critical("Błąd konfiguracji")
        exit(1)

    logger.info("Uruchamianie potoku End-to-End.")

    try:
        manifest = load_manifest("models_manifest.json")

        pipeline = ScrapingPipeline(manifest)
        raw_results = asyncio.run(pipeline.run())

        if raw_results:
            clean_results = enrich_data(raw_results)

            logger.info("Nawiązywanie połączenia z Google BigQuery...")
            bq_loader = BigQueryLoader()

            bq_loader.upload_to_fact_table(
                data=clean_results,
                project_id=PROJECT_ID,
                dataset_id=DATASET_ID
            )

            logger.info(f"Załadowano {len(clean_results)} rekordów do chmury")
        else:
            logger.warning("Potok nie zwrócił żadnych danych")

    except Exception as e:
        logger.critical(f"Krytyczny błąd potoku: {e}")