import attr
from typing import *


class TopicStore(Protocol):
    def add_topic_for_client(self, client_id: bytes, topic_name: str) -> int:
        ...

    def get_topic_for_client(self, client_id: bytes, topic_id: int) -> Optional[str]:
        ...


@attr.s()
class InMemoryTopicStore:
    # TODO: How to handle keep alive?
    topics_ids: Dict[bytes, Dict[int, str]] = attr.ib(factory=dict)
    topic_names: Dict[bytes, Dict[str, int]] = attr.ib(factory=dict)
    last_topic_ids: Dict[bytes, int] = attr.ib(factory=dict)

    def add_topic_for_client(self, client_id: bytes, topic_name: str) -> int:
        # is there a client?
        client_topics = self.topic_names.get(client_id, None)
        if client_topics is None:
            topic_id = self.get_new_topic_id(client_id)
            self.topic_names[client_id] = {topic_name: topic_id}
            self.topics_ids[client_id] = {topic_id: topic_name}
            return topic_id

        # what if there is a topic registed?
        current_topic_id = client_topics.get(topic_name, None)
        if current_topic_id is not None:
            return current_topic_id

        # No topic registed
        topic_id = self.get_new_topic_id(client_id)
        self.topic_names[client_id][topic_name] = topic_id
        self.topics_ids[client_id][topic_id] = topic_name
        return topic_id

    def get_topic_for_client(
        self, client_id: bytes, topic_id: int
    ) -> Optional[str]:
        client_topic_ids = self.topics_ids.get(client_id, None)
        if client_topic_ids is None:
            return None
        topic_name = client_topic_ids.get(topic_id, None)
        return topic_name

    def get_new_topic_id(self, client_id: bytes) -> int:
        last_topic_id = self.last_topic_ids.get(client_id, 1)
        new_last_topic_id = last_topic_id + 1
        self.last_topic_ids[client_id] = new_last_topic_id
        return last_topic_id
