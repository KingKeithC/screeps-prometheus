from tap import Tap
import yaml
import os
import logging
from pathlib import Path
from typing import Optional, override

from screepsapi import API, Socket  # pyright: ignore[reportMissingTypeStubs]
from screeps_prometheus import LogCallback, ScreepsStats, StatScraper, from_json_or_yaml

logger = logging.getLogger(__name__)

class BasicAuth:
    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password

class TokenAuth:
    def __init__(self, token: str) -> None:
        self.token = token


def to_auth(string: str) -> BasicAuth | TokenAuth:
    fields = string.split(":")
    if (len(fields) == 2):
        return BasicAuth(username=fields[0], password=fields[1])
    elif (len(fields)== 1):
        return TokenAuth(token=string)
    raise ValueError(f"Unknown Kind of auth {string}")


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

    def configure(self) -> None:
        self.add_argument("--auth", type=to_auth) # type: ignore

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
        new = ScreepsConfig()
        new.auth = TokenAuth(token=token)
        return new

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
        print(f"Logged into Screeps as {me}")
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

    def get_console_watcher(self, api: API, with_each_log: LogCallback) -> ScreepsConsoleMonitor:
        return ScreepsConsoleMonitor(api, self, with_each_log)


class ScreepsConsoleMonitor(Socket):
    CONSOLE_WATCHPOINT = "console"

    def __init__(self, api: API, config: ScreepsConfig, log_callback: LogCallback) -> None:
        self.api = api
        self.config = config
        self.log_callback = log_callback

        if (isinstance(config.auth, TokenAuth)):
            super().__init__( # type: ignore
                ptr=config.ptr,
                logging=False,
                host=config.host,
                secure=True,
                token=config.auth.token
            )
        else:
            super().__init__( # type: ignore
                user=config.auth.username,
                password=config.auth.password,
                ptr=config.ptr,
                host=config.host,
                secure=True
            )

    @override
    def connect(self):  # type: ignore
        logger.info("Connecting to Screeps websocket at %s", self.config.host)
        super().connect()

    @override
    def on_error(self, ws, error):  # type: ignore
        logger.error("Screeps websocket error: %s", error)

    def on_open(self, ws): # type: ignore
        logger.info("Screeps websocket connected; authenticating")
        super().on_open(ws) # type: ignore
        self.subscribe_user(ScreepsConsoleMonitor.CONSOLE_WATCHPOINT) # type: ignore
        logger.info("Requested Screeps console subscription")

    @override
    def on_message(self, ws, message): # type: ignore
        if message.startswith("auth ok"):
            logger.info("Screeps websocket authentication succeeded")
        elif message.startswith("auth failed"):
            logger.error("Screeps websocket authentication failed")
        super().on_message(ws, message) # type: ignore

    @override
    def on_close(self, ws, close_status_code=None, close_msg=None): # type: ignore
        logger.info(
            "Screeps websocket closed (status=%r, reason=%r)",
            close_status_code,
            close_msg,
        )
        super().on_close(ws) # type: ignore

    @override
    def process_log(self, ws, message, shard='shard0'): # type: ignore
        self.log_callback(message)
