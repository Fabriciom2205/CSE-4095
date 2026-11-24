"""HTTP access controls for the operator MCP endpoint."""

from hmac import compare_digest
from urllib.parse import urlsplit

from mcp.server.transport_security import TransportSecuritySettings
from starlette.datastructures import Headers
from starlette.responses import PlainTextResponse

LOOPBACK = {"localhost", "127.0.0.1", "::1"}


def protected_mcp_app(server, transport, host, token, public_url="", *, tls=False):
    """Build the MCP transport with a separate operator bearer token when shared."""
    if (public_url or host not in LOOPBACK) and not token:
        raise ValueError("Shared MCP requires MONROE_MCP_TOKEN")
    if token and (len(token) < 32 or not token.isascii() or any(c.isspace() for c in token)):
        raise ValueError("MONROE_MCP_TOKEN must contain at least 32 non-whitespace ASCII characters")
    if host not in LOOPBACK and (not tls or not public_url):
        raise ValueError("Non-loopback MCP requires direct TLS and MONROE_MCP_PUBLIC_URL")
    security = None
    if public_url:
        url = urlsplit(public_url)
        if (url.scheme != "https" or not url.hostname or url.username or url.password
                or url.path not in ("", "/") or url.query or url.fragment or "*" in url.netloc):
            raise ValueError("MONROE_MCP_PUBLIC_URL must be an HTTPS origin")
        security = TransportSecuritySettings(enable_dns_rebinding_protection=True,
                                             allowed_hosts=[url.netloc],
                                             allowed_origins=[f"https://{url.netloc}"])
    create = server.streamable_http_app if transport == "streamable-http" else server.sse_app
    app = create(host=host, transport_security=security)
    if not token:
        return app
    expected = token.encode("ascii")

    async def authenticated(scope, receive, send):
        if scope["type"] != "http":
            await app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        values = headers.getlist("authorization")
        scheme, _, credential = values[0].partition(" ") if len(values) == 1 else ("", "", "")
        if scheme.lower() != "bearer" or not compare_digest(credential.encode("latin-1"), expected):
            await PlainTextResponse("Unauthorized", status_code=401, headers={
                "WWW-Authenticate": "Bearer", "Cache-Control": "no-store",
            })(scope, receive, send)
            return
        hosts = headers.getlist("host")
        if security and (len(hosts) != 1 or hosts[0] not in security.allowed_hosts
                         or any(origin not in security.allowed_origins for origin in headers.getlist("origin"))):
            await PlainTextResponse("Forbidden MCP origin", status_code=403)(scope, receive, send)
            return
        await app(scope, receive, send)

    return authenticated
