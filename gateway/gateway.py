"""
gateway.py - API Gateway (REST to TCP bridge)
sendToService() bridges HTTP to TCP.
getServiceAddress() does routing/service discovery.
All REST routes fully working.
"""

import socket
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from common.config import (
    GATEWAY_HOST, GATEWAY_PORT,
    RESTAURANT_SERVICE_MAP, BACKUP_MAP,
    REPLICATION_HOST,
)
from common.protocol import sendMessage, receiveMessage

logger = logging.getLogger(__name__)

#only when primary is alive; but not responsive;
PRIMARY_TIMEOUT = 3.0


BACKUP_TIMEOUT  = 10.0


def sendToService(host, port, message, timeout=BACKUP_TIMEOUT):
    """Bridge from HTTP to TCP.

    Opens a TCP connection to the target service, sends the message using the
    shared newline-framed protocol, returns parsed response dict.
    The caller controls the timeout so primary and backup attempts can use
    different values (see sendToServiceWithFailover).
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sendMessage(sock, message)
        response = receiveMessage(sock)
        sock.close()
        return response
    except (ConnectionRefusedError, socket.timeout, OSError) as e:
        logger.error(f"Service at {host}:{port} unreachable: {e}")
        return {"status": "error", "message": f"Service unavailable: {e}"}


def sendToServiceWithFailover(host, port, message):
    """Try primary first with a short timeout; fall over to backup on failure.

    Using PRIMARY_TIMEOUT (3s) for the primary probe means a dead primary is
    detected quickly.  The total worst-case client delay after a primary death
    is PRIMARY_TIMEOUT + BACKUP_TIMEOUT = 13s, which is acceptable for this demo but could be improved in a production system
    """
    response = sendToService(host, port, message, timeout=PRIMARY_TIMEOUT)
    if response.get("status") == "error" and "unavailable" in response.get("message", ""):
        backup_port = BACKUP_MAP.get(port)
        if backup_port is not None:
            logger.warning(
                f"Primary {host}:{port} unavailable — retrying on backup port {backup_port}"
            )
            response = sendToService(REPLICATION_HOST, backup_port, message, timeout=BACKUP_TIMEOUT)
    return response


def getServiceAddress(restaurant_id):
    """Routing/service discovery. Looks up host and port from RESTAURANT_SERVICE_MAP in config."""
    return RESTAURANT_SERVICE_MAP.get(restaurant_id)


class GatewayHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        logger.info(f"HTTP {args[0]}")

    def _sendJson(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def _readBody(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(content_length).decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # GET /restaurants
        if path == "/restaurants":
            restaurants = []
            for rid, (host, port) in RESTAURANT_SERVICE_MAP.items():
                resp = sendToServiceWithFailover(host, port, {"action": "get_info"})
                if resp.get("status") == "ok":
                    restaurants.append({
                        "restaurant_id": rid,
                        "name": resp.get("name", ""),
                        "cuisine": resp.get("cuisine", ""),
                        "address": resp.get("address", ""),
                        "menu_url": resp.get("menu_url", ""),
                        "description": resp.get("description", ""),
                        "price_range": resp.get("price_range", ""),
                        "rating": resp.get("rating", 0),
                        "features": resp.get("features", []),
                        "tables": resp.get("tables", {}),
                        "timeslots": resp.get("timeslots", []),
                    })
            self._sendJson(200, {"restaurants": restaurants})

        # GET /restaurants/<id>/availability
        elif "/availability" in path:
            rid = path.split("/")[2]
            addr = getServiceAddress(rid)
            if not addr:
                self._sendJson(404, {"error": f"Restaurant '{rid}' not found"})
                return
            resp = sendToServiceWithFailover(addr[0], addr[1], {
                "action": "check_availability",
                "date": query.get("date", [""])[0],
                "timeslot": query.get("timeslot", [""])[0],
                "party_size": int(query.get("party_size", [1])[0]) if str(query.get("party_size", [1])[0]).isdigit() else 1,
            })
            self._sendJson(200, resp)

        # GET /restaurants/<id>
        elif path.startswith("/restaurants/"):
            rid = path.split("/")[2]
            addr = getServiceAddress(rid)
            if not addr:
                self._sendJson(404, {"error": f"Restaurant '{rid}' not found"})
                return
            resp = sendToServiceWithFailover(addr[0], addr[1], {"action": "get_info"})
            self._sendJson(200, resp)

        # GET /reservations/<restaurant_id>
        elif path.startswith("/reservations/"):
            rid = path.split("/")[2]
            addr = getServiceAddress(rid)
            if not addr:
                self._sendJson(404, {"error": f"Restaurant '{rid}' not found"})
                return
            resp = sendToServiceWithFailover(addr[0], addr[1], {
                "action": "list_reservations",
                "date": query.get("date", [None])[0],
            })
            self._sendJson(200, resp)

        else:
            self._sendJson(404, {"error": "Not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._readBody()
        # Return 400 if body is not valid JSON or is missing entirely.
        if body is None:
            self._sendJson(400, {"error": "Invalid JSON body"})
            return

        # POST /reservations
        if path == "/reservations":
            rid = body.get("restaurant_id")
            if not rid:
                self._sendJson(400, {"error": "restaurant_id is required"})
                return
            addr = getServiceAddress(rid)
            if not addr:
                self._sendJson(404, {"error": f"Restaurant '{rid}' not found"})
                return
            resp = sendToServiceWithFailover(addr[0], addr[1], {
                "action": "book",
                "table_id": body.get("table_id"),
                "date": body.get("date"),
                "timeslot": body.get("timeslot"),
                "customer_name": body.get("customer_name"),
                "party_size": body.get("party_size", 1),
                "contact": body.get("contact", ""),
            })
            status = 200 if resp.get("status") == "ok" else 409
            self._sendJson(status, resp)

        else:
            self._sendJson(404, {"error": "Not found"})

    def do_DELETE(self):
        path = urlparse(self.path).path
        body = self._readBody()

        if body is None:
            self._sendJson(400, {"error": "Invalid JSON body"})
            return

        if path == "/reservations":
            rid = body.get("restaurant_id")
            if not rid:
                self._sendJson(400, {"error": "restaurant_id is required"})
                return
            addr = getServiceAddress(rid)
            if not addr:
                self._sendJson(404, {"error": f"Restaurant '{rid}' not found"})
                return
            resp = sendToServiceWithFailover(addr[0], addr[1], {
                "action": "cancel",
                "table_id": body.get("table_id"),
                "date": body.get("date"),
                "timeslot": body.get("timeslot"),
            })
            status = 200 if resp.get("status") == "ok" else 400
            self._sendJson(status, resp)
        else:
            self._sendJson(404, {"error": "Not found"})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def startGateway():
    server = HTTPServer((GATEWAY_HOST, GATEWAY_PORT), GatewayHandler)
    logger.info(f"Gateway on http://{GATEWAY_HOST}:{GATEWAY_PORT}")
    server.serve_forever()