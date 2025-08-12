# mqtt-sn-gateway
An opinionated Python implementation of a MQTT-SN Gateway

## About
This MQTT-SN Gateway was created to collect meter data from Elvaco CMi6110 communication modules, and other Elvaco
metering products that support sending meter data via MQTT-SN.

This is not a full MQTT-SN implementation and does not aim to be. In previous iterations we used RabbitMQ with the 
mqtt plugin as the MQTT broker. But in later releases we removed the need to run an MQTT Broker at all and there is 
only need for an AMQP Broker like RabbitMQ. We where using the MQTT/AMQP translation feature in RabbitMQ but realied 
that we might as well not use the MQTT part at all and send everything directly on AMQP.

The server uses Valkey as Client Store and Topic Store. This means each instance is not depending on any internal state
and can be put behind a load balancer.

### Supported features

* CONNECT 
* REGISTER 
* PUBLISH 
* PINGREQ

### Not supported.
* DTLS encryption - This should be done in some form of reverse proxy setup and not in this application.

## Run the server

The server can be run like:

```
python mqtt_sn_gateway/main.py
```

## Install

Clone the repo and install locally using `-e`

```
pip install -e .
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
  --json-logs      Outputs logs in JSON-format
  --help           Show this message and exit.


```

## Settings

You can use either an .env file or environment variables to set up the gateway.

* MQTTSN_HOST: str, Example 0.0.0.0 
* MQTTSN_PORT: int, Port so serve the gateway. Ex 2883
* MQTTSN_USE_PORT_NUMBER_IN_CLIENT_STORE: bool. use port number in client store key
* MQTTSN_EXTEND_STORE_TTL_ON_PUBLISH: bool, default: true. 
* MQTTSN_AMQP_CONNECTION_STRING: str, default: amqp://guest:guest@localhost:5672//
* MQTTSN_AMQP_PUBLISH_EXCHANGE: str, default: mqtt-sn
* MQTTSN_VALKEY_CONNECTION_STRING: str: default: valkey://localhost:6379/0
* MQTTSN_SENTRY_DSN: str: default=None

The following is not supported in .env file:

* MQTTSN_DEBUG: bool, enables debug logging
* MQTTSN_ENV_FILE: str, path to env file
* MQTTSN_NO_ENV_FILES: bool, discard all use of env files
* MQTTSN_JSON_LOGS: bool, outputs structured logs in json format

## Running behind a NAT

If you have a NAT between the devices and the MQTT-SN Gateway it might be that incoming UDP-messages have the same IP.
The NAT will use a certain port number to be able to map responses back to the device. We need to activate the setting 
`MQTTSN_USE_PORT_NUMBER_IN_CLIENT_STORE` so that the key in the client store looks like `client:{ip}:{port}`.
It is also important that the timeout for port assignment is high enough for your use case so that the NAT does not 
remove the mapping when there is no messages being sent. If the mapping is removed the next message will get a new port 
and the client will not be found in the client store. Which will result in a DISCONNECT and the device have to reconnect 
and register again in the gateway. This causes more traffic and will also drain the battery of the device more than 
necessary if battery operated.

## Commercial support or custom development
This software is not fully open source. It uses a source available, non-compete license which allows you or your 
company to use the program for your own use. Using it in a commercial offering to others is not allowed and you will 
need another license granted to you.

We at [Utilitarian](https://www.utilitarian.io) offer support contracts and can help your company with integrating
the gateway to your systems. Contact us if you wish to speed up development or make 
sure your solution has long-term support.
