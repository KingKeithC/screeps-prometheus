import json
from pathlib import Path
from typing import Any, Callable, Optional
import yaml

# Needed by other classes so must be declared here
type ScreepsStats = dict[str, Any]
type StatScraper = Callable[[], ScreepsStats | None]

def from_json_or_yaml(path: Path) -> Optional[object]:
    with path.open('r') as fh:
        # Try to parse with yaml first
        yamlObj = yaml.load(fh, yaml.Loader)
        if yamlObj is not None: return yamlObj

        # Then fallback to JSON if we got nothing
        jsonObj = json.load(fh)
        if jsonObj is not None: return jsonObj

    return None

from screeps_prometheus.app import ScreepsPrometheus

def main():
    ScreepsPrometheus.run()
