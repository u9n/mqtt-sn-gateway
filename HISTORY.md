
# Changelog
All notable changes to this project will be documented in this file.


The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Calendar Versioning](https://calver.org/)

## Unreleased



### Changed

### Deprecated

### Removed

### Fixed

### Security

## 25.2.0 (2025-08-12)

### Added

* Extending store ttl by default on publish.
* Added EXTEND_STORE_TTL_ON_PUBLISH setting with default `True`

## 25.1.0

* Reimplemention on sync-IO. 
* Removed the need to MQTT Broker and just runs on AMQP for data forwarding
* Valkey based client and topic store

## 21.0.0 [2021-07-07]


Initial implementation.
