import json
from io import BytesIO
from queue import Queue

import requests

from openeo.rest.auth.oidc import QueuingRequestHandler, drain_queue, HttpServerThread, OidcAuthCodePkceAuthenticator, \
    OidcClientCredentialsAuthenticator


def handle_request(handler_class, path: str):
    """
    Fake (serverless) request handling

    :param handler_class: should be a subclass of `http.server.BaseHTTPRequestHandler`
    """

    class Request:
        """Fake socket-like request object."""

        def __init__(self):
            # Pass the requested URL path in HTTP format.
            self.rfile = BytesIO("GET {p} HTTP/1.1\r\n".format(p=path).encode('utf-8'))
            self.wfile = BytesIO()

        def makefile(self, mode, *args, **kwargs):
            return {'rb': self.rfile, 'wb': self.wfile}[mode]

        def sendall(self, bytes):
            self.wfile.write(bytes)

    request = Request()
    handler_class(request=request, client_address=('0.0.0.0', 8910), server=None)


def test_queuing_request_handler():
    queue = Queue()
    handle_request(QueuingRequestHandler.with_queue(queue), path="/foo/bar")
    assert list(drain_queue(queue)) == ['/foo/bar']


def test_http_server_thread():
    queue = Queue()
    server_thread = HttpServerThread(RequestHandlerClass=QueuingRequestHandler.with_queue(queue))
    server_thread.start()
    port, host, fqdn = server_thread.server_address_info()
    url = 'http://{f}:{p}/foo/bar'.format(f=fqdn, p=port)
    response = requests.get(url)
    response.raise_for_status()
    assert list(drain_queue(queue)) == ['/foo/bar']
    server_thread.shutdown()
    server_thread.join()


def test_oidc_auth_code_pkce_flow(oidc_auth_code_pkce_flow_test_setup):
    # see test/rest/conftest.py for oidc test setup fixture
    client_id = "myclient"
    oidc_discovery_url = "http://oidc.example.com/.well-known/openid-configuration"
    state, webbrowser_open = oidc_auth_code_pkce_flow_test_setup(
        client_id=client_id, oidc_discovery_url=oidc_discovery_url
    )

    authenticator = OidcAuthCodePkceAuthenticator(
        client_id=client_id,
        oidc_discovery_url=oidc_discovery_url,
        webbrowser_open=webbrowser_open
    )
    # Do the Oauth/OpenID Connect flow
    tokens = authenticator.get_tokens()
    assert state["access_token"] == tokens.access_token


def test_oidc_client_credentials_flow(oidc_client_credentials_test_setup):
    client_id = "myclient"
    oidc_discovery_url = "http://oidc.example.com/.well-known/openid-configuration"
    client_secret = "$3cr3t"
    state = oidc_client_credentials_test_setup(
        client_id=client_id, oidc_discovery_url=oidc_discovery_url
    )

    authenticator = OidcClientCredentialsAuthenticator(
        client_id=client_id,
        oidc_discovery_url=oidc_discovery_url,
        client_secret=client_secret
    )
    tokens = authenticator.get_tokens()
    assert state["access_token"] == tokens.access_token


def test_oidc_client_credentials_flow_from_json_file(tmpdir, oidc_client_credentials_test_setup):
    client_id = "myclient"
    oidc_discovery_url = "http://oidc.example.com/.well-known/openid-configuration"
    client_secret = "$3cr3t"

    state = oidc_client_credentials_test_setup(
        client_id=client_id, oidc_discovery_url=oidc_discovery_url
    )
    secrets = tmpdir.join("secrets.json")
    with secrets.open('w') as f:
        json.dump({"client_id": client_id, "client_secret": client_secret}, f)

    authenticator = OidcClientCredentialsAuthenticator.from_json_file(
        filename=str(secrets),
        oidc_discovery_url=oidc_discovery_url,
    )
    tokens = authenticator.get_tokens()
    assert state["access_token"] == tokens.access_token
