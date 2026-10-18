from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class PrometheusConfig:
    host: str
    port: int

    @staticmethod
    def from_file(path: Path) -> PrometheusConfig:
        if not path.is_file():
            raise FileNotFoundError(path)

        with path.open('rb') as fh:
            vals = json.load(fh)

            return PrometheusConfig(
                host=vals["host"] or "screeps.com",
                port=vals["port"] or 443,
            )
