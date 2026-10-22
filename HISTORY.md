
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

## 26.1.0 (2026-10-22)

### Security
* Docker builds now bootstrap pip from the SHA-256-verified 26.2.2 wheel before upgrading to the latest release and creating a virtualenv without ensurepip. Runtime images remove the unused global pip and ensurepip bundle to prevent seeding environments with an outdated installer.

## 25.3.1 (2025-08-28)

### Fixed

* A loose call to .strip() removed data when the initial byte was formated as asccii space. This made the data 
  malformed when the data was of a certain length. Removed the .strip()-call and no issues anymore.

## 25.3.0 (2025-08-26)

### Fixed

* By inheriting from DatagramRequestHandler there was a hidden call to `socket.sendall()`
  This resulted in an empty packet being sent and older devices could not handle this. 
  By inheriting directly from BaseRequestHandler this was fixed.


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
