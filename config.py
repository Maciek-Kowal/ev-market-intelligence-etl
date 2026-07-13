import json
import logging
from enum import Enum
from typing import List
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

class DriveTrain(str, Enum):
    EV = "EV"
    HEV = "HEV"

class Segment(str, Enum):
    B = "B"
    C = "C"
    D = "D"
    CSUV = "C-SUV"

class VehicleDef(BaseModel):
    make: str
    model: str
    segment: Segment
    drivetrain: DriveTrain
    slug: str

class ManifestMetadata(BaseModel):
    version: str
    description: str
    target_market: str

class ModelsManifest(BaseModel):
    metadata: ManifestMetadata
    vehicles: List[VehicleDef]


def load_manifest(path: str) -> ModelsManifest:
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        manifest = ModelsManifest(**raw_data)
        logger.info(f"Załadowano {len(manifest.vehicles)} aut z pliku w wersji {manifest.metadata.version}.")
        return manifest

    except ValidationError as e:
        logger.error("Plik JSON jest niezgodny ze schematem:")
        for error in e.errors():
            logger.error(f" -> Lokalizacja: {error['loc']} | Opis: {error['msg']}")
        raise
    except FileNotFoundError:
        logger.critical(f"Nie znaleziono pliku konfiguracyjnego pod adresem: {path}")
        raise