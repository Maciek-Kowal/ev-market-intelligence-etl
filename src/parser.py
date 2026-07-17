import json
import logging
from selectolax.parser import HTMLParser

class OtomotoParser:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def extract_json_state(self, html_text: str):
        tree = HTMLParser(html_text)
        script_node = tree.css_first("script#__NEXT_DATA__")

        if script_node:
            try:
                return json.loads(script_node.text())
            except json.JSONDecodeError as e:
                self.logger.error(f"Błąd dekodowania JSON: {e}")
        else:
            self.logger.warning("Nie znaleziono tagu __NEXT_DATA__!")
        return None

    def parse_offers(self, raw_json: dict) -> list[dict]:
        extracted_cars = []
        try:
            urql_state = raw_json.get("props", {}).get("pageProps", {}).get("urqlState", {})

            for key, value in urql_state.items():
                data_str = value.get("data", "{}")
                data_obj = json.loads(data_str)

                if "advertSearch" in data_obj:
                    edges = data_obj["advertSearch"].get("edges", [])

                    for edge in edges:
                        node = edge.get("node", {})
                        if not node: continue

                        params = {p["key"]: p["value"] for p in node.get("parameters", [])}
                        title = node.get("title", "").lower()
                        desc = node.get("shortDescription", "").lower()

                        car_record = {
                            "ad_id": node.get("id"),
                            "url": node.get("url"),
                            "price": node.get("price", {}).get("amount", {}).get("value"),
                            "year": params.get("year"),
                            "mileage": params.get("mileage"),
                            "make": params.get("make"),
                            "model": params.get("model"),
                            "fuel_type": params.get("fuel_type"),
                            "engine_power": params.get("engine_power"),
                            "battery_kwh": params.get("battery_capacity"),
                            "battery_owned": "wynajem" not in title and "wynajem" not in desc,
                            "city": node.get("location", {}).get("city", {}).get("name"),
                        }
                        extracted_cars.append(car_record)

        except Exception as e:
            self.logger.error(f"Błąd parsowania: {e}")

        return extracted_cars