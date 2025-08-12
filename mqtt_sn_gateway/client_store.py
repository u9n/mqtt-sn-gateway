from typing import Tuple, Protocol

from attrs import define
import valkey
import structlog

LOG = structlog.get_logger(__name__)

CLIENT_TTL = 60 * 60 * 24 * 7  # 7 days in seconds


class ClientDoesNotExist(Exception):
    """Client does not exist in store"""

class ConnectionError(Exception):
    """Unable to connect to client store"""

class ClientStore(Protocol):

    use_port_number: bool
    def add_client(self, client_id: bytes, remote_addr: Tuple[str, int]) -> None:
        """
        :raises ClientStoreConnectionError: Unable to connect to client store.
        """
        ...

    def get_client(self, remote_addr: Tuple[str, int]) -> bytes:
        """
        :raises ClientDoesNotExist: Client does not exist in store.
        :raises ClientStoreConnectionError: Unable to connect to client store.

        """
        ...

    def delete_client(self, remote_addr: Tuple[str, int]) -> None:
        """
        :raises ClientStoreConnectionError: Unable to connect to client store.
        """
        ...

    def extend_client_ttl(self, remote_addr: Tuple[str, int]) -> None:
        """
        :raises ClientStoreConnectionError: Unable to connect to client store.
        """


@define
class ValKeyClientStore:
    """
    Stores clients in valkey

    Keyname for data is "client:ip_address:port",

    """
    valkey: valkey.Valkey
    use_port_number: bool

    def key_from_remote_addr(self, remote_addr: Tuple[str, int]) -> str:
        if self.use_port_number:
            return f"client:{remote_addr[0]}:{remote_addr[1]}"
        else:
            return f"client:{remote_addr[0]}"

    def add_client(self, client_id: bytes, remote_addr: Tuple[str, int]) -> None:
        try:
            key = self.key_from_remote_addr(remote_addr)
            LOG.debug(f"Adding client", client_id=client_id, remote_addr=remote_addr, key=key, ttl=CLIENT_TTL)
            self.valkey.set(name=key, value=client_id, ex=CLIENT_TTL)
        except valkey.exceptions.ConnectionError as e:
            LOG.error(f"Connection error when adding client", client_id=client_id, remote_addr=remote_addr)
            raise ConnectionError("Unable to connect to client store") from e

    def get_client(self, remote_addr: Tuple[str, int]) -> bytes:
        """
        :raises ClientDoesNotExist: Client does not exist in store
        """
        try:

            client_id = self.valkey.get(name=self.key_from_remote_addr(remote_addr))
            if client_id is None:
                LOG.error(f"Client does not exist in store", remote_addr=remote_addr)
                raise ClientDoesNotExist(f"No such client")
            return client_id

        except valkey.exceptions.ConnectionError as e:
            LOG.error(f"Connection error to client store when getting client data", remote_addr=remote_addr, store=self)
            raise ConnectionError("Unable to connect to client store") from e


    def delete_client(self, remote_addr: Tuple[str, int]) -> None:
        try:
            LOG.debug(f"Deleting client", remote_addr=remote_addr)
            self.valkey.delete(self.key_from_remote_addr(remote_addr))
        except valkey.exceptions.ConnectionError as e:
            LOG.error(f"Connection error to client store when deleting client", remote_addr=remote_addr, store=self)
            raise ConnectionError("Unable to connect to client store") from e

    def extend_client_ttl(self, remote_addr: Tuple[str, int]) -> None:
        try:
            LOG.debug(f"Extending client TTL", remote_addr=remote_addr)
            self.valkey.expire(name=self.key_from_remote_addr(remote_addr), time=CLIENT_TTL)
        except valkey.exceptions.ConnectionError as e:
            LOG.error(f"Connection error to client store when extending client", remote_addr=remote_addr, store=self)
            raise ConnectionError("Unable to connect to client store") from e
