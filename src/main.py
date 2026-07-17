import os
import logging
import asyncio
from datetime import date
from dotenv import load_dotenv

from src.config import load_manifest
from src.pipeline import ScrapingPipeline
from src.database import BigQueryLoader

load_dotenv()


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def enrich_fact_data(raw_results: list[dict], current_snapshot_id: str) -> list[dict]:
    """Wycina zaledwie zmienne w czasie metryki (cena, przebieg) i wysyła do fact_listings."""
    today_str = date.today().isoformat()
    clean_facts = []

    for row in raw_results:
        clean_row = {
            "snapshot_id": current_snapshot_id,
            "ad_id": int(row.get("ad_id", 0)),
            "scrape_date": today_str,
            "price": float(row.get("price", 0)),
            "mileage": int(row.get("mileage", 0)),
            "url": row.get("url", ""),
            "city": row.get("city", "")
        }
        clean_facts.append(clean_row)
    return clean_facts


def enrich_dim_data(raw_results: list[dict], known_ids: set) -> list[dict]:
    """Wycina statyczne dane o pojeździe (wymiary) i przepuszcza tylko nowe ad_id."""
    clean_dims = []
    seen_in_this_batch = set()

    for row in raw_results:
        ad_id = int(row.get("ad_id", 0))
        if ad_id in known_ids or ad_id in seen_in_this_batch:
            continue

        battery_kwh_raw = row.get("battery_kwh")
        battery_kwh_clean = float(battery_kwh_raw) if battery_kwh_raw is not None else None

        engine_power_raw = row.get("engine_power")
        engine_power_clean = int(engine_power_raw) if engine_power_raw is not None else None

        clean_row = {
            "ad_id": ad_id,
            "make": row.get("make", ""),
            "model": row.get("model", ""),
            "year": int(row.get("year", 0)),
            "fuel_type": row.get("fuel_type", ""),
            "engine_power": engine_power_clean,
            "battery_kwh": battery_kwh_clean,
            "battery_owned": bool(row.get("battery_owned", True))
        }

        clean_dims.append(clean_row)
        seen_in_this_batch.add(ad_id)

    return clean_dims


if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger("Main")
    PROJECT_ID = os.getenv("GCP_PROJECT_ID")
    DATASET_ID = os.getenv("GCP_DATASET_ID")

    if not PROJECT_ID or not DATASET_ID:
        logger.critical("Błąd konfiguracji. Brak zmiennych w .env")
        exit(1)

    logger.info("Uruchamianie potoku End-to-End")
    today = date.today().isoformat()
    bq_loader = BigQueryLoader()

    logger.info("Sprawdzanie stanu bazy danych")
    if bq_loader.is_already_scraped_today(PROJECT_ID, DATASET_ID, today):
        logger.warning(f"Dane z dnia {today} są już w bazie. Przerywam działanie")
        exit(0)

    next_snapshot = bq_loader.get_next_snapshot_id(PROJECT_ID, DATASET_ID)
    logger.info(f"Przypisano nowy snapshot_id: {next_snapshot}")

    try:
        manifest = load_manifest("config/models_manifest.json")
        pipeline = ScrapingPipeline(manifest)
        raw_results = asyncio.run(pipeline.run())

        if raw_results and isinstance(raw_results, list):
            clean_facts = enrich_fact_data(raw_results, next_snapshot)
            logger.info("Wysyłanie danych do tabeli fact_listings...")
            bq_loader.upload_to_fact_table(clean_facts, PROJECT_ID, DATASET_ID)

            logger.info("Sprawdzanie znanych pojazdów dla tabeli vehicles...")
            known_ids = bq_loader.get_known_ad_ids(PROJECT_ID, DATASET_ID)
            clean_dims = enrich_dim_data(raw_results, known_ids)

            if clean_dims:
                logger.info(f"Znaleziono {len(clean_dims)} nowych aut. Wysyłanie do tabeli vehicles...")
                bq_loader.upload_to_dim_table(clean_dims, PROJECT_ID, DATASET_ID)
            else:
                logger.info("Brak nowych aut. Tabela vehicles nie wymaga aktualizacji.")

            logger.info("Zakończono pracę potoku!")

        else:
            logger.warning("Potok nie zwrócił żadnych danych")

    except Exception as e:
        logger.critical(f"Krytyczny błąd potoku: {e}", exc_info=True)