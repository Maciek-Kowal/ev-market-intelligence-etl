import json
import logging
import asyncio
from config import load_manifest
from pipeline import ScrapingPipeline


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger("Main")
    logger.info("Uruchamianie potoku")

    try:
        manifest = load_manifest("models_manifest.json")
        pipeline = ScrapingPipeline(manifest)
        results = asyncio.run(pipeline.run())

        if results:
            with open("sample.json", "w", encoding="utf-8") as f:
                json.dump(results, f, indent=4, ensure_ascii=False)
            logger.info(f"Pomyślnie zapisano {len(results)} pojazdów do pliku sample.json")

    except Exception as e:
        logger.critical(f"Krytyczny błąd potoku: {e}")