"""Bearer and origin checks for shared MCP across transports."""

import unittest

from starlette.testclient import TestClient

from mcp_access import protected_mcp_app
from mcp_server import mcp


class McpAccessTests(unittest.TestCase):
    def test_remote_bind_requires_explicit_token_tls_and_public_origin(self):
        with self.assertRaisesRegex(ValueError, "MONROE_MCP_TOKEN"):
            protected_mcp_app(mcp, "streamable-http", "0.0.0.0", "")
        with self.assertRaisesRegex(ValueError, "direct TLS"):
            protected_mcp_app(mcp, "streamable-http", "0.0.0.0", "t" * 32, "https://mcp.example.com")

    def test_shared_http_rejects_every_unauthenticated_transport_request(self):
        origin = "https://mcp.example.com"
        token = "t" * 32
        auth = {"Authorization": f"Bearer {token}"}
        initialize = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"},
        }}
        for transport, path in (("streamable-http", "/mcp"), ("sse", "/sse")):
            with TestClient(protected_mcp_app(mcp, transport, "127.0.0.1", token, origin), base_url=origin) as client:
                for method in ("GET", "POST", "DELETE"):
                    denied = client.request(method, path)
                    self.assertEqual(denied.status_code, 401)
                    self.assertEqual(denied.headers["www-authenticate"], "Bearer")
                self.assertEqual(client.get(path, headers={**auth, "Origin": "https://bad.example"}).status_code, 403)
                self.assertEqual(client.get(path, headers={**auth, "Host": "bad.example"}).status_code, 403)
                if transport == "streamable-http":
                    response = client.post(path, json=initialize,
                                           headers={**auth, "Accept": "application/json, text/event-stream"})
                    self.assertEqual(response.status_code, 200)
                    self.assertIn("serverInfo", response.text)
