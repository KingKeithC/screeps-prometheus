
from dataclasses import dataclass
import json
from pathlib import Path

from screepsapi import API # pyright: ignore[reportMissingTypeStubs]

from screeps_prometheus import ScreepsStats, StatScraper


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
    shard: str = "shard3"

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

    def login(self) -> API:
        if isinstance(self.auth, TokenAuth):
            authopts = {"token": self.auth.token}
        else:
            authopts = {"u": self.auth.username, "p": self.auth.password}

        api = API(
            host=self.host,
            ptr=self.ptr,
            secure=self.protocol == "https",
            **authopts,
        )

        me: OrderedDict = api.me() # type: ignore
        print(f"Logged into Screeps as {me["email"]}")
        return api


    def get_stat_scraper(self, api: API) -> StatScraper:
        def inner() -> ScreepsStats | None:
            ret = api.memory(path="stats", shard=self.shard)

            if ret is None or len(ret) == 1:
                print(f"No stats exist")
                return None
            elif not ret["ok"]:
                raise Exception(f'Fetching Memory was not OK: {ret["ok"]}')

            return ret

        return inner
