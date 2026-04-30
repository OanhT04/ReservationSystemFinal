"""
Internal service communication uses this protocol.
Messages are JSON dicts terminated by a newline character (\n).

Framing rule: every message is exactly one JSON object followed by \n.
sendMessage()   — serialises dict → JSON + \n, sends atomically via sendall().
receiveMessage() — loops on recv() until a \n arrives, then parses the first
                complete line.  
"""

import socket
import json

from common.config import BUFFER_SIZE, ENCODING


def sendMessage(sock: socket.socket, message: dict):
    # Append newline as the message delimiter before sending.
    data = (json.dumps(message) + "\n").encode(ENCODING)
    sock.sendall(data)


def receiveMessage(sock: socket.socket) -> dict:
    """
    Read bytes from sock until a newline delimiter is found, then parse the
    JSON object that precedes it.
    """
    buffer = ""
    while "\n" not in buffer:
        # Keep reading until we have at least one complete message.
        chunk = sock.recv(BUFFER_SIZE).decode(ENCODING)
        if not chunk:
            raise ConnectionError("Connection closed before a complete message arrived")
        buffer += chunk

    # Split off exactly the first complete message; leave any trailing bytes
    # (a second message arriving early) untouched in the discarded tail.
    message, _ = buffer.split("\n", 1)
    return json.loads(message)


def createRequest(action: str, **kwargs) -> dict:
    """
    Create a request message with the specified action and additional keyword arguments.
    """
    msg = {"action": action}
    msg.update(kwargs)
    return msg


def createResponse(status: str, **kwargs) -> dict:
    """
    Create a response message with the specified status and additional keyword arguments.
    """
    msg = {"status": status}
    msg.update(kwargs)
    return msg