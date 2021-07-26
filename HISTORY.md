
# Changelog
All notable changes to this project will be documented in this file.


The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Calendar Versioning](https://calver.org/)

## Unreleased


### Added

* Unsupported QoS in publish will result in PUBACK with return code NOT_SUPPORTED.

### Changed

* Made client and topic store Protocols use async methods.
* Using the QoS of MQTT-SN message when publishing to MQTT.

### Deprecated

### Removed

### Fixed

* If a client is not found in the client store the gateway responds with a DISCONNECT.

### Security


## 21.0.0 [2021-07-07]


Initial implementation.
