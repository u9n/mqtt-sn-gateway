# mqtt-sn-gateway
An asyncio Python implementation of a MQTT-SN Gateway

## About

We built this since we needed a nice way to interface MQTT-SN devices into our data 
stream. It is not feature complete as we wrote it quite quick but we hope to add onto 
it as our need grows. We used a transparent gateway before we built this and once we 
got over 1000 devices we got problems with the underlying I/O implementation.
So this gateway is built as an aggregating gateway with multiple connections to the 
MQTT broker.

### Supported features

* CONNECT - In-memory store of clients
* REGISTER - In-memory store of registered topics in clients
* PUBLISH - Receive a PUBLISH and forward it to MQTT broker

### Not supported - yet!
* Gateway ADVERTISE
* LAST WILL and TESTAMENT
* QoS 2 and QoS-1
* SUBSCRIBE
* PINGREG/PINGRESP
* Encapsulated messages
* DTLS encryption
  

### Future work

We would like a Redis-backed client and topic store. This would make it possible to 
run several instances of the gateway with shared and persistent state for handling 
higher loads and services outages.

## Install

Requires Python 3.7 and higher (since we use asyncio and it is much nicer in 3.7+)

```
pip install mqtt-sn-gateway
```

## Run via CLI

After installing via pip you can run the server via the command `mqtt-sn-server`

```shell
mqtt-sn-gateway --help

>
Usage: mqtt-sn-gateway [OPTIONS]

  Will assume there is a .env file in the root of the package. This is for
  simple development. To use .env files as in production use the --env-file
  arg to specify path. To make force the application to discard all .env files
  use the --no-env-files flag.

Options:
  --debug          Enable debug logging
  --env-file TEXT  Path to .env file
  --no-env-files   Discard all use of .env files.
  --help           Show this message and exit.

```

## Run via Docker

You can pull the latest docker-image and run via docker if needed.

```shell
docker pull quay.io/u9n/mqtt-sn-gateway
```

## Settings

You can use either an .env file or environment variables to set up the gateway.

* HOST: str, Example 0.0.0.0 
* PORT: int, Port so serve the gateway. Ex 2883
* BROKER_HOST: str, Broker host, Ex: test.mosquitto.com
* BROKER_PORT: int, Borker port, Default=1883
* BROKER_CONNECTIONS: int: How many connections the gatewat should have to the broker, default=10
* BACK_PRESSURE_LIMIT: int: How many unhandled UDP-packets should be queued up before not receiving more traffic, Default=1000


## Extend

It is possible to implement your own client and topic stores. Just supply the 
gateway an object the follows the correct Protocol.

```python

class ClientStore(Protocol):
    def add_client(self, client: MqttSnClient) -> None:
        ...

    def get_client(self, remote_addr: Tuple[str, int]) -> Optional[MqttSnClient]:
        ...

    def delete_client(self, remote_addr: Tuple[str, int]) -> None:
        ...
    
    
class TopicStore(Protocol):
    def add_topic_for_client(self, client_id: bytes, topic_name: str) -> int:
        ...

    def get_topic_for_client(self, client_id: bytes, topic_id: int) -> Optional[str]:
        ...

```

## Contribute
We appreciate all contributions.  File a bug report or fix the issue yourself 
and submit a pull request.


## Commercial support or custom development
We at [Utilitarian](https://www.utilitarian.io) can help your company with integrating
the gateway to your systems. Contact us if you wish to speed up development or make 
sure your solution has long-term support.
