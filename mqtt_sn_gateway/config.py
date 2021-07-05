from pathlib import Path
from typing import Optional

import environ


def format_env_path(env_file_path: str):
    if env_file_path.endswith(".env"):
        return env_file_path
    else:
        return env_file_path + ".env"


class Config:
    HOST: str
    PORT: int
    BROKER_HOST: str
    BROKER_PORT: int
    BROKER_CONNECTIONS: int
    BACK_PRESSURE_LIMIT: int



    def __init__(
        self, env_file_path: Optional[str] = None, no_env_files: Optional[bool] = False
    ):
        root_dir = Path(__file__).parents[1]
        env = environ.Env()

        if not no_env_files:
            file_path: str = env_file_path or Path.joinpath(root_dir, ".env")
            env.read_env(env_file=str(file_path))

        self.HOST = env.str("HOST")
        self.PORT = env.int("PORT")
        self.BROKER_HOST = env.str("BROKER_HOST")
        self.BROKER_PORT = env.int("BROKER_PORT", default=1883)
        self.BROKER_CONNECTIONS = env.int("BROKER_CONNECTIONS", default=10)
        self.BACK_PRESSURE_LIMIT = env.int("BACK_PRESSURE_LIMIT", default=1000)





