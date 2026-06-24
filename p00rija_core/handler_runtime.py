"""HTTP request handler extracted from the application entrypoint."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler


def bind_runtime(namespace):
    """Bind application runtime dependencies and return the handler class."""
    protected = {"__name__", "__file__", "__package__", "__spec__", "__loader__", "__builtins__"}
    globals().update({key: value for key, value in namespace.items() if key not in protected})
    globals()["APP_ENTRYPOINT"] = namespace.get("__file__", "P00RIJA.py")
    return P00RIJAHTTPHandler


class P00RIJAHTTPHandler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, format, *args):
        pass

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def send_html(self, html, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def hidden_panel_path(self):
        settings = db.data.get("settings", {})
        if not settings.get("hidden_panel_path_enabled"):
            return ""
        raw = str(settings.get("hidden_panel_path") or "").strip()
        if not re.fullmatch(r"/[A-Za-z0-9_-]{19,120}", raw):
            return ""
        return raw

    def panel_gate_value(self):
        hidden = self.hidden_panel_path()
        if not hidden:
            return ""
        try:
            with open(PANEL_SECRET_PATH, "r", encoding="utf-8") as source:
                secret = source.read().strip()
        except Exception:
            secret = str(db.data.get("admin", {}).get("password_hash") or "")
        return hmac.new(secret.encode(), hidden.encode(), hashlib.sha256).hexdigest()

    def has_panel_gate(self):
        expected = self.panel_gate_value()
        if not expected:
            return True
        cookie_header = str(self.headers.get("Cookie") or "")
        cookies = {}
        for part in cookie_header.split(";"):
            key, separator, value = part.strip().partition("=")
            if separator:
                cookies[key] = value
        return hmac.compare_digest(cookies.get("p00rija_panel_gate", ""), expected)

    def is_panel_page_path(self, path):
        hidden = self.hidden_panel_path()
        if not hidden:
            return path in PANEL_PAGE_ROUTES
        if path == hidden:
            return True
        suffix = path[len(hidden):] if path.startswith(hidden + "/") else ""
        return bool(suffix and suffix in PANEL_PAGE_ROUTES)

    def send_panel_html(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        gate = self.panel_gate_value()
        if gate:
            self.send_header(
                "Set-Cookie",
                f"p00rija_panel_gate={gate}; Path=/; Max-Age=86400; Secure; HttpOnly; SameSite=Strict",
            )
        self.end_headers()
        self.wfile.write(INDEX_HTML.encode("utf-8"))

    def send_bytes(self, content, status=200, headers=None):
        self.send_response(status)
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(content)

    def send_file(self, path, status=200, headers=None, chunk_size=1024 * 1024):
        file_size = os.path.getsize(path)
        start = 0
        range_header = self.headers.get("Range", "")
        if range_header.startswith("bytes="):
            try:
                start_text = range_header[6:].split("-", 1)[0].strip()
                start = int(start_text or 0)
                if start < 0 or start >= file_size:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{file_size}")
                    self.end_headers()
                    return
                status = 206
            except Exception:
                start = 0
        self.send_response(status)
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(file_size - start))
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{file_size - 1}/{file_size}")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        with open(path, "rb") as source:
            if start:
                source.seek(start)
            while True:
                chunk = source.read(chunk_size)
                if not chunk:
                    break
                self.wfile.write(chunk)

    def end_headers(self):
        # Prevent CORS wildcard attack
        origin = "*"
        try:
            origin = self.headers.get("Origin", "*")
        except Exception:
            origin = "*"
        self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Access-Control-Allow-Methods', 'GET, HEAD, POST, PUT, DELETE, OPTIONS')
        self.send_header(
            'Access-Control-Allow-Headers',
            'Content-Type, Authorization, X-Node-Token, X-Backup-Password-B64, '
            'X-Backup-Filename, X-New-Panel-Url, X-Regenerate-Certificate',
        )
        if db.data["settings"].get("panel_tls", PANEL_TLS_FORCED):
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "same-origin")
        super().end_headers()

    def do_OPTIONS(self):
        parsed_url = urlparse(self.path)
        path = normalize_request_path(parsed_url.path)
        # Exempt /api/ paths from HTTPS redirect (matching do_GET behavior)
        # This prevents CORS preflight failures for API calls on dual HTTP/HTTPS port
        if not path.startswith("/api/") and self.redirect_plain_http_to_https():
            return
        self.send_response(200)
        self.end_headers()

    def do_HEAD(self):
        parsed_url = urlparse(self.path)
        path = normalize_request_path(parsed_url.path)

        if not path.startswith("/api/") and self.redirect_plain_http_to_https():
            return

        if self.is_panel_page_path(path):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            return

        if path.startswith("/.well-known/acme-challenge/"):
            filename = os.path.basename(path)
            filepath = os.path.join(f"{CONFIG_DIR}/acme_webroot/.well-known/acme-challenge/", filename)
            self.send_response(200 if os.path.exists(filepath) else 404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            return

        if path.startswith("/fonts/"):
            self.send_response(200)
            self.send_header("Content-Type", font_content_type(path))
            self.end_headers()
            return

        static_types = {
            "/manifest.webmanifest": "application/manifest+json",
            "/sw.js": "application/javascript",
            "/icon.svg": "image/svg+xml",
        }
        if path in static_types:
            self.send_response(200)
            self.send_header("Content-Type", static_types[path])
            self.end_headers()
            return

        if path == "/api/public-settings":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.end_headers()
            return

        self.send_response(404)
        self.end_headers()

    def redirect_plain_http_to_https(self):
        if isinstance(self.connection, ssl.SSLSocket):
            return False
        
        # Check proxy headers to avoid redirect loops when behind a reverse proxy handling HTTPS
        forwarded_proto = self.headers.get("X-Forwarded-Proto", "").lower()
        if "https" in forwarded_proto:
            return False
        if self.headers.get("X-Forwarded-Ssl", "").lower() == "on":
            return False
        if self.headers.get("X-Forwarded-Scheme", "").lower() == "https":
            return False
        if self.headers.get("Front-End-Https", "").lower() == "on":
            return False
            
        host = "localhost"
        try:
            host = self.headers.get("Host", host)
        except Exception:
            pass
        host_name = host.split(":", 1)[0].lower()
        if os.environ.get("P00RIJA_ALLOW_INSECURE_ORBSTACK", "0") == "1" and host_name.endswith(".orb.local"):
            return False
        target = f"https://{host}{self.path}"
        self.send_response(308)
        self.send_header("Location", target)
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.end_headers()
        return True

    def check_auth(self):
        auth_hdr = self.headers.get("Authorization")
        if not auth_hdr or not auth_hdr.startswith("Bearer "):
            return False
        token = auth_hdr.split(" ")[1]
        now = time.time()
        with active_sessions_lock:
            for session_token, login_time in list(active_sessions.items()):
                if now - login_time > 86400:
                    active_sessions.pop(session_token, None)
            if token in active_sessions:
                active_sessions[token] = now
                return True
        return False

    def get_post_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 1024 * 1024:
            raise ValueError("Request body too large")
        return self.rfile.read(content_length).decode('utf-8')

    def receive_backup_upload(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            raise ValueError("Choose an encrypted backup file to upload")
        if content_length > 4 * 1024 * 1024 * 1024:
            raise ValueError("Backup upload exceeds the 4 GiB safety limit")
        backup_root = os.path.join(CONFIG_DIR, "panel_backups")
        os.makedirs(backup_root, exist_ok=True)
        backup_id = "imported-" + time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
        target = os.path.join(backup_root, f"p00rija-panel-backup-{backup_id}.tar.gz.enc")
        remaining = content_length
        try:
            with open(target, "xb") as output:
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ValueError("Backup upload ended before the declared file size")
                    output.write(chunk)
                    remaining -= len(chunk)
            os.chmod(target, 0o600)
        except Exception:
            try:
                os.unlink(target)
            except OSError:
                pass
            raise
        return backup_id, target

    def send_restore_result(self, result):
        self.send_json({
            **result,
            "message": "Backup restored successfully; the panel is restarting.",
            "restart_delay_seconds": 2,
        })
        timer = threading.Timer(2.0, lambda: os._exit(0))
        timer.daemon = True
        timer.start()

    def dispatch_node_ssh_api(self, path):
        if not dispatch_node_ssh_request:
            return False
        body_text = self.get_post_body()
        body = json.loads(body_text) if body_text else {}
        handled, payload, status = dispatch_node_ssh_request(
            path,
            body,
            db_data=db.data,
            load_ssh_vault=load_ssh_vault,
            save_ssh_vault=save_ssh_vault,
            sanitize_ssh_credential=sanitize_ssh_credential,
            prune_ssh_sessions=prune_ssh_sessions,
            start_ssh_session=start_ssh_session,
            write_ssh_session=write_ssh_session,
            read_ssh_session_output=read_ssh_session_output,
            cleanup_ssh_session=cleanup_ssh_session,
            execute_ssh_command=execute_ssh_command,
            log_event=db.log,
        )
        if handled:
            self.send_json(payload, status)
        return handled

    def dispatch_nodes_post_api(self, path):
        if not dispatch_nodes_post:
            return False
        body_text = self.get_post_body()
        body = json.loads(body_text) if body_text else {}
        handled, payload, status = dispatch_nodes_post(
            path,
            body,
            db_data=db.data,
            node_api_key=NODE_ENROLLMENT_API_KEY,
            client_ip=self.client_address[0],
            normalize_role=normalize_role,
            normalize_tags=normalize_tags,
            make_node_keypair=make_node_keypair,
            save_db=db.save,
            log_event=db.log,
        )
        if handled:
            self.send_json(payload, status)
        return handled

    def handle_payload_test(self, query=None, body=None):
        query = query or {}
        try:
            if body is None:
                raw_body = self.get_post_body()
                body = json.loads(raw_body or "{}")
            link_id = body.get("id") or body.get("link_id") or query.get("id", [""])[0] or query.get("link_id", [""])[0]
            try:
                mapping_index = int(body.get("index", query.get("index", ["0"])[0]))
            except Exception:
                mapping_index = 0
            size_mb = clamp_int(body.get("size_mb", query.get("size_mb", ["4"])[0]), 4, 1, 32)
            link = db.data["links"].get(link_id)
            if not link:
                self.send_json({
                    "error": "Payload test link not found",
                    "received_id": link_id,
                    "received_index": mapping_index,
                    "available_links": summarize_links_for_error()
                }, 404)
                return
            ports = link.get("ports", [])
            if not (0 <= mapping_index < len(ports)):
                self.send_json({
                    "error": "Invalid payload test mapping index",
                    "link_id": link_id,
                    "received_index": mapping_index,
                    "ports_count": len(ports),
                    "ports": [
                        {"index": i, "user_port": p.get("user_port"), "target_port": p.get("target_port")}
                        for i, p in enumerate(ports)
                    ]
                }, 400)
                return
            mapping = ports[mapping_index]
            user_port = int(mapping.get("user_port"))
            target_port = int(mapping.get("target_port"))
            if not valid_port(user_port) or not valid_port(target_port):
                self.send_json({"error": "Invalid port mapping", "link_id": link_id, "mapping_index": mapping_index}, 400)
                return
            internal_id = link.get("internal_node_id", link.get("iran_node_id"))
            external_id = link.get("external_node_id", link.get("foreign_node_id"))
            internal_node = db.data["nodes"].get(internal_id, {})
            external_node = db.data["nodes"].get(external_id, {})
            now = time.time()
            internal_live = internal_node.get("status") == "online" and now - internal_node.get("last_seen", 0) <= 30
            external_live = external_node.get("status") == "online" and now - external_node.get("last_seen", 0) <= 30
            if not internal_live or not external_live:
                self.send_json({
                    "error": "Both internal and external nodes must be online",
                    "internal_live": internal_live,
                    "external_live": external_live,
                    "internal_node": internal_node.get("name", internal_id),
                    "external_node": external_node.get("name", external_id)
                }, 400)
                return
            direction = link.get("direction", "external_to_internal")
            if direction == "internal_to_external":
                server_id, server_node = external_id, external_node
                client_id, client_node = internal_id, internal_node
            else:
                server_id, server_node = internal_id, internal_node
                client_id, client_node = external_id, external_node

            temp_marker = f"payload_{secrets.token_hex(6)}"
            temp_user_port, temp_target_port = choose_temp_link_ports(link)
            link.setdefault("ports", []).append({
                "user_port": temp_user_port,
                "target_port": temp_target_port,
                "_temp_test": temp_marker,
                "target_host": "127.0.0.1",
            })
            db.save()
            echo_payload = {}
            transfer = {}
            try:
                # Give both nodes one config-sync/report cycle to open the temporary mapping.
                time.sleep(7)
                cmd_id = queue_payload_echo_command(client_id, temp_target_port, duration=90)
                echo_result = wait_for_node_command_result(client_id, cmd_id, timeout=22)
                if not echo_result:
                    self.send_json({
                        "error": "Tunnel client node did not start the temporary payload echo service. Update/restart that node and try again.",
                        "client_node": client_node.get("name", client_id),
                        "link_id": link_id,
                        "test_user_port": temp_user_port,
                        "test_target_port": temp_target_port
                    }, 504)
                    return
                echo_payload = echo_result.get("result", {})
                if not echo_payload.get("success"):
                    self.send_json({
                        "error": "External temporary payload echo service failed",
                        "echo_result": echo_payload,
                        "test_user_port": temp_user_port,
                        "test_target_port": temp_target_port
                    }, 500)
                    return

                transfer_cmd_id = queue_payload_client_command(server_id, temp_user_port, size_mb=size_mb)
                client_result = wait_for_node_command_result(server_id, transfer_cmd_id, timeout=75)
                if not client_result:
                    self.send_json({
                        "error": "Tunnel server node did not finish the payload transfer command. Check its listener/network mode and logs.",
                        "server_node": server_node.get("name", server_id),
                        "test_user_port": temp_user_port,
                        "test_target_port": temp_target_port,
                        "echo_result": echo_payload
                    }, 504)
                    return
                transfer = client_result.get("result", {})
            finally:
                removed = remove_temp_port_mapping(link, temp_marker)
                if removed:
                    db.save()
                if echo_payload.get("success"):
                    queue_payload_echo_stop_command(client_id, temp_target_port)

            production_hint = ""
            if not transfer.get("success"):
                server_mode = (server_node.get("stats") or {}).get("network_mode", "unknown")
                client_mode = (client_node.get("stats") or {}).get("network_mode", "unknown")
                production_hint = (
                    f"Data-plane failed. direction={direction}, server_network={server_mode}, "
                    f"client_network={client_mode}. Production VPN traffic should use host network. "
                    "In bridge mode the entry ports must be published and target services must be reachable through the Docker host gateway."
                )
            db.log("panel", "info", f"Payload tunnel self-test for '{link.get('name', link_id)}' temp {temp_user_port}->{temp_target_port}: {transfer}.")
            self.send_json({
                "success": bool(transfer.get("success")),
                "error": "" if transfer.get("success") else transfer.get("error", "Payload transfer validation failed"),
                "hint": production_hint,
                "link_id": link_id,
                "mapping_index": mapping_index,
                "user_port": user_port,
                "target_port": target_port,
                "test_user_port": temp_user_port,
                "test_target_port": temp_target_port,
                "internal_node": internal_node.get("name", internal_id),
                "external_node": external_node.get("name", external_id),
                "direction": direction,
                "server_node": server_node.get("name", server_id),
                "client_node": client_node.get("name", client_id),
                "server_network_mode": (server_node.get("stats") or {}).get("network_mode", "unknown"),
                "client_network_mode": (client_node.get("stats") or {}).get("network_mode", "unknown"),
                "size_mb": size_mb,
                "echo_result": echo_payload,
                "transfer": transfer
            }, 200 if transfer.get("success") else 502)
        except Exception as e:
            self.send_json({"error": f"Payload tunnel test failed: {e}"}, 500)

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = normalize_request_path(parsed_url.path)
        query = parse_qs(parsed_url.query)

        if not path.startswith("/api/") and self.redirect_plain_http_to_https():
            return

        # Let's Encrypt / ACME HTTP-01 Webroot challenge route
        if path.startswith("/.well-known/acme-challenge/"):
            filename = os.path.basename(path)
            filepath = os.path.join(f"{CONFIG_DIR}/acme_webroot/.well-known/acme-challenge/", filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r") as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(content.encode())
                    return
                except Exception:
                    pass
            self.send_response(404)
            self.end_headers()
            return

        if self.is_panel_page_path(path):
            self.send_panel_html()
            return

        if path.startswith("/fonts/"):
            font_name = os.path.basename(path)
            font_dirs = [
                os.environ.get("P00RIJA_FONTS_DIR", ""),
                "/app/fonts",
                os.path.join(CONFIG_DIR, "fonts"),
                os.path.join(os.getcwd(), "fonts"),
                os.path.join(APP_ROOT, "fonts"),
            ]
            filepath = ""
            for font_dir in font_dirs:
                if not font_dir:
                    continue
                candidate = os.path.join(font_dir, font_name)
                if os.path.exists(candidate):
                    filepath = candidate
                    break
            if filepath:
                try:
                    with open(filepath, "rb") as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", font_content_type(path))
                    self.send_header("Cache-Control", "public, max-age=31536000")
                    self.end_headers()
                    self.wfile.write(content)
                    return
                except Exception:
                    pass
            self.send_response(404)
            self.end_headers()
            return

        if path == "/manifest.webmanifest":
            self.send_response(200)
            self.send_header("Content-Type", "application/manifest+json")
            self.end_headers()
            self.wfile.write(build_manifest(self.hidden_panel_path() or "/"))
            return

        if path == "/sw.js":
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.end_headers()
            self.wfile.write(service_worker_script())
            return

        if path == "/icon.svg":
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.end_headers()
            self.wfile.write(APP_LOGO_SVG.encode("utf-8"))
            return

        if path == "/api/public-settings" and dispatch_public_system_get:
            handled, payload, status = dispatch_public_system_get(
                path,
                settings=db.data.get("settings", {}),
                app_version=APP_VERSION,
                app_license=APP_LICENSE,
                root=os.getcwd(),
                config_dir=CONFIG_DIR,
                engines_dir=ENGINES_DIR,
                db_data=db.data,
                engine_catalog=ENGINE_CATALOG,
                audit_builder=core_build_system_audit,
            )
            if handled:
                self.send_json(payload, status)
                return

        if path == "/api/node-update-package":
            package_id = query.get("package_id", [""])[0]
            node_token = normalize_node_token(self.headers.get("X-Node-Token"))
            matched_node_id, matched_node = node_for_update_package_download(node_token, package_id)
            if not matched_node_id:
                self.send_json({"error": "Unauthorized update package"}, 401)
                return
            signed_path = path + (f"?{parsed_url.query}" if parsed_url.query else "")
            if not valid_node_signature(matched_node, signed_path, "", self.headers.get("X-Node-Signature")):
                self.send_json({"error": "Invalid node signature"}, 401)
                return
            package_path = node_update_package_path(package_id)
            if not package_path:
                self.send_json({"error": "Update package not found"}, 404)
                return
            self.send_file(package_path, 200, {
                "Content-Type": "application/gzip",
                "Content-Disposition": f'attachment; filename="p00rija-node-update-{package_id}.tar.gz"',
            })
            return

        if path == "/api/node-config":
            node_token = normalize_node_token(self.headers.get("X-Node-Token"))
            matched_node_id = None
            for nid, n in db.data["nodes"].items():
                if n.get("token") == node_token:
                    matched_node_id = nid
                    break
            
            if not matched_node_id:
                self.send_json({"error": "Unauthorized Node"}, 401)
                return

            node = db.data["nodes"][matched_node_id]
            if not valid_node_signature(node, path, "", self.headers.get("X-Node-Signature")):
                self.send_json({"error": "Invalid node signature"}, 401)
                return
            node_links = []
            for lid, l in db.data["links"].items():
                if l.get("paused", False):
                    continue
                if l.get("internal_node_id", l.get("iran_node_id")) == matched_node_id or l.get("external_node_id", l.get("foreign_node_id")) == matched_node_id:
                    direction = l.get("direction", "external_to_internal")
                    if direction not in ("external_to_internal", "internal_to_external"):
                        direction = "external_to_internal"
                    internal_id = l.get("internal_node_id", l.get("iran_node_id"))
                    external_id = l.get("external_node_id", l.get("foreign_node_id"))
                    internal_node = db.data["nodes"].get(internal_id, {})
                    external_node = db.data["nodes"].get(external_id, {})
                    server_node_id = internal_id if direction == "external_to_internal" else external_id
                    client_node_id = external_id if direction == "external_to_internal" else internal_id
                    server_node = db.data["nodes"].get(server_node_id, {})
                    client_node = db.data["nodes"].get(client_node_id, {})
                    local_tunnel_role = "server" if matched_node_id == server_node_id else "client"
                    peer_node = client_node if local_tunnel_role == "server" else server_node
                    other_ip = peer_node.get("ip", "")
                    
                    link_config = {
                        "id": lid,
                        "direction": direction,
                        "local_tunnel_role": local_tunnel_role,
                        "server_node_id": server_node_id,
                        "client_node_id": client_node_id,
                        "server_ip": server_node.get("ip", ""),
                        "client_ip": client_node.get("ip", ""),
                        "iran_ip": server_node.get("ip", other_ip),
                        "peer_ip": other_ip,
                        "bridge_port": l["bridge_port"],
                        "sync_port": l["sync_port"],
                        "pool_size": l.get("pool_size", 4),
                        "max_reverse_workers": l.get("max_reverse_workers", MAX_REVERSE_WORKERS_PER_LINK),
                        "min_ready_workers": l.get("min_ready_workers", MIN_READY_WORKERS_PER_LINK),
                        "bonding_enabled": bool(l.get("bonding_enabled", False)),
                        "bonding_max_lanes": clamp_int(l.get("bonding_max_lanes", 4), 4, 2, BONDING_MAX_LANES),
                        "data_plane_architecture": str(l.get("data_plane_architecture") or ("adaptive_bonding" if l.get("bonding_enabled") else "per_user")),
                        "mux_carriers": clamp_int(l.get("mux_carriers", 4), 4, 2, MUX_MAX_CARRIERS),
                        "ports": l.get("ports", []),
                        "engine": l.get("engine", "builtin"),
                        "native_engine_enabled": bool(l.get("native_engine_enabled", False)),
                        "transport": l.get("transport", l.get("tunnel_mode", "tcp")),
                        "network": l.get("network", "tcp"),
                        "tunnel_mode": l.get("tunnel_mode", "tcp"),
                        "tls_enabled": l.get("tls_enabled", False),
                        "tls_sni": l.get("tls_sni", "speedtest.net"),
                        "cert_sni": db.data["settings"].get("panel_host", "localhost"),
                        "obfs_host": l.get("obfs_host", "speedtest.net"),
                        "obfs_path": l.get("obfs_path", "/tunnel"),
                        "profile_id": l.get("profile_id", "custom"),
                        "padding_min": l.get("padding_min", 0),
                        "padding_max": l.get("padding_max", 0),
                        "jitter_ms": l.get("jitter_ms", 0),
                        "keepalive_interval": l.get("keepalive_interval", 25),
                        "hysteria_up_mbps": l.get("hysteria_up_mbps", HYSTERIA2_DEFAULT_UP_MBPS),
                        "hysteria_down_mbps": l.get("hysteria_down_mbps", HYSTERIA2_DEFAULT_DOWN_MBPS),
                        "xray_config": xray_config_for_link(l, node.get("type", node.get("role", "unknown"))) if l.get("engine") == "xray" else None,
                        "muxquantum_config": muxquantum_config_for_link(lid, l, node.get("type", node.get("role", "unknown")), other_ip) if l.get("engine") == "muxquantum" else None,
                        "hysteria2_config": hysteria2_config_for_link(l, node.get("type", node.get("role", "unknown"))) if l.get("engine") == "hysteria2" else None,
                        "amneziawg_config": amneziawg_config_for_link(lid, l, node.get("type", node.get("role", "unknown")), other_ip) if l.get("engine") == "amneziawg" and amneziawg_config_for_link else None,
                        "wireguard_config": wireguard_config_for_link(lid, l, node.get("type", node.get("role", "unknown")), other_ip) if l.get("engine") == "wireguard" and wireguard_config_for_link else None
                    }
                    for key in (
                        "awg_address", "awg_client_address", "awg_mtu", "awg_jc", "awg_jmin", "awg_jmax",
                        "awg_s1", "awg_s2", "awg_s3", "awg_s4", "awg_h1", "awg_h2", "awg_h3", "awg_h4",
                        "awg_i1", "awg_i2", "awg_i3", "awg_i4", "awg_i5", "awg_interface",
                        "wg_address", "wg_client_address", "wg_mtu", "wg_allowed_ips", "wg_interface"
                    ):
                        if key in l:
                            link_config[key] = l.get(key)

                    # Pin the same panel-managed certificate on both tunnel endpoints.
                    if l.get("tls_enabled"):
                        cert_path = db.data["settings"].get("cert_path", f"{CONFIG_DIR}/certs/cert.pem")
                        key_path = db.data["settings"].get("key_path", f"{CONFIG_DIR}/certs/key.pem")
                        try:
                            with open(cert_path, "r") as f:
                                link_config["cert_content"] = f.read()
                            needs_private_key = (
                                local_tunnel_role == "server"
                                or (
                                    l.get("engine") == "hysteria2"
                                    and l.get("native_engine_enabled", False)
                                    and local_tunnel_role == "client"
                                )
                            )
                            if needs_private_key:
                                with open(key_path, "r") as f:
                                    link_config["key_content"] = f.read()
                        except Exception as e:
                            db.log("panel", "error", f"Failed reading SSL cert for link sync: {e}")

                    node_links.append(link_config)

            if node.get("paused", False):
                node_links = []

            node_commands = db.data.setdefault("node_commands", {}).get(matched_node_id, [])
            self.send_json({
                "role": node.get("type", node.get("role", "unknown")), 
                "links": node_links,
                "commands": node_commands[:8],
                "settings": {
                    "engine_restart_interval": db.data["settings"].get("engine_restart_interval", 0),
                    "disable_ipv6": db.data["settings"].get("disable_ipv6", False)
                }
            })
            return

        if path.startswith("/api/"):
            if path in ("/api/logs/csv", "/api/profiles/export") and "token" in query:
                csv_token = query["token"][0]
                with active_sessions_lock:
                    has_csv_session = csv_token in active_sessions
                if not has_csv_session:
                    self.send_response(401)
                    self.end_headers()
                    return
            elif not self.check_auth():
                self.send_json({"error": "Unauthorized"}, 401)
                return

            if path in ("/api/system/audit", "/api/system/routes") and dispatch_public_system_get:
                handled, payload, status = dispatch_public_system_get(
                    path,
                    settings=db.data.get("settings", {}),
                    app_version=APP_VERSION,
                    app_license=APP_LICENSE,
                    root=os.getcwd(),
                    config_dir=CONFIG_DIR,
                    engines_dir=ENGINES_DIR,
                    db_data=db.data,
                    engine_catalog=ENGINE_CATALOG,
                    audit_builder=core_build_system_audit,
                )
                if handled:
                    self.send_json(payload, status)
                    return

            if path == "/api/engines/check-updates":
                engine_id = query.get("engine", [""])[0]
                payload = check_all_engine_updates(engine_id)
                self.send_json(payload, 200 if payload.get("success") else 400)
                return

            if path == "/api/nodes/version-check":
                node_id = query.get("id", [""])[0]
                if node_id and node_id not in db.data.get("nodes", {}):
                    self.send_json({"error": "Node not found"}, 404)
                    return
                payload = check_node_versions(node_id)
                self.send_json(payload, 200 if payload.get("success") else 400)
                return

            if path == "/api/speedtest/status":
                job_id = query.get("id", [""])[0]
                job = get_speedtest_job(job_id)
                if not job:
                    self.send_json({"error": "Speed-test job not found"}, 404)
                else:
                    self.send_json({"success": True, "job": job})
                return

            if path == "/api/host-control/status":
                if not host_control_status:
                    self.send_json({"error": "Host-control module is unavailable"}, 503)
                    return
                request_id = query.get("id", [""])[0]
                payload = host_control_status(CONFIG_DIR, request_id)
                self.send_json(payload, 200 if payload.get("success") else 400)
                return

            if path == "/api/backup/download":
                backup_id = query.get("id", [""])[0]
                backup_path = backup_path_for_id(backup_id)
                if not backup_path:
                    self.send_json({"error": "Backup not found"}, 404)
                    return
                self.send_file(backup_path, 200, {
                    "Content-Type": "application/octet-stream",
                    "Content-Disposition": f'attachment; filename="{os.path.basename(backup_path)}"',
                })
                return

            if path == "/api/backup/list":
                if not list_server_backups:
                    self.send_json({"error": "Backup module is unavailable"}, 503)
                    return
                self.send_json({"success": True, "backups": list_server_backups(CONFIG_DIR)})
                return

            if path in ("/api/status", "/api/logs", "/api/logs/csv") and dispatch_dashboard_get:
                handled, payload, status, headers = dispatch_dashboard_get(
                    path,
                    db_data=db.data,
                    app_version=APP_VERSION,
                    app_build=APP_BUILD,
                    app_license=APP_LICENSE,
                    author_github=APP_AUTHOR_GITHUB,
                    author_email=APP_AUTHOR_EMAIL,
                    sanitize_nodes_for_status=sanitize_nodes_for_status,
                    list_engine_status=list_engine_status,
                    load_ssh_vault=load_ssh_vault,
                    sanitize_ssh_credential=sanitize_ssh_credential,
                    list_all_runtime_sessions=list_all_runtime_sessions,
                    get_host_info=get_host_info,
                    ensure_tunnel_profiles=ensure_tunnel_profiles,
                    refresh_node_ping_async=refresh_node_ping_async,
                    save_db=db.save,
                )
                if handled:
                    if isinstance(payload, (bytes, bytearray)):
                        self.send_bytes(bytes(payload), status, headers)
                    else:
                        self.send_json(payload, status)
                    return

            if path in ("/api/nodes/secrets", "/api/nodes/toggle-pause", "/api/nodes/test") and dispatch_nodes_get:
                handled, payload, status = dispatch_nodes_get(
                    path,
                    query,
                    db_data=db.data,
                    save_db=db.save,
                )
                if handled:
                    self.send_json(payload, status)
                    return

            if path == "/api/links/smart-test":
                try:
                    body = json.loads(self.get_post_body())
                    self.send_json(build_smart_tunnel_benchmark(
                        body.get("internal_node_id"),
                        body.get("external_node_id"),
                        body.get("direction", "external_to_internal"),
                        body.get("objective", "balanced"),
                    ))
                except Exception as e:
                    self.send_json({"error": f"Smart test failed: {e}"}, 400)
                return

            if path in ("/api/nodes/ssh/save", "/api/nodes/ssh/start", "/api/nodes/ssh/write", "/api/nodes/ssh/read", "/api/nodes/ssh/close", "/api/nodes/ssh/run"):
                if self.dispatch_node_ssh_api(path):
                    return

            if path == "/api/engines/health":
                try:
                    body = json.loads(self.get_post_body())
                    self.send_json(check_engine_health(body.get("engine")))
                except Exception as e:
                    self.send_json({"success": False, "healthy": False, "error": f"Engine health check failed: {e}"}, 400)
                return

            if path == "/api/engines/check-updates":
                try:
                    body_text = self.get_post_body()
                    body = json.loads(body_text) if body_text else {}
                    payload = check_all_engine_updates(body.get("engine", ""))
                    self.send_json(payload, 200 if payload.get("success") else 400)
                except Exception as e:
                    self.send_json({"success": False, "error": f"Engine update check failed: {e}"}, 400)
                return

            if path == "/api/engines/control":
                try:
                    body = json.loads(self.get_post_body())
                    engine_id = body.get("engine")
                    action = body.get("action")
                    if action not in ("start", "stop", "restart"):
                        self.send_json({"error": "Invalid action"}, 400)
                        return
                    result = control_engine_process(engine_id, action)
                    if not result.get("success"):
                        self.send_json(result, 400)
                        return
                    db.log("panel", "info", f"Engine control: {engine_id} -> {action}.")
                    self.send_json({"success": True, "result": result, "engines": list_engine_status()})
                except Exception as e:
                    self.send_json({"error": f"Engine control failed: {e}"}, 400)
                return

            if path == "/api/engines/upload":
                try:
                    body = json.loads(self.get_post_body())
                    engine_id = body.get("engine")
                    filename = str(body.get("filename") or "")
                    content = base64.b64decode(body.get("content_base64") or "")
                    installed = install_engine_archive(engine_id, filename, content)
                    db.log("panel", "info", f"Manually updated engine {engine_id}: {installed}.")
                    self.send_json({"success": True, "installed": installed, "engines": list_engine_status()})
                except Exception as e:
                    self.send_json({"error": f"Manual engine update failed: {e}"}, 400)
                return

            if path in ("/api/runtime/processes", "/api/runtime/threads", "/api/runtime/sessions", "/api/runtime/resources") and dispatch_runtime_get:
                handled, payload, status = dispatch_runtime_get(
                    path,
                    db_data=db.data,
                    get_all_process_snapshot=get_all_process_snapshot,
                    get_all_thread_snapshot=get_all_thread_snapshot,
                    list_all_runtime_sessions=list_all_runtime_sessions,
                    runtime_session_summary=runtime_session_summary,
                    thread_count=threading.active_count,
                    get_own_rss_kb=get_own_rss_kb,
                )
                if handled:
                    self.send_json(payload, status)
                    return

            if path in ("/api/links/toggle-pause", "/api/links/test", "/api/links/engine-config") and dispatch_links_get:
                handled, payload, status = dispatch_links_get(
                    path,
                    query,
                    db_data=db.data,
                    save_db=db.save,
                    log_event=db.log,
                    list_runtime_sessions=list_runtime_sessions,
                    hysteria2_config_for_link=hysteria2_config_for_link,
                    muxquantum_config_for_link=muxquantum_config_for_link,
            xray_config_for_link=xray_config_for_link,
            singbox_config_for_link=singbox_config_for_link,
            masque_config_for_link=masque_config_for_link,
                    amneziawg_config_for_link=amneziawg_config_for_link,
                    wireguard_config_for_link=wireguard_config_for_link,
                    ssh_config_for_link=ssh_config_for_link,
                    stunnel_config_for_link=stunnel_config_for_link,
                    raw_socket_config_for_link=raw_socket_config_for_link,
                    aead_config_for_link=aead_config_for_link,
                )
                if handled:
                    self.send_json(payload, status)
                    return

            if path == "/api/links/payload-test":
                self.handle_payload_test(query, body={})
                return

            if path == "/api/profiles/export":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Disposition", 'attachment; filename="p00rija_tunnel_profiles.json"')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "version": APP_VERSION,
                    "profiles": db.data["settings"].get("tunnel_profiles", default_tunnel_profiles())
                }, indent=2).encode("utf-8"))
                return

        if path.startswith("/api/"):
            self.send_json({"error": "API endpoint not found", "method": "GET", "path": path}, 404)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed_url = urlparse(self.path)
        path = normalize_request_path(parsed_url.path)
        query = parse_qs(parsed_url.query)

        # Exempt /api/ paths from HTTPS redirect (matching do_GET behavior)
        # This prevents login and other API POST requests from being redirected
        if not path.startswith("/api/") and self.redirect_plain_http_to_https():
            return

        if path == "/api/login":
            if not self.has_panel_gate():
                self.send_json({"error": "Not found"}, 404)
                return
            try:
                body = json.loads(self.get_post_body())
                username = body.get("username")
                password = body.get("password")
                otp = body.get("otp")
                pwd_hash = hashlib.sha256(password.encode()).hexdigest()

                if username == db.data["admin"]["username"] and pwd_hash == db.data["admin"]["password_hash"]:
                    if db.data["settings"].get("two_factor_enabled"):
                        if not verify_totp(db.data["settings"].get("two_factor_secret", ""), otp):
                            self.send_json({"error": "Invalid two-factor code"}, 401)
                            return
                    session_token = secrets.token_hex(16)
                    with active_sessions_lock:
                        active_sessions[session_token] = time.time()
                    self.send_json({"token": session_token})
                    db.log("panel", "info", f"Admin user '{username}' successfully logged in.")
                else:
                    self.send_json({"error": "Invalid credentials"}, 401)
            except Exception:
                self.send_json({"error": "Bad request"}, 400)
            return

        if path == "/api/report":
            node_token = normalize_node_token(self.headers.get("X-Node-Token"))
            matched_node_id = None
            for nid, n in db.data["nodes"].items():
                if n.get("token") == node_token:
                    matched_node_id = nid
                    break

            if not matched_node_id:
                self.send_json({"error": "Unauthorized Node"}, 401)
                return

            try:
                body_text = self.get_post_body()
                stats = json.loads(body_text)
                node = db.data["nodes"][matched_node_id]
                if not valid_node_signature(node, path, body_text, self.headers.get("X-Node-Signature")):
                    self.send_json({"error": "Invalid node signature"}, 401)
                    return
                node["status"] = "online"
                node["last_seen"] = time.time()
                if "ping_ms" in node.get("stats", {}):
                    stats["ping_ms"] = node["stats"]["ping_ms"]
                node["stats"] = stats
                persist_node_heartbeats_if_due()
                self.send_json({"success": True})
            except Exception:
                self.send_json({"error": "Bad request"}, 400)
            return

        if path == "/api/node-command-result":
            node_token = normalize_node_token(self.headers.get("X-Node-Token"))
            matched_node_id = None
            for nid, n in db.data["nodes"].items():
                if n.get("token") == node_token:
                    matched_node_id = nid
                    break
            if not matched_node_id:
                self.send_json({"error": "Unauthorized Node"}, 401)
                return
            try:
                body_text = self.get_post_body()
                body = json.loads(body_text)
                node = db.data["nodes"][matched_node_id]
                if not valid_node_signature(node, path, body_text, self.headers.get("X-Node-Signature")):
                    self.send_json({"error": "Invalid node signature"}, 401)
                    return
                cmd_id = body.get("id")
                command_result = {
                    "id": cmd_id,
                    "type": body.get("type"),
                    "action": body.get("action"),
                    "result": body.get("result", {}),
                    "received_at": time.time()
                }
                node["last_command_result"] = command_result
                history = node.setdefault("command_results", {})
                history[str(cmd_id or "")] = command_result
                if len(history) > 24:
                    stale_ids = sorted(
                        history,
                        key=lambda item: float((history.get(item) or {}).get("received_at", 0)),
                    )[:-16]
                    for stale_id in stale_ids:
                        history.pop(stale_id, None)
                commands = db.data.setdefault("node_commands", {}).get(matched_node_id, [])
                db.data["node_commands"][matched_node_id] = [cmd for cmd in commands if cmd.get("id") != cmd_id]
                db.save()
                self.send_json({"success": True})
            except Exception as e:
                self.send_json({"error": f"Bad command result: {e}"}, 400)
            return

        if path.startswith("/api/"):
            if not self.check_auth():
                self.send_json({"error": "Unauthorized"}, 401)
                return

            if path == "/api/links/payload-test":
                self.handle_payload_test(query)
                return

            if path == "/api/links/smart-test":
                try:
                    body = json.loads(self.get_post_body())
                    self.send_json(build_smart_tunnel_benchmark(
                        body.get("internal_node_id"),
                        body.get("external_node_id"),
                        body.get("direction", "external_to_internal"),
                        body.get("objective", "balanced"),
                    ))
                except Exception as e:
                    self.send_json({"error": f"Smart test failed: {e}"}, 400)
                return

            if path == "/api/speedtest/start":
                try:
                    body = json.loads(self.get_post_body() or "{}")
                    self.send_json({"success": True, "job": start_speedtest_job(body)}, 202)
                except Exception as e:
                    self.send_json({"error": f"Speed test could not start: {e}"}, 400)
                return

            if path == "/api/speedtest/install":
                try:
                    body = json.loads(self.get_post_body() or "{}")
                    node_ids = body.get("node_ids") or list(db.data.get("nodes", {}))
                    queued = []
                    for node_id in node_ids:
                        if node_id not in db.data.get("nodes", {}):
                            continue
                        command_id = queue_speedtest_command(node_id, "speedtest_iperf_install")
                        queued.append({"node_id": node_id, "command_id": command_id})
                    self.send_json({"success": True, "queued": queued, "queued_count": len(queued)})
                except Exception as e:
                    self.send_json({"error": f"iperf3 installation could not be queued: {e}"}, 400)
                return

            if path in ("/api/nodes/ssh/save", "/api/nodes/ssh/start", "/api/nodes/ssh/write", "/api/nodes/ssh/read", "/api/nodes/ssh/close", "/api/nodes/ssh/run"):
                if self.dispatch_node_ssh_api(path):
                    return

            if path == "/api/nodes/update":
                try:
                    body_text = self.get_post_body()
                    body = json.loads(body_text) if body_text else {}
                    scope = str(body.get("scope", "app_engines"))
                    restart = bool(body.get("restart", True))
                    node_id = body.get("node_id") or None
                    if node_id and node_id not in db.data.get("nodes", {}):
                        self.send_json({"error": "Node not found"}, 404)
                        return
                    result = queue_node_update(node_id=node_id, scope=scope, restart=restart)
                    status = 200 if result.get("queued_count") else 400
                    if not result.get("queued_count"):
                        result["error"] = "No online node matched the update target"
                    self.send_json(result, status)
                except Exception as e:
                    self.send_json({"error": f"Remote update queue failed: {e}"}, 400)
                return

            if path == "/api/backup/create":
                try:
                    if not build_encrypted_backup:
                        raise RuntimeError("Backup module is unavailable")
                    body_text = self.get_post_body()
                    body = json.loads(body_text) if body_text else {}
                    result = build_encrypted_backup(
                        config_dir=CONFIG_DIR,
                        app_root=APP_ROOT,
                        engines_dir=ENGINES_DIR,
                        password=str(body.get("backup_password") or ""),
                        app_version=APP_VERSION,
                        app_build=APP_BUILD,
                        include_engines=bool(body.get("include_engines", True)),
                    )
                    db.log("panel", "warning", f"Encrypted full panel backup created: {result['filename']}.")
                    self.send_json({
                        "success": True,
                        "backup_id": result["backup_id"],
                        "filename": result["filename"],
                        "size": result["size"],
                        "sha256": result["sha256"],
                        "include_engines": result["include_engines"],
                        "download_url": f"/api/backup/download?id={result['backup_id']}",
                    })
                except Exception as e:
                    self.send_json({"error": f"Backup creation failed: {e}"}, 400)
                return

            if path == "/api/backup/restore":
                try:
                    if not restore_encrypted_backup:
                        raise RuntimeError("Restore module is unavailable")
                    body_text = self.get_post_body()
                    body = json.loads(body_text) if body_text else {}
                    backup_path = backup_path_for_id(body.get("backup_id"))
                    if not backup_path:
                        raise ValueError("Selected server backup was not found")
                    result = restore_encrypted_backup(
                        backup_path=backup_path,
                        password=str(body.get("backup_password") or ""),
                        config_dir=CONFIG_DIR,
                        new_panel_url=str(body.get("new_panel_url") or ""),
                        regenerate_certificate=bool(body.get("regenerate_certificate", False)),
                    )
                    self.send_restore_result(result)
                except Exception as e:
                    self.send_json({"error": f"Backup restore failed: {e}"}, 400)
                return

            if path == "/api/backup/restore-upload":
                uploaded_path = ""
                try:
                    if not restore_encrypted_backup:
                        raise RuntimeError("Restore module is unavailable")
                    _backup_id, uploaded_path = self.receive_backup_upload()
                    encoded_password = str(self.headers.get("X-Backup-Password-B64") or "")
                    try:
                        backup_password = base64.b64decode(encoded_password, validate=True).decode("utf-8")
                    except Exception:
                        raise ValueError("Backup password header is invalid")
                    result = restore_encrypted_backup(
                        backup_path=uploaded_path,
                        password=backup_password,
                        config_dir=CONFIG_DIR,
                        new_panel_url=str(self.headers.get("X-New-Panel-Url") or ""),
                        regenerate_certificate=str(
                            self.headers.get("X-Regenerate-Certificate") or ""
                        ).lower() in ("1", "true", "yes"),
                    )
                    self.send_restore_result(result)
                except Exception as e:
                    if uploaded_path:
                        try:
                            os.unlink(uploaded_path)
                        except OSError:
                            pass
                    self.send_json({"error": f"Backup restore failed: {e}"}, 400)
                return

            if path == "/api/migration/start":
                try:
                    if not build_encrypted_backup or not migrate_backup_over_ssh:
                        raise RuntimeError("Migration module is unavailable")
                    body_text = self.get_post_body()
                    body = json.loads(body_text) if body_text else {}
                    new_panel_url = normalize_panel_url(body.get("new_panel_url"))
                    backup_password = str(body.get("backup_password") or "")
                    backup = build_encrypted_backup(
                        config_dir=CONFIG_DIR,
                        app_root=APP_ROOT,
                        engines_dir=ENGINES_DIR,
                        password=backup_password,
                        app_version=APP_VERSION,
                        app_build=APP_BUILD,
                        include_engines=bool(body.get("include_engines", True)),
                    )
                    destination = migrate_backup_over_ssh(
                        backup_path=backup["path"],
                        backup_password=backup_password,
                        host=str(body.get("host") or ""),
                        port=int(body.get("port") or 22),
                        username=str(body.get("username") or "root"),
                        password=str(body.get("password") or ""),
                        new_panel_url=new_panel_url,
                        regenerate_certificate=bool(body.get("regenerate_certificate", True)),
                    )
                    queued = queue_panel_handoff(new_panel_url)
                    handoff = wait_for_panel_handoff_results(
                        queued,
                        timeout=clamp_int(body.get("handoff_timeout", 45), 45, 10, 120),
                    )
                    acknowledged = sum(1 for item in handoff.values() if item.get("success"))
                    db.log(
                        "panel",
                        "warning",
                        f"Panel migrated to {new_panel_url}; node handoff acknowledged={acknowledged}/{len(queued)}.",
                    )
                    self.send_json({
                        "success": True,
                        "destination": destination,
                        "backup": {
                            "backup_id": backup["backup_id"],
                            "filename": backup["filename"],
                            "size": backup["size"],
                            "sha256": backup["sha256"],
                        },
                        "node_handoff": {
                            "queued": len(queued),
                            "acknowledged": acknowledged,
                            "results": handoff,
                            "source_panel_kept_online": True,
                        },
                    })
                except subprocess.CalledProcessError as e:
                    detail = (e.stderr or e.stdout or b"").decode(errors="replace") if isinstance(e.stderr or e.stdout, bytes) else str(e.stderr or e.stdout or e)
                    self.send_json({"error": f"Migration failed: {detail[-3000:]}"}, 400)
                except Exception as e:
                    self.send_json({"error": f"Migration failed: {e}"}, 400)
                return

            if path == "/api/engines/health":
                try:
                    body = json.loads(self.get_post_body())
                    self.send_json(check_engine_health(body.get("engine")))
                except Exception as e:
                    self.send_json({"success": False, "healthy": False, "error": f"Engine health check failed: {e}"}, 400)
                return

            if path == "/api/engines/check-updates":
                try:
                    body_text = self.get_post_body()
                    body = json.loads(body_text) if body_text else {}
                    payload = check_all_engine_updates(body.get("engine", ""))
                    self.send_json(payload, 200 if payload.get("success") else 400)
                except Exception as e:
                    self.send_json({"success": False, "error": f"Engine update check failed: {e}"}, 400)
                return

            if path == "/api/engines/control":
                try:
                    body = json.loads(self.get_post_body())
                    engine_id = body.get("engine")
                    action = body.get("action")
                    if action not in ("start", "stop", "restart"):
                        self.send_json({"error": "Invalid action"}, 400)
                        return
                    result = control_engine_process(engine_id, action)
                    if not result.get("success"):
                        self.send_json(result, 400)
                        return
                    db.log("panel", "info", f"Engine control: {engine_id} -> {action}.")
                    self.send_json({"success": True, "result": result, "engines": list_engine_status()})
                except Exception as e:
                    self.send_json({"error": f"Engine control failed: {e}"}, 400)
                return

            if path == "/api/engines/upload":
                try:
                    body = json.loads(self.get_post_body())
                    engine_id = body.get("engine")
                    filename = str(body.get("filename") or "")
                    content = base64.b64decode(body.get("content_base64") or "")
                    installed = install_engine_archive(engine_id, filename, content)
                    db.log("panel", "info", f"Manually updated engine {engine_id}: {installed}.")
                    self.send_json({"success": True, "installed": installed, "engines": list_engine_status()})
                except Exception as e:
                    self.send_json({"error": f"Manual engine update failed: {e}"}, 400)
                return

            if path == "/api/runtime/optimize":
                try:
                    body_text = self.get_post_body()
                    body = json.loads(body_text) if body_text else {}
                    action = str(body.get("action", "idle"))
                    scope = str(body.get("scope", "all"))
                    link_id = str(body.get("link_id", "") or "")
                    if action not in ("idle", "gc", "all", "pressure", "thread_guard"):
                        self.send_json({"error": "Invalid optimization action"}, 400)
                        return
                    if scope not in ("panel", "nodes", "all"):
                        self.send_json({"error": "Invalid optimization scope"}, 400)
                        return
                    panel_result = optimize_runtime_resources(action, link_id=link_id or None) if scope in ("panel", "all") else None
                    if action == "thread_guard" and scope in ("nodes", "all"):
                        queued_nodes = queue_node_link_guardian(link_id or None)
                        queued_link_guardians = queued_nodes
                    else:
                        queued_nodes = queue_node_optimization(action) if scope in ("nodes", "all") else 0
                        queued_link_guardians = 0
                    self.send_json({
                        "success": True,
                        "action": action,
                        "scope": scope,
                        "panel": panel_result,
                        "queued_nodes": queued_nodes,
                        "queued_link_guardians": queued_link_guardians,
                        "closed_idle_sessions": (panel_result or {}).get("closed_idle_sessions", 0),
                        "link_guardian_runs": (panel_result or {}).get("link_guardian_runs", 0),
                        "link_idle_workers_reaped": (panel_result or {}).get("link_idle_workers_reaped", 0),
                        "gc_collected": (panel_result or {}).get("gc_collected", 0),
                        "malloc_trimmed": (panel_result or {}).get("malloc_trimmed", False),
                        "pressure_level": (panel_result or {}).get("pressure_level", "normal"),
                        "rss_reclaimed_kb": (panel_result or {}).get("rss_reclaimed_kb", 0),
                        "threads_before": (panel_result or {}).get("threads_before", 0),
                        "rss_kb": (panel_result or {}).get("rss_kb", get_own_rss_kb())
                    })
                except Exception as e:
                    self.send_json({"error": f"Optimization failed: {e}"}, 500)
                return

            if path in ("/api/nodes", "/api/nodes/edit", "/api/nodes/register", "/api/nodes/auto", "/api/nodes/reorder"):
                if self.dispatch_nodes_post_api(path):
                    return

            if path in (
                "/api/links", "/api/links/edit", "/api/links/next-ports",
                "/api/links/ports", "/api/links/ports/edit",
                "/api/links/reorder", "/api/links/categories/reorder",
            ) and dispatch_links_post:
                try:
                    body = json.loads(self.get_post_body())
                    handled, payload, status = dispatch_links_post(
                        path,
                        query,
                        body,
                        db_data=db.data,
                        save_db=db.save,
                        log_event=db.log,
                        default_tunnel_profiles=default_tunnel_profiles,
                        normalize_tags=normalize_tags,
                        clamp_int=clamp_int,
                        valid_port=valid_port,
                        role_matches=role_matches,
                        valid_engines=VALID_TUNNEL_ENGINES,
                        valid_modes=VALID_TUNNEL_MODES,
                        valid_transports=VALID_TUNNEL_TRANSPORTS,
                        max_pool_size_per_link=MAX_POOL_SIZE_PER_LINK,
                        xray_binary=engine_binary_path("xray"),
                    )
                    if handled:
                        self.send_json(payload, status)
                        return
                except Exception as e:
                    self.send_json({"error": f"Bad request: {e}"}, 400)
                    return

            if path == "/api/sync/xui":
                try:
                    body = json.loads(self.get_post_body())
                    link_id = body.get("link_id")
                    xui_url = body.get("url", "").rstrip("/")
                    xui_user = body.get("username")
                    xui_pass = body.get("password")
                    
                    if not link_id or link_id not in db.data["links"]:
                        self.send_json({"error": "Link not found"}, 404)
                        return
                    if not xui_url or not xui_user or not xui_pass:
                        self.send_json({"error": "Missing X-UI credentials"}, 400)
                        return

                    import urllib.request, urllib.parse, urllib.error
                    
                    # 1. Login
                    login_data = urllib.parse.urlencode({"username": xui_user, "password": xui_pass}).encode('utf-8')
                    login_req = urllib.request.Request(f"{xui_url}/login", data=login_data)
                    # Ignore SSL errors if using fake certs
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    
                    try:
                        resp = urllib.request.urlopen(login_req, context=ctx, timeout=10)
                        cookie = resp.headers.get('Set-Cookie')
                        if not cookie:
                            self.send_json({"error": "Login failed (No cookie returned)"}, 401)
                            return
                    except Exception as e:
                        self.send_json({"error": f"Failed to connect or login to X-UI: {e}"}, 400)
                        return

                    # 2. Fetch inbounds
                    list_req = urllib.request.Request(f"{xui_url}/panel/api/inbounds/list")
                    list_req.add_header('Cookie', cookie)
                    list_req.add_header('Accept', 'application/json')
                    
                    try:
                        resp = urllib.request.urlopen(list_req, context=ctx, timeout=10)
                        data = json.loads(resp.read().decode('utf-8'))
                        if not data.get("success"):
                            self.send_json({"error": "Failed to fetch inbounds from X-UI API"}, 400)
                            return
                        inbounds = data.get("obj", [])
                    except Exception as e:
                        self.send_json({"error": f"Failed to fetch inbounds: {e}"}, 400)
                        return

                    # 3. Extract active ports
                    ports = set()
                    for ib in inbounds:
                        if ib.get("enable"):
                            ports.add(int(ib.get("port")))
                    
                    if not ports:
                        self.send_json({"error": "No active inbounds found in X-UI panel"}, 400)
                        return

                    # 4. Map ports on the link
                    link = db.data["links"][link_id]
                    existing_ports = {p["user_port"] for p in link.get("ports", [])}
                    
                    added = 0
                    for port in ports:
                        if port not in existing_ports:
                            link.setdefault("ports", []).append({"user_port": port, "target_port": port})
                            added += 1

                    db.save()
                    db.log("panel", "info", f"Synced {added} new ports from X-UI panel to link '{link['name']}'.")
                    self.send_json({"success": True, "added": added, "total": len(ports)})
                except Exception as e:
                    self.send_json({"error": f"Error parsing request or syncing: {e}"}, 400)
                return

            if path == "/api/settings/network":
                try:
                    body = json.loads(self.get_post_body())
                    disable_ipv6 = body.get("disable_ipv6", False)
                    engine_restart_interval = body.get("engine_restart_interval", 0)
                    
                    db.data["settings"]["disable_ipv6"] = disable_ipv6
                    db.data["settings"]["engine_restart_interval"] = engine_restart_interval
                    db.save()
                    
                    ipv6_result = apply_ipv6_disabled(disable_ipv6)
                    db.log("panel", "info", f"Network settings updated. disable_ipv6={disable_ipv6}, engine_restart_interval={engine_restart_interval}, ipv6_applied={ipv6_result['success']}.")
                        
                    self.send_json({"success": True, "ipv6": ipv6_result, "engine_restart_interval": engine_restart_interval})
                except Exception as e:
                    self.send_json({"error": f"Failed: {e}"}, 500)
                return

            if path == "/api/settings/panel-ports":
                try:
                    if not submit_host_control:
                        raise RuntimeError("Host-control module is unavailable")
                    body = json.loads(self.get_post_body())
                    web_port = int(body.get("web_port") or 0)
                    api_port = int(body.get("api_port") or 0)
                    if not 1 <= web_port <= 65535 or not 1 <= api_port <= 65535:
                        raise ValueError("Panel and API ports must be between 1 and 65535")
                    if web_port == 22 or api_port == 22:
                        raise ValueError("Port 22 is reserved for SSH")
                    settings = db.data.get("settings", {})
                    panel_host = normalize_cert_host(
                        body.get("panel_host")
                        or settings.get("panel_host")
                        or self.headers.get("Host", "").split(":", 1)[0]
                    )
                    if not panel_host:
                        raise ValueError("A valid panel host or IP is required")
                    old_api_port = int(settings.get("api_port", 8000) or 8000)
                    handoff = {}
                    if api_port != old_api_port:
                        new_api_url = f"https://{panel_host}:{api_port}"
                        queued = queue_panel_handoff(new_api_url)
                        handoff = {
                            "queued": len(queued),
                            "results": wait_for_panel_handoff_results(queued, timeout=30),
                        }
                        handoff["acknowledged"] = sum(
                            1 for item in handoff["results"].values() if item.get("success")
                        )
                    result = submit_host_control(
                        CONFIG_DIR,
                        "panel_ports",
                        {
                            "web_port": web_port,
                            "api_port": api_port,
                            "host": panel_host,
                        },
                        delay_seconds=3,
                    )
                    db.log(
                        "panel",
                        "warning",
                        f"Queued panel port change: web={web_port}, api={api_port}, host={panel_host}.",
                    )
                    self.send_json({
                        **result,
                        "web_port": web_port,
                        "api_port": api_port,
                        "new_panel_url": f"https://{panel_host}:{web_port}",
                        "node_handoff": handoff,
                    })
                except Exception as e:
                    self.send_json({"error": f"Panel port change failed: {e}"}, 400)
                return

            if path == "/api/settings/panel-path":
                try:
                    body = json.loads(self.get_post_body())
                    enabled = bool(body.get("enabled", False))
                    raw_path = str(body.get("path") or "").strip()
                    if enabled and not raw_path:
                        raw_path = "/manage-" + secrets.token_hex(18)
                    if raw_path and not raw_path.startswith("/"):
                        raw_path = "/" + raw_path
                    if enabled and not re.fullmatch(r"/[A-Za-z0-9_-]{19,120}", raw_path):
                        raise ValueError(
                            "Hidden path must be 20-121 characters and contain only letters, numbers, dash, or underscore"
                        )
                    db.data.setdefault("settings", {})["hidden_panel_path_enabled"] = enabled
                    db.data["settings"]["hidden_panel_path"] = raw_path if enabled else ""
                    db.save()
                    host = str(self.headers.get("Host") or db.data["settings"].get("panel_host") or "")
                    access_path = raw_path if enabled else "/"
                    access_url = f"https://{host}{access_path}"
                    db.log(
                        "panel",
                        "warning",
                        f"Hidden management path {'enabled' if enabled else 'disabled'}.",
                    )
                    self.send_json({
                        "success": True,
                        "enabled": enabled,
                        "path": access_path,
                        "access_url": access_url,
                    })
                except Exception as e:
                    self.send_json({"error": f"Hidden panel path update failed: {e}"}, 400)
                return

            if path == "/api/settings/password":
                try:
                    body = json.loads(self.get_post_body())
                    username = body.get("username")
                    password = body.get("password")
                    if not username or not password:
                        self.send_json({"error": "Missing parameters"}, 400)
                        return

                    db.data["admin"]["username"] = username
                    db.data["admin"]["password_hash"] = hashlib.sha256(password.encode()).hexdigest()
                    db.save()
                    active_sessions.clear()
                    db.log("panel", "info", f"Admin credentials updated. Username changed to '{username}'. Sessions cleared.")
                    self.send_json({"success": True})
                except Exception:
                    self.send_json({"error": "Bad request"}, 400)
                return

            if path == "/api/settings/tls":
                try:
                    body = json.loads(self.get_post_body())
                    panel_tls = True
                    cert_path = body.get("cert_path", f"{CONFIG_DIR}/certs/cert.pem")
                    key_path = body.get("key_path", f"{CONFIG_DIR}/certs/key.pem")
                    if not cert_path or not key_path or not os.path.isfile(cert_path) or not os.path.isfile(key_path):
                        host = body.get("host") or db.data["settings"].get("panel_host") or "localhost"
                        cert_path, key_path = generate_local_panel_certificate(host, cert_path, key_path)
                        db.data["settings"]["cert_auto_generated"] = True
                    else:
                        db.data["settings"]["cert_auto_generated"] = False
                    db.data["settings"]["panel_tls"] = panel_tls
                    db.data["settings"]["cert_path"] = cert_path
                    db.data["settings"]["key_path"] = key_path
                    db.save()
                    db.log("panel", "info", "Panel SSL/TLS settings updated.")
                    self.send_json({"success": True})
                except Exception as e:
                    self.send_json({"error": f"Bad request: {e}"}, 400)
                return

            if path == "/api/settings/security":
                try:
                    body = json.loads(self.get_post_body())
                    enable_2fa = bool(body.get("two_factor_enabled", False))
                    enable_bio = bool(body.get("biometric_enabled", False))
                    if enable_2fa and not db.data["settings"].get("two_factor_secret"):
                        db.data["settings"]["two_factor_secret"] = make_totp_secret()
                    db.data["settings"]["two_factor_enabled"] = enable_2fa
                    db.data["settings"]["biometric_enabled"] = enable_bio
                    db.save()
                    db.log("panel", "info", f"Security options updated. 2FA={enable_2fa}, biometric={enable_bio}.")
                    self.send_json({
                        "success": True,
                        "two_factor_secret": db.data["settings"].get("two_factor_secret", "") if enable_2fa else ""
                    })
                except Exception as e:
                    self.send_json({"error": f"Bad request: {e}"}, 400)
                return

            if path == "/api/certificates/local":
                try:
                    body = json.loads(self.get_post_body())
                    host = normalize_cert_host(body.get("host", "localhost"))
                    if not host:
                        self.send_json({"error": "Valid IP or hostname is required"}, 400)
                        return
                    cert_path, key_path = generate_local_panel_certificate(host)
                    db.data["settings"]["cert_path"] = cert_path
                    db.data["settings"]["key_path"] = key_path
                    db.data["settings"]["panel_tls"] = True
                    db.data["settings"]["cert_auto_generated"] = True
                    db.save()
                    db.log("panel", "info", f"Generated local SSL certificate for {host}.")
                    self.send_json({"success": True, "cert_path": cert_path, "key_path": key_path})
                except FileNotFoundError:
                    self.send_json({"error": "openssl command not found"}, 500)
                except Exception as e:
                    self.send_json({"error": f"Local certificate failed: {e}"}, 500)
                return

            if path == "/api/profiles":
                try:
                    body = json.loads(self.get_post_body())
                    profile_id = str(body.get("id") or f"custom_{str(uuid.uuid4())[:8]}")
                    profile_id = "".join(ch for ch in profile_id if ch.isalnum() or ch in ("_", "-"))[:40] or f"custom_{str(uuid.uuid4())[:8]}"
                    profiles, _ = ensure_tunnel_profiles()
                    profiles[profile_id] = {
                        "name": str(body.get("name", profile_id))[:80],
                        "engine": body.get("engine", "builtin"),
                        "transport": body.get("transport", body.get("tunnel_mode", "websocket")),
                        "network": body.get("network", "tcp"),
                        "tunnel_mode": body.get("tunnel_mode", "websocket"),
                        "tls_enabled": bool(body.get("tls_enabled", True)),
                        "pool_size": clamp_int(body.get("pool_size", 4), 4, 1, MAX_POOL_SIZE_PER_LINK),
                        "obfs_host": str(body.get("obfs_host", "speedtest.net"))[:255],
                        "obfs_path": str(body.get("obfs_path", "/tunnel"))[:255],
                        "padding_min": clamp_int(body.get("padding_min", 0), 0, 0, 4096),
                        "padding_max": clamp_int(body.get("padding_max", 64), 64, 0, 4096),
                        "jitter_ms": clamp_int(body.get("jitter_ms", 0), 0, 0, 5000),
                        "keepalive_interval": clamp_int(body.get("keepalive_interval", 25), 25, 5, 300)
                    }
                    if profiles[profile_id]["engine"] not in VALID_TUNNEL_ENGINES:
                        self.send_json({"error": "Invalid tunnel engine"}, 400)
                        return
                    if profiles[profile_id]["tunnel_mode"] not in VALID_TUNNEL_MODES:
                        self.send_json({"error": "Invalid tunnel mode"}, 400)
                        return
                    if profiles[profile_id]["transport"] not in VALID_TUNNEL_TRANSPORTS:
                        self.send_json({"error": "Invalid transport"}, 400)
                        return
                    if not profiles[profile_id]["obfs_path"].startswith("/"):
                        profiles[profile_id]["obfs_path"] = "/" + profiles[profile_id]["obfs_path"]
                    profiles[profile_id]["padding_max"] = max(profiles[profile_id]["padding_min"], profiles[profile_id]["padding_max"])
                    profiles[profile_id].update(profile_decision_metadata(profile_id, profiles[profile_id]))
                    db.save()
                    db.log("panel", "info", f"Saved tunnel profile '{profiles[profile_id]['name']}'.")
                    self.send_json({"success": True, "profile_id": profile_id, "profiles": profiles})
                except Exception as e:
                    self.send_json({"error": f"Bad request: {e}"}, 400)
                return

            if path == "/api/profiles/import":
                try:
                    body = json.loads(self.get_post_body())
                    incoming = body.get("profiles", body)
                    if not isinstance(incoming, dict):
                        self.send_json({"error": "Invalid profile bundle"}, 400)
                        return
                    profiles = db.data["settings"].setdefault("tunnel_profiles", default_tunnel_profiles())
                    for profile_id, profile in incoming.items():
                        if isinstance(profile, dict):
                            safe_id = "".join(ch for ch in str(profile_id) if ch.isalnum() or ch in ("_", "-"))[:40]
                            if safe_id:
                                profiles[safe_id] = profile
                    db.save()
                    db.log("panel", "info", "Imported tunnel profile bundle.")
                    self.send_json({"success": True, "profiles": profiles})
                except Exception as e:
                    self.send_json({"error": f"Bad request: {e}"}, 400)
                return

            if path == "/api/certificates/generate":
                try:
                    body = json.loads(self.get_post_body())
                    domain = str(body.get("domain") or "").strip().lower()
                    email = str(body.get("email") or "").strip()
                    if not domain or not email:
                        self.send_json({"error": "Domain and email are required"}, 400)
                        return
                    if not submit_host_control:
                        raise RuntimeError("Host-control module is unavailable")
                    result = submit_host_control(
                        CONFIG_DIR,
                        "certificate",
                        {
                            "domain": domain,
                            "email": email,
                            "challenge": str(body.get("challenge") or "http-01"),
                            "wildcard": bool(body.get("wildcard", False)),
                            "dns_provider": str(body.get("dns_provider") or ""),
                            "dns_credentials": str(body.get("dns_credentials") or ""),
                            "dns_propagation_seconds": clamp_int(
                                body.get("dns_propagation_seconds", 30), 30, 10, 600
                            ),
                        },
                        wait_timeout=900,
                    )
                    if not result.get("success"):
                        raise RuntimeError(result.get("error") or "Certificate issuance failed")
                    db.data["settings"].update({
                        "panel_host": domain,
                        "cert_path": result.get("cert_path", f"{CONFIG_DIR}/certs/cert.pem"),
                        "key_path": result.get("key_path", f"{CONFIG_DIR}/certs/key.pem"),
                        "panel_tls": True,
                        "cert_auto_generated": False,
                        "letsencrypt_challenge": result.get("challenge", "http-01"),
                        "letsencrypt_wildcard": bool(result.get("wildcard", False)),
                    })
                    db.save()
                    db.log("panel", "info", f"Successfully generated SSL certificate for '{domain}' via host agent.")
                    self.send_json(result)
                except Exception as e:
                    db.log("panel", "error", f"Let's Encrypt failed: {e}")
                    self.send_json({"error": f"Let's Encrypt failed: {e}"}, 400)
                return

            if path == "/api/nodes/panel-local":
                try:
                    if not submit_host_control:
                        raise RuntimeError("Host-control module is unavailable")
                    body_text = self.get_post_body()
                    body = json.loads(body_text) if body_text else {}
                    existing = [
                        (node_id, node)
                        for node_id, node in db.data.get("nodes", {}).items()
                        if node.get("is_panel_node")
                    ]
                    if existing:
                        node_id, node = existing[0]
                        self.send_json({
                            "success": True,
                            "already_exists": True,
                            "node_id": node_id,
                            "node": sanitize_nodes_for_status({node_id: node})[node_id],
                        })
                        return
                    settings = db.data.get("settings", {})
                    host = normalize_cert_host(
                        body.get("host")
                        or settings.get("panel_host")
                        or self.headers.get("Host", "").split(":", 1)[0]
                    )
                    if not host:
                        raise ValueError("A valid public panel host or IP is required")
                    api_port = int(settings.get("api_port", 8000) or 8000)
                    node_id = f"node_panel_{secrets.token_hex(4)}"
                    node_token = f"tok_{secrets.token_hex(8)}"
                    private_key, public_key = make_node_keypair()
                    db.data.setdefault("nodes", {})[node_id] = {
                        "name": str(body.get("name") or "Panel Local Node")[:80],
                        "role": "internal",
                        "ip": host,
                        "token": node_token,
                        "public_key": public_key,
                        "private_key": private_key,
                        "status": "offline",
                        "last_seen": 0,
                        "tags": ["panel", "local", "internal"],
                        "category": "Panel",
                        "display_order": max(
                            [int(item.get("display_order", 0) or 0) for item in db.data.get("nodes", {}).values()] or [-1]
                        ) + 1,
                        "stats": {},
                        "is_panel_node": True,
                    }
                    db.save()
                    try:
                        result = submit_host_control(
                            CONFIG_DIR,
                            "panel_node",
                            {
                                "node_id": node_id,
                                "token": node_token,
                                "private_key": private_key,
                                "panel_url": f"https://127.0.0.1:{api_port}",
                            },
                            wait_timeout=90,
                        )
                        if not result.get("success"):
                            raise RuntimeError(result.get("error") or "Local panel node failed to start")
                    except Exception:
                        db.data.get("nodes", {}).pop(node_id, None)
                        db.save()
                        raise
                    db.log("panel", "warning", f"Added this panel host as local internal node '{node_id}'.")
                    self.send_json({
                        **result,
                        "node_id": node_id,
                        "token": node_token,
                        "private_key": private_key,
                    })
                except Exception as e:
                    self.send_json({"error": f"Panel node creation failed: {e}"}, 400)
                return

            if path == "/api/engines/install":
                try:
                    body = json.loads(self.get_post_body())
                    engine_type = body.get("engine")
                    version = body.get("version", "latest")
                    
                    if engine_type not in ENGINE_CATALOG:
                        self.send_json({"error": "Engine type not supported"}, 400)
                        return

                    def do_install_engine():
                        try:
                            db.log("panel", "info", f"Installing/updating engine {engine_type} from GitHub releases...")
                            result = install_engine_from_github(engine_type)
                            db.log("panel", "info", f"Successfully installed engine {engine_type}: {result.get('installed', [])}")
                        except Exception as e:
                            db.log("panel", "error", f"Failed to install engine {engine_type}: {e}")

                    threading.Thread(target=do_install_engine, daemon=True).start()
                    self.send_json({"success": True, "engine": engine_type, "version": version})
                except Exception as e:
                    self.send_json({"error": f"Bad request: {e}"}, 400)
                return

            if path == "/api/settings/restart":
                def do_restart():
                    time.sleep(1)
                    db.log("panel", "info", "Restarting P00RIJA PANEL server to apply changes...")
                    # Sanitize sys.argv for safe exec
                    safe_args = [sys.executable, os.path.abspath(APP_ENTRYPOINT)]
                    if "--panel" in sys.argv: safe_args.append("--panel")
                    if "--internal" in sys.argv: safe_args.append("--internal")
                    if "--external" in sys.argv: safe_args.append("--external")
                    os.execv(sys.executable, safe_args)
                
                threading.Thread(target=do_restart, daemon=True).start()
                self.send_json({"success": True})
                return

        if path.startswith("/api/"):
            self.send_json({"error": "API endpoint not found", "method": "POST", "path": path}, 404)
            return
        self.send_response(404)
        self.end_headers()

    def do_DELETE(self):
        parsed_url = urlparse(self.path)
        path = normalize_request_path(parsed_url.path)
        query = parse_qs(parsed_url.query)

        if path.startswith("/api/"):
            if not self.check_auth():
                self.send_json({"error": "Unauthorized"}, 401)
                return

            if path == "/api/nodes":
                node_id = query.get("id", [""])[0]
                if node_id in db.data["nodes"]:
                    node = db.data["nodes"].pop(node_id)
                    for lid in list(db.data["links"].keys()):
                        l = db.data["links"][lid]
                        if l["iran_node_id"] == node_id or l["foreign_node_id"] == node_id:
                            db.data["links"].pop(lid)
                    db.save()
                    db.log("panel", "info", f"Deleted node '{node['name']}' and its associated tunnel links.")
                    self.send_json({"success": True})
                else:
                    self.send_json({"error": "Node not found"}, 404)
                return

            if path in ("/api/links", "/api/links/ports") and dispatch_links_delete:
                handled, payload, status = dispatch_links_delete(
                    path,
                    query,
                    db_data=db.data,
                    save_db=db.save,
                    log_event=db.log,
                )
                if handled:
                    self.send_json(payload, status)
                    return

            if path == "/api/runtime/sessions":
                session_id = query.get("id", [""])[0]
                if close_runtime_session(session_id):
                    db.log("panel", "warning", f"Closed runtime bridge session {session_id}.")
                    self.send_json({"success": True})
                elif ":" in session_id:
                    node_id, raw_session_id = session_id.split(":", 1)
                    queued, detail = queue_node_session_close(node_id, raw_session_id)
                    if queued:
                        self.send_json({"success": True, "queued": True, "node_id": node_id, "command_id": detail})
                    else:
                        self.send_json({"error": detail}, 404)
                else:
                    self.send_json({"error": "Session not found"}, 404)
                return

            if path == "/api/runtime/processes":
                # Removed dangerous arbitrary process termination endpoint
                self.send_json({"error": "This endpoint has been disabled for security reasons"}, 403)
                return

        if path.startswith("/api/"):
            self.send_json({"error": "API endpoint not found", "method": "DELETE", "path": path}, 404)
            return
        self.send_response(404)
        self.end_headers()

# --------- CLI Setup Wizard ----------
