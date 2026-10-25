
from dataclasses import dataclass
import json
from tap import Tap
import yaml
import os
from pathlib import Path
from typing import Optional

from screepsapi import API  # pyright: ignore[reportMissingTypeStubs]

from screeps_prometheus import ScreepsStats, StatScraper, from_json_or_yaml




@dataclass
class BasicAuth:
    username: str
    password: str

@dataclass
class TokenAuth:
    token: str

# TODO: Align with https://github.com/screepers/screepers-standards/blob/master/SS3-Unified_Credentials_File.md
class ScreepsConfig(Tap):
    auth: BasicAuth | TokenAuth
    host: str = "screeps.com"
    port: int = 443
    path: str = "/"
    branch: str = "main"
    ptr: bool = False
    protocol: str = "https"
    shard: str = "shard3"

    ENV_SCREEPS_CONFIG = "SCREEPS_CONFIG"

    def __add__(self, other: ScreepsConfig | None):
        if other is None: return self
        dictme = self.as_dict()
        dictthem = self.as_dict()
        dictme.update(dictthem)
        dictus: ScreepsConfig = self.from_dict(dictme)
        return dictus

    def to_file(self, path: Path, clobber: bool = False):
        if path.is_file() and not clobber:
            raise FileExistsError(f"{path=} exists but {clobber=}")

        with path.open('w') as fh:
            yaml.dump(self, fh)

    @staticmethod
    def from_standard_locations() -> Optional[ScreepsConfig]:
        if (config := ScreepsConfig.from_env()) is not None:
            return config

        for search in [
            "project/.screeps.yaml"                # 1. Project Root
            "./.screeps.yaml"                      # 2. Current Working Directory
            "$XDG_CONFIG_HOME/screeps/config.yaml" # 3. XDG Config Directory
            "$HOME/.config/screeps/config.yaml"    # 4. XDG Config Default Directory
            "%APPDATA%/screeps/config.yaml"        # 5. APPDATA (Windows Only)
            "~/.screeps.yaml"                      # 6. Home Directory
        ]:
            file = Path(os.path.expandvars(search))
            if (config := ScreepsConfig.from_file(file)) is not None:
                return config

        return None

    @staticmethod
    def from_env() -> Optional[ScreepsConfig]:
        if ((filePath := os.environ.get(ScreepsConfig.ENV_SCREEPS_CONFIG, None)) is not None):
            return ScreepsConfig.from_file(Path(filePath))

        # raise EnvironmentError(f"{ScreepsConfig.ENV_SCREEPS_CONFIG} is not defined!")
        return None


    @staticmethod
    def from_token(token: str) -> ScreepsConfig:
        return ScreepsConfig(auth=TokenAuth(token=token))

    @staticmethod
    def from_file(path: Path) -> Optional[ScreepsConfig]:
        if not path.is_file():
            # raise FileNotFoundError(path)
            return None

        vals = from_json_or_yaml(path)
        if not isinstance(vals, dict): return None

        return ScreepsConfig(
            **vals, # type: ignore
            auth=TokenAuth(vals["token"]) if vals["token"] else BasicAuth(username=vals["username"], password=vals["password"]), # type: ignore
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
