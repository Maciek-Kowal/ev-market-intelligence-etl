import logging
from config import ModelsManifest, DriveTrain
from network import OtomotoNetwork
from parser import OtomotoParser


class ScrapingPipeline:
    def __init__(self, manifest: ModelsManifest):
        self.manifest = manifest
        self.logger = logging.getLogger(self.__class__.__name__)
        self.network = OtomotoNetwork(max_concurrent=3)
        self.parser = OtomotoParser()

    def build_query_tasks(self) -> list[str]:
        self.logger.info("Generowanie adresów URL")
        target_urls = []
        base_filters = "&search%5Bfilter_enum_damaged%5D=0&search%5Bfilter_enum_no_accident%5D=1&search%5Bfilter_enum_registered%5D=1"

        for vehicle in self.manifest.vehicles:
            base_url = f"https://www.otomoto.pl/osobowe/{vehicle.make.lower()}/{vehicle.slug}?"

            if vehicle.drivetrain == DriveTrain.EV:
                final_url = f"{base_url}search%5Bfilter_enum_fuel_type%5D=electric{base_filters}"
            elif vehicle.drivetrain == DriveTrain.HEV:
                final_url = f"{base_url}search%5Bfilter_enum_fuel_type%5D=hybrid{base_filters}"

            target_urls.append(final_url)

        self.logger.info(f"Pomyślnie przygotowano {len(target_urls)} zapytań HTTP")
        return target_urls

    async def run(self):
        urls = self.build_query_tasks()

        html_pages = await self.network.fetch_all(urls)
        self.logger.info(f"HTML: {len(html_pages)}/{len(urls)}.")

        all_cars = []
        for html in html_pages:
            raw_json = self.parser.extract_json_state(html)
            if raw_json:
                parsed_cars = self.parser.parse_offers(raw_json)
                all_cars.extend(parsed_cars)

        self.logger.info(f"Wyciągnięto łącznie {len(all_cars)} czystych ogłoszeń.")
        return all_cars