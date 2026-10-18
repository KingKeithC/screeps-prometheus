
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class BasicAuth:
    username: str
    password: str

@dataclass
class TokenAuth:
    token: str

@dataclass
class ScreepsConfig:
    auth: BasicAuth | TokenAuth
    protocol: str
    host: str
    port: int
    path: str
    branch: str

    @staticmethod
    def from_file(path: Path) -> ScreepsConfig:
        if not path.is_file():
            raise FileNotFoundError(path)

        with path.open('rb') as fh:
            vals = json.load(fh)

            return ScreepsConfig(
                auth=TokenAuth(vals["token"]) if vals["token"] else BasicAuth(username=vals["username"], password=vals["password"]),
                protocol=vals["protocol"] or "https",
                host=vals["host"] or "screeps.com",
                port=vals["port"] or 443,
                path=vals["path"] or "/",
                branch=vals["branch"] or "main",
            )
