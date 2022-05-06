

import socket
import ssl


def url_origin(url):
    scheme_colon, _, host, _ = url.split("/", 3)
    return scheme_colon + "//" + host


COOKIE_JAR = {}


def request(url="file://browser.html", top_level_url="file://browser.html", payload=None):
    scheme, url = url.split("://", 1)
    # support for different schemes
    if scheme == "file":
        # read file
        localfile = open("browser.html", "r")
        body = localfile.read()
        return [], body
    assert scheme in ["http", "https"], \
        "Unknown scheme {}".format(scheme)
    # get host (domain) and path within domain
    if "/" not in url:
        url = url + "/"
    host, path = url.split("/", 1)

    path = "/" + path
    port = 80 if scheme == "http" else 443

    if ":" in host:
        host, port = host.split(":", 1)
        port = int(port)
    # create socket to talk to other computers
    s = socket.socket(
        # connect via internet (INET) or bluetooth, etc.
        family=socket.AF_INET,
        # stream communication or dgram (upper limit on data that can be sent)
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,  # communication protocol
    )
    s.connect((host, port))

    if scheme == "https":
        ctx = ssl.create_default_context()
        s = ctx.wrap_socket(s, server_hostname=host)
    # prepare request
    method = "POST" if payload else "GET"
    body = "{} {} HTTP/1.0\r\n".format(method, path)
    body += "Host: {}\r\n".format(host)
    if host in COOKIE_JAR:
        cookie, params = COOKIE_JAR[host]
        allow_cookie = True
        if top_level_url and params.get("samesite", "none") == "lax":
            _, _, top_level_host, _ = top_level_url.split("/", 3)
            if ":" in top_level_host:
                top_level_host, _ = top_level_host.split(":", 1)
            allow_cookie = (host == top_level_host or method == "GET")
        if allow_cookie:
            body += "Cookie: {}\r\n".format(cookie)
    if payload:
        content_length = len(payload.encode("utf8"))
        body += "Content-Length: {}\r\n".format(content_length)

    body += "\r\n" + (payload or "")
    s.send(body.encode("utf8"))  # convert python strings to bytes
    # make a file-like object to easy store all response bytes
    response = s.makefile("r", encoding="utf8", newline="\r\n")

    statusline = response.readline()
    version, status, explanation = statusline.split(" ", 2)
    if not status == "301":
        assert status == "200", "{}: {}".format(status, explanation)
    # HEADER SPECIFIC ACTIONS
    headers = {}
    while True:
        line = response.readline()
        if line == "\r\n":
            break
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()
    # fixed 301 error
    if "location" in headers:
        newurl = headers["location"]
        return request(newurl, newurl)

    if "set-cookie" in headers:
        params = {}
        if ";" in headers["set-cookie"]:
            cookie, rest = headers["set-cookie"].split(";", 1)
            for param_pair in rest.split(";"):
                if '=' in param_pair:
                    name, value = param_pair.strip().split("=", 1)
                    params[name.lower()] = value.lower()
        else:
            cookie = headers["set-cookie"]
        COOKIE_JAR[host] = (cookie, params)

    assert "transfer-encoding" not in headers
    assert "content-encoding" not in headers

    body = response.read()
    s.close()

    return headers, body
