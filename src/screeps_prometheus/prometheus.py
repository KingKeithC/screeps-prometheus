from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, NoReturn

from prometheus_client import CollectorRegistry, start_http_server
from prometheus_client.metrics_core import GaugeMetricFamily, Metric
from prometheus_client.registry import Collector

from screeps_prometheus import ScreepsStats, StatScraper


@dataclass
class PrometheusConfig:
    addr: str = "0.0.0.0"
    port: int = 8585
    jobName: str = "screeps-prometheus"
    metricsNamespace: str = "screeps"

    @staticmethod
    def from_file(path: Path) -> PrometheusConfig:
        if not path.is_file():
            raise FileNotFoundError(path)

        with path.open('rb') as fh:
            vals = json.load(fh)
            return PrometheusConfig(**vals)

    def serve_forever(self, scraper: StatScraper) -> NoReturn:
        # Create the registry with our custom collector.
        reg = CollectorRegistry()
        reg.register(ScreepsCollector(self, scraper))

        print(f'Serving Metrics on {self.addr}:{self.port}')
        server, t = start_http_server(addr=self.addr, port=self.port, registry=reg)
        server.serve_forever()

        print(f'Shutting down...')
        server.server_close()
        t.join()
        print(f'Bye :)')
        exit(0)

type ReportScaler = int | float
type ReportMetric = dict[str, ReportValue]
type ReportValue = ReportScaler | ReportMetric

@dataclass
class FieldSchema:
    labelKeys: list[str] | None = None
    unit: str = "number"

type ReportSchema = dict[str, str | list[str]] | dict[str, ReportSchema]

class ScreepsCollector(Collector):
    def __init__(self, config: PrometheusConfig, statGetter: StatScraper) -> None:
        self._config = config
        self._statGetter = statGetter

    def parse_metrics(
            self,
            schema: FieldSchema | ReportSchema,
            path: list[str],
            data: ReportValue,
        ) -> Iterable[Metric]:

        info: str = (f"isinstance(data, int | float): {isinstance(data, int | float)}"
            f"isinstance(data, dict): {isinstance(data, dict)}"
            f"isinstance(schema, dict): {isinstance(schema, dict)}"
            f"isinstance(schema, FieldSchema): {isinstance(schema, FieldSchema)}")

        # Base Case
        if isinstance(data, int | float):
            print(f"Base Case: {path} {schema=}")
            # One metric

            fs = schema if isinstance(schema, FieldSchema) else FieldSchema(
                unit=getattr(schema, "unit", "number"),
                labelKeys=getattr(schema, "labelKeys", None),
            )

            # Schema:
            # "last_reset_time": {
            #   "unit": "ticks"
            # },

            # Data:
            # "last_reset_time": 8675309

            metricName = "_".join(path)
            metricKey = "_".join([self._config.metricsNamespace, metricName])
            yield GaugeMetricFamily(
                name=metricKey,
                value=data,
                documentation=f'Auto gauge for {metricName}',
                unit=fs.unit
            )

        # Recursive Case - Multiple Scaler Metrics, w/o Labels
        elif isinstance(schema, FieldSchema) and schema.labelKeys is None:
            print(f"Multiple Scaler Metrics, w/o Labels: {path}, {schema=}")
            # Multiple metrics with no labels and shared FieldSchema:

            # Schema:
            # "meminfo": {
            #   "unit": "bytes(SI)"
            # },

            # Data:
            # "meminfo": {
            #     "total_heap_size": 93204480,
            #     "total_heap_size_executable": 524288,
            #     "total_physical_size": 57683968,
            #     "total_available_size": 742508904,
            #     "used_heap_size": 29066496,
            #     "heap_size_limit": 775946240,
            #     "malloced_memory": 581736,
            #     "peak_malloced_memory": 20454784,
            #     "externally_allocated_size": 39767332
            # },
            for mName, mVal in data.items():
                yield from self.parse_metrics(
                    schema=schema,
                    path=path + [mName],
                    data=mVal,
                )


        # Recursive Case - Single Scaler Metric, w/Labels
        elif isinstance(schema, FieldSchema) and schema.labelKeys is not None:
            print(f"Single Scaler Metric, w/Labels Case: {path}, {schema=}")
            # One metric with multiple labels and one FieldSchema:

            # Schema:
            # "room_quota": {
            #   "labelKeys": [
            #     "role",
            #     "room"
            #   ],
            #   "unit": "number"
            # },

            # Data:
            # "room_quota": {
            #     "Miner": {
            #         "E28S47": 3
            #     },
            #     "Worker": {
            #         "E28S47": 12
            #     },
            #     "Defender": {
            #         "E28S47": 0
            #     },
            #     "Scout": {
            #         "E28S47": 1
            #     },
            #     "Attacker": {
            #         "E28S47": 1
            #     },
            #     "Claimer": {
            #         "E28S47": 1
            #     }
            # },
            metricName = "_".join(path)
            metricKey = "_".join([self._config.metricsNamespace, metricName])
            gauge = GaugeMetricFamily(
                name=metricKey,
                documentation=f'Auto gauge for {metricName}',
                unit=schema.unit,
                labels=schema.labelKeys,
            )

            for label, rest in data.items():
                if isinstance(rest, dict):
                    for nextLabel, final in rest.items():
                        if isinstance(final, int | float):
                            gauge.add_metric([label, nextLabel], final)
                        else:
                            raise ValueError(f"Value expected to be int or float, was type {type(final)=}, {final=}")
                else:
                    gauge.add_metric([label], rest)

            yield gauge

        # Recursive Case, collection of metrics and schemas
        elif isinstance(schema, dict):
            print(f"Recursive Case: {path} {schema=} {len(data)=}")
            # Schema:
            # "resources": { ... },
            # "meminfo": { ... },
            # "roleStats": {
            #   "global_quota": {... },
            #   "room_quota": {... },
            #   "assigned_room_count": {... }
            # },

            # Data:
            # "resources": { ... },
            # "meminfo": { ... },
            # "roleStats": {
            #   "global_quota": {... },
            #   "room_quota": {... },
            #   "assigned_room_count": {... }
            # },

            if (len(schema) != len(data)):
                print(f"info: {info}\nschema: {json.dumps(schema)}\ndata: {json.dumps(data)}\npath: {path}")
                raise ValueError(f"Schema and Data len mismatch: {len(schema)=} {len(data)=}")

            metric_names = list(schema.keys())
            for m in metric_names:
                nextSchema = schema.get(m)
                nextData = data[m]
                nextPath = path + [m]

                if isinstance(nextSchema, str | list | None):
                    raise Exception("Dict Expected.")

                fp = None
                if nextSchema.get("unit", None) is not None:
                    fp = FieldSchema(
                        unit=nextSchema.get("unit"), # type: ignore
                        labelKeys=nextSchema.get("labelKeys"), # type: ignore
                    )

                # Recurse on another of this case
                yield from self.parse_metrics(nextSchema if fp is None else fp, nextPath, nextData)
        else:
            print(f"info: {info}\nschema: {json.dumps(schema)}\ndata: {json.dumps(data)}\npath: {path}")
            raise Exception("Unhandled Else Case")


    def collect(self) -> Iterable[Metric]:
        print("Collecting stats...")
        latest: ScreepsStats | None = self._statGetter()
        if latest is None:
            print("Stats fetch was null.")
            return

        time = latest["data"]["time"]
        yield GaugeMetricFamily("time", "The time as of which the stats are valid.", value=time)

        schema = latest["data"]["schema"]
        data = latest["data"]["data"]

        # Parse each item in the stat dictionary into a gauge and return the gauge
        yield from self.parse_metrics(schema,  [], data)
