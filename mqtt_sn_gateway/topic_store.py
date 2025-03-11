from attrs import define, field
from typing import *
import structlog
import valkey

LOG = structlog.get_logger(__name__)


class TopicDoesNotExist(Exception):
    """No such topic"""


class TopicStore(Protocol):
    def add_topic_for_client(self, client_id: bytes, topic_name: str) -> int:
        ...

    def get_topic_for_client(self, client_id: bytes, topic_id: int) -> str:
        """
        :raises TopicDoesNotExist: Incase no topic exists
        """
        ...

    def delete_all_topics(self, client_id: bytes) -> None:
        """
        On clean session all topics should be erased.
        """


@define
class ValKeyTopicStore:
    valkey: valkey.Valkey

    @staticmethod
    def build_key(client_id: bytes) -> str:
        return f"topic:{client_id.decode()}"

    def add_topic_for_client(self, client_id: bytes, topic_name: str) -> int:
        """
        Uses ValKey list to store topics. the list index is the topic id.
        """
        key = self.build_key(client_id)
        LOG.debug("Adding topic for client", key=key, client_id=client_id, topic_name=topic_name)
        index = self.valkey.rpush(key, topic_name)
        LOG.debug("Topic register for client", key=key, client_id=client_id, topic_name=topic_name, topic_id=index)
        return index

    def get_topic_for_client(self, client_id: bytes, topic_id: int) -> bytes:
        """
        Get list item by index, index is the topic_id
        """
        key = self.build_key(client_id)
        topic_index = topic_id - 1
        LOG.debug("Requesting topic name for topic id", client_id=client_id, topic_index=topic_index, topic_id=topic_id)
        result = self.valkey.lindex(key, topic_index)
        if isinstance(result, tuple):
            topic = result[0]
        else:
            topic = result
        if topic is None:
            raise TopicDoesNotExist()

        LOG.debug("Retrieved topic name for topic id", client_id=client_id, topic_index=topic_index, topic_id=topic_id,
                  topic_name=topic)

        return topic

    def delete_all_topics(self, client_id: bytes) -> None:
        key = self.build_key(client_id)
        LOG.debug("Deleting all topics for client", key=key, client_id=client_id)
        self.valkey.delete(key)
