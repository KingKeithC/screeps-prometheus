
from dataclasses import dataclass
import json
from pathlib import Path

import screepsapi


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
    host: str = "screeps.com"
    port: int = 443
    path: str = "/"
    branch: str = "main"
    ptr: bool = False
    protocol: str = "https"

    @staticmethod
    def from_file(path: Path) -> ScreepsConfig:
        if not path.is_file():
            raise FileNotFoundError(path)

        with path.open('rb') as fh:
            vals = json.load(fh)

            return ScreepsConfig(
                **vals,
                auth=TokenAuth(vals["token"]) if vals["token"] else BasicAuth(username=vals["username"], password=vals["password"]),
            )

    def login(self) -> screepsapi.API:
        if isinstance(self.auth, TokenAuth):
            authopts = {"token": self.auth.token}
        else:
            authopts = {"u": self.auth.username, "p": self.auth.password}

        return screepsapi.API(
            host=self.host,
            ptr=self.ptr,
            secure=self.protocol == "https",
            **authopts,
        )
