import logging
from src.config import ModelsManifest, DriveTrain
from src.network import OtomotoNetwork
from src.parser import OtomotoParser


class ScrapingPipeline:
    def __init__(self, manifest: ModelsManifest):
        self.manifest = manifest
        self.logger = logging.getLogger(self.__class__.__name__)
        self.network = OtomotoNetwork(max_concurrent=3)
        self.parser = OtomotoParser()

    def build_query_tasks(self) -> list[str]:
        self.logger.info("Generowanie bazowych adresów URL")
        target_urls = []
        base_filters = "&search%5Bfilter_enum_damaged%5D=0&search%5Bfilter_enum_no_accident%5D=1&search%5Bfilter_enum_registered%5D=1"

        for vehicle in self.manifest.vehicles:
            base_url = f"https://www.otomoto.pl/osobowe/{vehicle.make.lower()}/{vehicle.slug}?"

            if vehicle.drivetrain == DriveTrain.EV:
                final_url = f"{base_url}search%5Bfilter_enum_fuel_type%5D=electric{base_filters}"
            elif vehicle.drivetrain == DriveTrain.HEV:
                final_url = f"{base_url}search%5Bfilter_enum_fuel_type%5D=hybrid{base_filters}"
            target_urls.append(final_url)

        self.logger.info(f"Przygotowano {len(target_urls)} bazowych zapytań.")
        return target_urls

    async def run(self):
        base_urls = self.build_query_tasks()
        all_cars = []
        current_page = 1
        active_urls = base_urls.copy()

        while active_urls:
            self.logger.info(f"--- Pobieranie strony {current_page} dla {len(active_urls)} aktywnych modeli ---")
            paged_urls = [f"{url}&page={current_page}" for url in active_urls]
            html_pages = await self.network.fetch_all(paged_urls)
            next_active_urls = []

            for i, html in enumerate(html_pages):
                if html is None:
                    continue

                raw_json = self.parser.extract_json_state(html)
                if raw_json:
                    parsed_cars = self.parser.parse_offers(raw_json)

                    if parsed_cars:
                        all_cars.extend(parsed_cars)
                        next_active_urls.append(active_urls[i])

            active_urls = next_active_urls
            current_page += 1

        self.logger.info(f"Sukces! Wyciągnięto łącznie {len(all_cars)} ogłoszeń ze wszystkich stron.")
        return all_cars