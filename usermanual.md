# User Manual

**How to Install and Execute**

To install, clone or download the repository to run. To execute the reservation system itself, open two separate terminals. In the first terminal, start the server using the command python run_all.py. In the second terminal, start the client with the command python client.py. clients require the server to be running as the client connects to the gateway to present the main menu. To stop the system, press Ctrl+C in the server (first) terminal to terminate both terminals. To run the automated tests, use the command python run_tests.py, the server does not need to be running in order to run the tests.

**System Functionality**

This distributed restaurant reservation system allows users (clients) to look at restaurants by cuisine, reserve a table at a restaurant, and to manage any existing reservations they may have. This system is useful not only for restaurants that require a reservation system, but also helps customers make reservations smoothly in advance. 

Request Handling

Our system implements a primary-backup replication, meaning that when the client sends a HTTP request to the gateway, the gateway looks up the requested restaurant in RESTAURANT_SERVICE_MAP and opens a TCP connection to the primary and sends a message. The primary then writes and replicates to the backup, and then the response is sent back to the client via the gateway. 

Events Ordering and Consistency

In our system, we implemented Lamport clocks that timestamp all reservations made and per-table locks with timeouts. This ensures that the backup is updated with new writes from the primary, and that casual ordering is still intact, meaning that two users can not reserve the same table at the same time.

Failures

To address failures, the primary heartbeats (pings) the backup every 2 seconds to ensure to the backup that the primary still works. However, if there is no heartbeat ping from the primary after 6 seconds, then the backup promotes itself, ensuring users don't notice the failover. 
