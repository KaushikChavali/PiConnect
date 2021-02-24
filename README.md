# PiConnect

## IDP
Development of an intelligent sensor system for monitoring battery storages

## Overview
A wireless control application to perform remote sensor measurements on an evaluation board.

GNU GPLv3.0 Licence, Copyright (C) 2021  Kaushik Chavali

<img src="https://github.com/KaushikChavali/PiConnect/blob/main/screens/PiConnect.png?raw=true" alt="PiConnectv2 GUI">

## Features
- Client-server model
- Pure Python codebase and Modular Architecture
- Auto-discovery of Raspberry Pi on the local network
- Auto-detection of connected sensors over the network
- Remote initiation of measurements from multiple sensors
- Synchronization of data files over the network
- Real-time event log
- Supports dual-connection modes
- Cross-platform support

## Requirements
Python >= 3.0

### Client-side
* Matplotlib
* Numpy
* Paramiko
* scp

### Server-side
* PySerial 3.5

## Usage

### Client-side

#### Packages
* client.py

To run the application of the client.

```console
$ python3 client.py
```

### Server-side

#### Packages
* server.py
* helper.py
* calibrate.py
* capture.py
* plot.py

To start the server on the evaluation board.

```console
$ python3 server.py
```
