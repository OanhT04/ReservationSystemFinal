# Reservation Service

A distributed restaurant reservation system built for **CECS 327: Introduction to Networks and Distributed Computing** at California State University, Long Beach.

This project demonstrates core distributed systems concepts including network communication, concurrency control, replication, fault tolerance, logical time, and service coordination. The system supports multiple independent restaurant services coordinated through a central API gateway.

## Overview

Reservation systems must handle many clients attempting to book tables at the same time while preventing double bookings and preserving confirmed reservations during failures. This project implements a distributed reservation service that addresses these challenges through sharding, per-table locking, synchronous replication, and heartbeat-based failover.

The system supports six independent restaurants, each running as its own service instance with separate memory, locks, and backup node. A central API gateway receives client requests and routes them to the correct restaurant service.

<img width="1592" height="1188" alt="image" src="https://github.com/user-attachments/assets/566e0aa4-4dae-46e3-ad32-a5027b77445a" />

## Key Features

- REST-based client-facing API through a central gateway
- Internal TCP socket communication between services
- Six independent restaurant service instances
- Per-table locking to prevent double bookings
- Synchronous primary-backup replication
- Heartbeat-based failure detection
- Automatic backup promotion after primary failure
- Lamport clocks for ordering write events
- Sharding by restaurant ID for horizontal scalability
- Gateway-level routing, protocol translation, and retry logic

## System Architecture

The system follows a layered client-server architecture with three main tiers:

### Client Tier

The client provides an interactive user interface that allows users to browse restaurants, check availability, make reservations, and cancel bookings.

### Gateway Tier

The API gateway acts as the single entry point for client requests. It runs as an HTTP server and translates external REST requests into internal TCP messages.

Responsibilities include:

- Accepting HTTP requests from clients
- Routing requests to the correct restaurant service
- Translating HTTP communication into TCP messages
- Performing service discovery through a static configuration registry
- Retrying requests when failover occurs

### Service Tier

Each restaurant runs as an independent service instance with its own:

- Primary server
- Backup server
- In-memory reservation data
- Per-table locks
- Heartbeat mechanism
- Replication logic

This design allows traffic for one restaurant to remain isolated from traffic for another.

## Distributed Systems Concepts Demonstrated

### 1. Concurrency Control

The system uses per-table locking to ensure that two clients cannot reserve the same table at the same time.

Instead of locking the entire restaurant service, the system locks only the specific table being booked. This allows reservations for different tables to proceed concurrently while still preventing double bookings.

### 2. Synchronous Replication

Each restaurant service uses a primary-backup replication model. Before a booking is confirmed to the client, the primary server sends the update to the backup and waits for an acknowledgment.

This ensures that every confirmed reservation exists on both the primary and backup nodes.

### 3. Fault Tolerance

The backup server monitors the primary using a heartbeat protocol. If the backup does not receive heartbeats for a set period of time, it assumes the primary has failed and automatically promotes itself.

This allows the system to continue serving clients even after a primary server failure.

### 4. Sharding

The system is horizontally scaled by restaurant ID. Each restaurant runs as its own independent service instance.

Adding a new restaurant requires:

1. Adding a new entry to the configuration file
2. Starting a new restaurant service process

Existing restaurant services are not affected.

### 5. Logical Time

Lamport clocks are used to maintain a total order of write events within each service. This helps preserve ordering across replicated operations and failover scenarios.

### 6. Network Communication

The system uses two forms of communication:

- HTTP REST communication between the client and gateway
- TCP socket communication between the gateway and restaurant services

TCP is used internally because it provides reliable, ordered delivery, which is important for replication correctness.

## Technologies Used

- Python
- Flask / HTTP REST API
- TCP sockets
- Threading / concurrency control
- JSON-based storage
- Lamport clocks
- Primary-backup replication
- Heartbeat-based failure detection


#### Limitations
Currently, data is stored in memory and JSON files rather than a production database, so a real system would need stronger persistence and ACID transaction guarantees. The system also uses a two-node primary-backup design instead of a three-node consensus-based approach such as Paxos or Raft, which limits safe leader election and recovery. The API gateway is currently a single point of failure. In a production system, this would be addressed by running multiple gateway instances behind a load balancer so that if one gateway fails, traffic can automatically be routed to another healthy instance. Additional monitoring and health checks would be used to detect failed gateway nodes and remove them from rotation.

## Project Structure

```text
reservation-service/
├── client/
│   └── client interface files
├── gateway/
│   └── API gateway and routing logic
├── services/
│   └── restaurant service instances
├── config.py
│   └── static service registry
├── data/
│   └── reservation storage files
└── README.md


