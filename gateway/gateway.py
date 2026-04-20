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
    RESTAURANT_SERVICE_MAP
)
from common.protocol import sendMessage, receiveMessage

logger = logging.getLogger(__name__)


def sendToService(host, port, message):
    """Bridge from HTTP to TCP. Opens TCP connection to correct service and forwards request."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10.0)
        sock.connect((host, port))
        sendMessage(sock, message)
        response = receiveMessage(sock)
        sock.close()
        return response
    except (ConnectionRefusedError, socket.timeout, OSError) as e:
        logger.error(f"Service at {host}:{port} unreachable: {e}")
        return {"status": "error", "message": f"Service unavailable: {e}"}


def getServiceAddress(restaurant_id):
    """Routing/service discovery. Uses restaurant service map from config."""
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
        return json.loads(self.rfile.read(content_length).decode())

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # GET /restaurants
        if path == "/restaurants":
            restaurants = []
            for rid, (host, port) in RESTAURANT_SERVICE_MAP.items():
                resp = sendToService(host, port, {"action": "get_info"})
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
            resp = sendToService(addr[0], addr[1], {
                "action": "check_availability",
                "date": query.get("date", [""])[0],
                "timeslot": query.get("timeslot", [""])[0],
                "party_size": int(query.get("party_size", [1])[0]),
            })
            self._sendJson(200, resp)

        # GET /restaurants/<id>
        elif path.startswith("/restaurants/"):
            rid = path.split("/")[2]
            addr = getServiceAddress(rid)
            if not addr:
                self._sendJson(404, {"error": f"Restaurant '{rid}' not found"})
                return
            resp = sendToService(addr[0], addr[1], {"action": "get_info"})
            self._sendJson(200, resp)

        # GET /reservations/<restaurant_id>
        elif path.startswith("/reservations/"):
            rid = path.split("/")[2]
            addr = getServiceAddress(rid)
            if not addr:
                self._sendJson(404, {"error": f"Restaurant '{rid}' not found"})
                return
            resp = sendToService(addr[0], addr[1], {
                "action": "list_reservations",
                "date": query.get("date", [None])[0],
            })
            self._sendJson(200, resp)

        else:
            self._sendJson(404, {"error": "Not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._readBody()

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
            resp = sendToService(addr[0], addr[1], {
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

        if path == "/reservations":
            rid = body.get("restaurant_id")
            addr = getServiceAddress(rid)
            if not addr:
                self._sendJson(404, {"error": f"Restaurant '{rid}' not found"})
                return
            resp = sendToService(addr[0], addr[1], {
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
