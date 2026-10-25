from pathlib import Path
from typing import Any, Callable, Optional

from tap import Tap

# Needed by other classes so must be declared here
type ScreepsStats = dict[str, Any]
type StatScraper = Callable[[], ScreepsStats | None]

from screeps_prometheus.prometheus import PrometheusConfig
from screeps_prometheus.screeps import ScreepsConfig, TokenAuth


class ScreepsPrometheus(Tap):
    screeps: Optional[str | Path | ScreepsConfig]
    prometheus: Optional[Path | PrometheusConfig]

    def get_screeps_config(self) -> ScreepsConfig:
        if isinstance(self.screeps, ScreepsConfig):
            return self.screeps
        elif isinstance(self.screeps, str):
            return ScreepsConfig(auth=TokenAuth(self.screeps))
        elif isinstance(self.screeps, Path):
            resolved = ScreepsConfig.from_file(self.screeps)
            if resolved is None: raise FileNotFoundError(self.screeps)
            return resolved
        elif self.screeps is None:
            resolved = ScreepsConfig.from_standard_locations()
            if resolved is None: raise LookupError("Could not find a screeps config file!")
            return resolved
        raise ValueError(f"`screeps` parsed but doesn't seem valid: {self.screeps}")

    def get_prometheus_config(self) -> PrometheusConfig:
        if isinstance(self.prometheus, PrometheusConfig):
            return self.prometheus
        elif isinstance(self.prometheus, Path):
            return PrometheusConfig.from_file(self.prometheus)
        elif self.prometheus is None:
            return PrometheusConfig()
        raise ValueError(f"`prometheus` parsed but doesn't seem valid: {self.prometheus}")

    @staticmethod
    def run() -> None:
        args = ScreepsPrometheus().parse_args()
        screeps_config = args.get_screeps_config()
        prometheus_config = args.get_prometheus_config()
        api = screeps_config.login()
        scraper = screeps_config.get_stat_scraper(api)
        prometheus_config.serve_forever(scraper)


def main():
    ScreepsPrometheus.run()
