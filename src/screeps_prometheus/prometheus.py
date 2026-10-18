from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class PrometheusConfig:
    host: str
    port: int
    jobName: str = "screeps-prometheus"
    metricsNamespace: str = "screeps"

    @staticmethod
    def from_file(path: Path) -> PrometheusConfig:
        if not path.is_file():
            raise FileNotFoundError(path)

        with path.open('rb') as fh:
            vals = json.load(fh)
            return PrometheusConfig(**vals)

    @property
    def gateway(self) -> str:
        return f'{self.host}:{self.port}'
