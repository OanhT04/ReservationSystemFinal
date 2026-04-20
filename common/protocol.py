"""
Internal service communication uses this protocol
Messages are JSON dicts terminated by Newline char
"""

import socket
import json

ENCODING = "utf-8"


def sendMessage(sock: socket.socket, message: dict):
    data = (json.dumps(message) + "\n").encode(ENCODING)
    sock.sendall(data)


def receiveMessage(sock: socket.socket) -> dict:
    buffer = ""
    while True:
        chunk = sock.recv(4096).decode(ENCODING)
        if not chunk:
            raise ConnectionError("Connection closed")
        buffer += chunk
        if "\n" in buffer:
            message, _ = buffer.split("\n", 1)
            return json.loads(message)


def createRequest(action: str, **kwargs) -> dict:
    msg = {"action": action}
    msg.update(kwargs)
    return msg


def createResponse(status: str, **kwargs) -> dict:
    msg = {"status": status}
    msg.update(kwargs)
    return msg
