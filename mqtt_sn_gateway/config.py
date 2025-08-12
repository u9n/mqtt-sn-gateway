from pathlib import Path
from typing import Optional
from attrs import define
import environ  # type: ignore


def format_env_path(env_file_path: str):
    if env_file_path.endswith(".env"):
        return env_file_path
    else:
        return env_file_path + ".env"

@define
class Config:
    HOST: str
    PORT: int
    USE_PORT_NUMBER_IN_CLIENT_STORE: bool
    EXTEND_STORE_TTL_ON_PUBLISH: bool
    AMQP_CONNECTION_STRING: str
    AMQP_PUBLISH_EXCHANGE: str
    VALKEY_CONNECTION_STRING: str
    SENTRY_DSN: Optional[str]

    def __init__(
            self, env_file_path: Optional[str] = None, no_env_files: Optional[bool] = False
    ):
        root_dir = Path(__file__).parents[1]
        env = environ.Env()

        if not no_env_files:
            file_path = env_file_path or Path.joinpath(root_dir, ".env")
            env.read_env(env_file=str(file_path))

        self.HOST = env.str("MQTTSN_HOST")
        self.PORT = env.int("MQTTSN_PORT")
        self.USE_PORT_NUMBER_IN_CLIENT_STORE = env.bool("MQTTSN_USE_PORT_NUMBER_IN_CLIENT_STORE")
        self.EXTEND_STORE_TTL_ON_PUBLISH = env.bool("MQTTSN_EXTEND_STORE_TTL_ON_PUBLISH", default=True)
        self.AMQP_CONNECTION_STRING = env.str("MQTTSN_AMQP_CONNECTION_STRING",
                                              default='amqp://guest:guest@localhost:5672//')
        self.AMQP_PUBLISH_EXCHANGE = env.str("MQTTSN_AMQP_PUBLISH_EXCHANGE", default='mqtt-sn')
        self.VALKEY_CONNECTION_STRING = env.str("MQTTSN_VALKEY_CONNECTION_STRING", default='valkey://localhost:6379/0')
        self.SENTRY_DSN = env.str("MQTTSN_SENTRY_DSN", default=None)
