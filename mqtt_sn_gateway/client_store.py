from typing import Dict, Tuple, Protocol

from mqtt_sn_gateway.common import MqttSnClient
from attrs import define, field
import valkey
import structlog

LOG = structlog.get_logger(__name__)

CLIENT_TTL = 60 * 60 * 24 * 7  # 7 days in seconds


class ClientDoesNotExist(Exception):
    """Client does not exist in store"""


class ClientStore(Protocol):
    def add_client(self, client_id: bytes, remote_addr: Tuple[str, int]) -> None:
        ...

    def get_client(self, remote_addr: Tuple[str, int]) -> bytes:
        """
        :raises ClientDoesNotExist: Client does not exist in store
        """
        ...

    def delete_client(self, remote_addr: Tuple[str, int]) -> None:
        ...


@define
class ValKeyClientStore:
    """
    Stores clients in valkey

    Keyname for data is "client:ip_address:port",

    """
    valkey: valkey.Valkey

    @staticmethod
    def key_from_remote_addr(remote_addr: Tuple[str, int]) -> str:
        return f"client:{remote_addr[0]}:{remote_addr[1]}"

    def add_client(self, client_id: bytes, remote_addr: Tuple[str, int]) -> None:
        key = self.key_from_remote_addr(remote_addr)
        LOG.debug(f"Adding client", client_id=client_id, remote_addr=remote_addr, key=key, ttl=CLIENT_TTL)
        self.valkey.set(name=key, value=client_id, ex=CLIENT_TTL)

    def get_client(self, remote_addr: Tuple[str, int]) -> bytes:
        """
        :raises ClientDoesNotExist: Client does not exist in store
        """
        client_id = self.valkey.get(name=self.key_from_remote_addr(remote_addr))
        if client_id is None:
            raise ClientDoesNotExist(f"No such client")
        return client_id

    def delete_client(self, remote_addr: Tuple[str, int]) -> None:
        self.valkey.delete(self.key_from_remote_addr(remote_addr))
