from multiprocessing.pool import ThreadPool
from pathlib import Path
from threading import Thread
from typing import Literal, Optional

from tap import Tap
from screeps_prometheus.prometheus import PrometheusConfig
from screeps_prometheus.screeps import ScreepsConfig

class ScreepsPrometheus(Tap):
    screeps_token: Optional[str] = None # A Token to use to connect to shard3 (quickstart)
    screeps_config: Optional[Path] = None # The path to a screeps.yaml or screeps.json config file.
    screeps_extra: Optional[ScreepsConfig] = None # Additional config to overwite any retrieved from file or standard locations.

    prometheus_config: Optional[Path] = None # The path to a json file containing the settings for the Prometheus/Export features.
    prometheus_extra: Optional[PrometheusConfig] = None # Additional config to overwite any retrieved from file or standard locations.

    action:Literal["tail-console", "serve-metrics", "both"] = "both" # The action to perform.

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

        metrics = Thread()
        if args.action == "serve-metrics" or args.action == "both":
            scraper = screeps_config.get_stat_scraper(api)
            metrics = Thread(target=prometheus_config.serve_forever, args=(scraper,))

        logs = Thread()
        if args.action == "tail-console" or args.action == "both":
            watcher = screeps_config.get_console_watcher(api, lambda log: print(log))
            logs = Thread(target=watcher.start)

        threads = [metrics, logs]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        exit(0)
