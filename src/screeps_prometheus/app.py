
from pathlib import Path
from typing import Optional

from tap import Tap

from screeps_prometheus.prometheus import PrometheusConfig
from screeps_prometheus.screeps import ScreepsConfig


class ScreepsPrometheus(Tap):
    screeps_token: Optional[str] = None
    screeps_config: Optional[Path] = None
    screeps_extra: Optional[ScreepsConfig] = None

    prometheus_config: Optional[Path] = None
    prometheus_extra: Optional[PrometheusConfig] = None

    def get_screeps_config(self) -> ScreepsConfig:
        fallback = ScreepsConfig.from_standard_locations()

        config = None
        if self.screeps_config is not None:
            config = ScreepsConfig.from_file(self.screeps_config)
            if config is not None:
                config += fallback
        elif self.screeps_token is not None:
            config = ScreepsConfig.from_token(self.screeps_token)
            config += fallback
        elif fallback is not None:
            config = fallback

        if config is None:
            raise LookupError("No suitable config could be found, did you at least provide a token?")

        if self.screeps_extra is not None:
            config += self.screeps_extra

        return config

    def get_prometheus_config(self) -> PrometheusConfig:
        if self.prometheus_config is not None:
            config = PrometheusConfig.from_file(self.prometheus_config)
        else:
            config = PrometheusConfig()

        config += self.prometheus_extra
        return config


    @staticmethod
    def run() -> None:
        args = ScreepsPrometheus().parse_args()
        screeps_config = args.get_screeps_config()
        prometheus_config = args.get_prometheus_config()
        api = screeps_config.login()
        scraper = screeps_config.get_stat_scraper(api)
        prometheus_config.serve_forever(scraper)
