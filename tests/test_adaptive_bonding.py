import hashlib
import os
import socket
import tempfile
import threading
import unittest
import json
import subprocess
import tarfile
from queue import Queue
from unittest import mock


_state_dir = tempfile.mkdtemp(prefix="p00rija-bond-test-")
os.environ.setdefault("P00RIJA_CONFIG_DIR", _state_dir)
os.environ.setdefault("P00RIJA_DB_PATH", os.path.join(_state_dir, "db.json"))
os.environ.setdefault("P00RIJA_CONFIG_PATH", os.path.join(_state_dir, "config.json"))

import P00RIJA as app
from p00rija_core.links_api import dispatch_links_get, dispatch_links_post
from p00rija_core.backup_migration import (
    _remote_restore_script,
    build_encrypted_backup,
    migrate_backup_over_ssh,
    normalize_panel_url,
    restore_encrypted_backup,
)
from p00rija_core.engine_updates import check_engine_updates
from p00rija_core.versioning import node_version_status
from p00rija_core.host_control import (
    host_control_available,
    host_control_status,
    submit_host_control,
)


class AdaptiveBondingTests(unittest.TestCase):
    def dispatch_link(self, path, body, db_data):
        return dispatch_links_post(
            path,
            {},
            body,
            db_data=db_data,
            save_db=lambda: None,
            log_event=lambda *_args: None,
            default_tunnel_profiles=app.default_tunnel_profiles,
            normalize_tags=lambda value: list(value or []),
            clamp_int=app.clamp_int,
            valid_port=app.valid_port,
            role_matches=app.role_matches,
            valid_engines=app.VALID_TUNNEL_ENGINES,
            valid_modes=app.VALID_TUNNEL_MODES,
            valid_transports=app.VALID_TUNNEL_TRANSPORTS,
            max_pool_size_per_link=32,
        )

    def test_shared_mux_keeps_user_streams_isolated(self):
        link_a = {"running": True}
        link_b = {"running": True}
        app.init_link_lifecycle(link_a)
        app.init_link_lifecycle(link_b)
        wire_a, wire_b = socket.socketpair()
        echo_threads = []

        def open_echo(_target_port):
            mux_side, service_side = socket.socketpair()

            def echo():
                try:
                    while True:
                        chunk = service_side.recv(64 * 1024)
                        if not chunk:
                            break
                        service_side.sendall(chunk)
                    service_side.shutdown(socket.SHUT_WR)
                finally:
                    service_side.close()

            thread = threading.Thread(target=echo)
            thread.start()
            echo_threads.append(thread)
            return mux_side

        carrier_a = app.SharedMuxCarrier(wire_a, link_a, "mux-test", 0)
        carrier_b = app.SharedMuxCarrier(wire_b, link_b, "mux-test", 0, on_open=open_echo)
        readers = [
            threading.Thread(target=carrier_a.run),
            threading.Thread(target=carrier_b.run),
        ]
        for thread in readers:
            thread.start()

        payloads = [os.urandom(1024 * 1024 + index * 97) for index in range(8)]
        clients = []
        sessions = []
        for payload in payloads:
            client, mux_side = socket.socketpair()
            clients.append((client, payload))
            sessions.append(carrier_a.start_local_stream(mux_side, 443))

        received = []
        for client, payload in clients:
            client.sendall(payload)
            client.shutdown(socket.SHUT_WR)
            output = bytearray()
            while True:
                chunk = client.recv(64 * 1024)
                if not chunk:
                    break
                output.extend(chunk)
            client.close()
            received.append(bytes(output))

        for session in sessions:
            self.assertTrue(session.done.wait(10))
        self.assertEqual(received, payloads)

        link_a["running"] = False
        link_b["running"] = False
        carrier_a.close()
        carrier_b.close()
        for thread in readers + echo_threads:
            thread.join(5)
        self.assertFalse(any(thread.is_alive() for thread in readers + echo_threads))

    def test_six_carrier_mux_handles_one_hundred_concurrent_streams(self):
        client_link = {"running": True}
        server_link = {"running": True}
        app.init_link_lifecycle(client_link)
        app.init_link_lifecycle(server_link)
        pool = app.SharedMuxPool(client_link, "mux-100", 6)
        carriers = []
        carrier_threads = []
        echo_threads = []

        def open_echo(_target_port):
            mux_side, service_side = socket.socketpair()

            def echo():
                try:
                    while True:
                        chunk = service_side.recv(64 * 1024)
                        if not chunk:
                            break
                        service_side.sendall(chunk)
                    service_side.shutdown(socket.SHUT_WR)
                finally:
                    service_side.close()

            thread = threading.Thread(target=echo)
            thread.start()
            echo_threads.append(thread)
            return mux_side

        for carrier_id in range(6):
            wire_a, wire_b = socket.socketpair()
            local_carrier = app.SharedMuxCarrier(wire_a, client_link, "mux-100", carrier_id)
            remote_carrier = app.SharedMuxCarrier(wire_b, server_link, "mux-100", carrier_id, on_open=open_echo)
            pool.add_carrier(local_carrier)
            carriers.extend((local_carrier, remote_carrier))
            for carrier in (local_carrier, remote_carrier):
                thread = threading.Thread(target=carrier.run)
                thread.start()
                carrier_threads.append(thread)

        failures = []

        def client_job(index):
            payload = hashlib.sha256(f"stream-{index}".encode()).digest() * 2048
            client, mux_side = socket.socketpair()
            try:
                session = pool.open_stream(mux_side, 443)
                if session is None:
                    failures.append((index, "no-session"))
                    return
                client.sendall(payload)
                client.shutdown(socket.SHUT_WR)
                output = bytearray()
                while True:
                    chunk = client.recv(64 * 1024)
                    if not chunk:
                        break
                    output.extend(chunk)
                if bytes(output) != payload:
                    failures.append((index, "payload"))
                if not session.done.wait(10):
                    failures.append((index, "timeout"))
            except Exception as exc:
                failures.append((index, repr(exc)))
            finally:
                client.close()

        clients = [threading.Thread(target=client_job, args=(index,)) for index in range(100)]
        for thread in clients:
            thread.start()
        for thread in clients:
            thread.join(20)

        self.assertFalse(any(thread.is_alive() for thread in clients))
        self.assertFalse(failures)
        self.assertEqual(len(pool.live_carriers()), 6)
        self.assertTrue(all(carrier.streams_total > 0 for carrier in pool.live_carriers()))

        client_link["running"] = False
        server_link["running"] = False
        pool.close()
        for carrier in carriers:
            carrier.close()
        for thread in carrier_threads + echo_threads:
            thread.join(5)
        self.assertFalse(any(thread.is_alive() for thread in carrier_threads + echo_threads))

    def test_sixteen_lane_transfer_preserves_order_and_hash(self):
        payload = os.urandom(8 * 1024 * 1024 + 333)
        client, endpoint_a = socket.socketpair()
        endpoint_b, service = socket.socketpair()
        lane_pairs = [socket.socketpair() for _ in range(16)]
        lanes_a = [pair[0] for pair in lane_pairs]
        lanes_b = [pair[1] for pair in lane_pairs]
        errors = []

        def run_bridge(endpoint, lanes):
            try:
                app.bonded_bridge(endpoint, lanes, "bond-unittest", 443)
            except Exception as exc:
                errors.append(repr(exc))

        def service_worker():
            received = bytearray()
            try:
                while True:
                    chunk = service.recv(256 * 1024)
                    if not chunk:
                        break
                    received.extend(chunk)
                service.sendall(hashlib.sha256(received).digest())
                service.shutdown(socket.SHUT_WR)
            finally:
                service.close()

        threads = [
            threading.Thread(target=run_bridge, args=(endpoint_a, lanes_a)),
            threading.Thread(target=run_bridge, args=(endpoint_b, lanes_b)),
            threading.Thread(target=service_worker),
        ]
        for thread in threads:
            thread.start()

        client.sendall(payload)
        client.shutdown(socket.SHUT_WR)
        response = bytearray()
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            response.extend(chunk)
        client.close()

        for thread in threads:
            thread.join(15)

        self.assertEqual(bytes(response), hashlib.sha256(payload).digest())
        self.assertFalse(errors)
        self.assertFalse(any(thread.is_alive() for thread in threads))

    def test_lane_scheduler_uses_supported_steps_and_fair_share(self):
        pool = Queue()
        for _ in range(16):
            pool.put(object())
        link_data = {
            "_link_id": "scheduler-test",
            "pool": pool,
            "lifecycle_lock": threading.Lock(),
            "max_workers": 16,
            "bonded_lanes_in_use": 0,
        }
        with mock.patch.object(app, "count_active_bridge_sessions", return_value=0):
            self.assertEqual(app.adaptive_bond_lane_count(link_data, 16), 16)
            self.assertEqual(app.adaptive_bond_lane_count(link_data, 12), 12)
            self.assertEqual(app.adaptive_bond_lane_count(link_data, 10), 10)
            self.assertEqual(app.adaptive_bond_lane_count(link_data, 6), 6)
        with mock.patch.object(app, "count_active_bridge_sessions", return_value=1):
            self.assertEqual(app.adaptive_bond_lane_count(link_data, 16), 8)
        with mock.patch.object(app, "count_active_bridge_sessions", return_value=3):
            self.assertEqual(app.adaptive_bond_lane_count(link_data, 16), 4)

    def test_link_api_warms_selected_sixteen_lane_pool(self):
        db_data = {
            "nodes": {
                "internal": {"role": "internal", "status": "online"},
                "external": {"role": "external", "status": "online"},
            },
            "links": {},
            "settings": {"tunnel_profiles": app.default_tunnel_profiles()},
        }
        handled, payload, status = dispatch_links_post(
            "/api/links",
            {},
            {
                "name": "16 lane API test",
                "internal_node_id": "internal",
                "external_node_id": "external",
                "engine": "builtin",
                "transport": "reverse_tcp",
                "network": "tcp",
                "tunnel_mode": "reverse_tcp",
                "bridge_port": 7400,
                "sync_port": 7401,
                "pool_size": 4,
                "bonding_enabled": True,
                "bonding_max_lanes": 16,
            },
            db_data=db_data,
            save_db=lambda: None,
            log_event=lambda *_args: None,
            default_tunnel_profiles=app.default_tunnel_profiles,
            normalize_tags=lambda value: list(value or []),
            clamp_int=app.clamp_int,
            valid_port=app.valid_port,
            role_matches=app.role_matches,
            valid_engines=app.VALID_TUNNEL_ENGINES,
            valid_modes=app.VALID_TUNNEL_MODES,
            valid_transports=app.VALID_TUNNEL_TRANSPORTS,
            max_pool_size_per_link=32,
        )
        self.assertTrue(handled)
        self.assertEqual(status, 200)
        link = db_data["links"][payload["link_id"]]
        self.assertEqual(link["pool_size"], 16)
        self.assertEqual(link["max_reverse_workers"], 16)
        self.assertEqual(link["min_ready_workers"], 16)

    def test_link_api_configures_shared_mux_and_hybrid_budgets(self):
        for architecture, expected_workers in (("shared_mux", 3), ("smart_hybrid", 7)):
            db_data = {
                "nodes": {
                    "internal": {"role": "internal", "status": "online"},
                    "external": {"role": "external", "status": "online"},
                },
                "links": {},
                "settings": {"tunnel_profiles": app.default_tunnel_profiles()},
            }
            handled, payload, status = dispatch_links_post(
                "/api/links",
                {},
                {
                    "name": f"{architecture} API test",
                    "internal_node_id": "internal",
                    "external_node_id": "external",
                    "engine": "builtin",
                    "transport": "reverse_tcp",
                    "network": "tcp",
                    "tunnel_mode": "reverse_tcp",
                    "bridge_port": 7500,
                    "sync_port": 7501,
                    "data_plane_architecture": architecture,
                    "mux_carriers": 3,
                    "bonding_max_lanes": 4,
                },
                db_data=db_data,
                save_db=lambda: None,
                log_event=lambda *_args: None,
                default_tunnel_profiles=app.default_tunnel_profiles,
                normalize_tags=lambda value: list(value or []),
                clamp_int=app.clamp_int,
                valid_port=app.valid_port,
                role_matches=app.role_matches,
                valid_engines=app.VALID_TUNNEL_ENGINES,
                valid_modes=app.VALID_TUNNEL_MODES,
                valid_transports=app.VALID_TUNNEL_TRANSPORTS,
                max_pool_size_per_link=32,
            )
            self.assertTrue(handled)
            self.assertEqual(status, 200)
            link = db_data["links"][payload["link_id"]]
            self.assertEqual(link["data_plane_architecture"], architecture)
            self.assertEqual(link["mux_carriers"], 3)
            self.assertEqual(link["max_reverse_workers"], expected_workers)
            self.assertEqual(link["min_ready_workers"], expected_workers)

    def test_new_profiles_raise_mux_and_hybrid_capacity(self):
        profiles = app.default_tunnel_profiles()
        self.assertEqual(profiles["adaptive_bonding"]["bonding_max_lanes"], 8)
        self.assertEqual(profiles["shared_mux_pool"]["mux_carriers"], 4)
        self.assertEqual(profiles["smart_hybrid_mux_bonding"]["mux_carriers"], 6)
        self.assertEqual(profiles["smart_hybrid_mux_bonding"]["bonding_max_lanes"], 8)
        self.assertEqual(profiles["smart_hybrid_mux_bonding"]["pool_size"], 14)

    def test_every_bundled_profile_uses_supported_runtime_metadata(self):
        profiles = app.default_tunnel_profiles()
        self.assertGreaterEqual(len(profiles), 20)
        for profile_id, profile in profiles.items():
            with self.subTest(profile=profile_id):
                self.assertIn(profile.get("engine"), app.VALID_TUNNEL_ENGINES)
                self.assertIn(profile.get("tunnel_mode"), app.VALID_TUNNEL_MODES)
                self.assertIn(profile.get("transport"), app.VALID_TUNNEL_TRANSPORTS)
                self.assertIn(profile.get("network"), ("tcp", "udp", "tcp_udp"))
                self.assertGreaterEqual(int(profile.get("pool_size", 1)), 1)

    def test_easy_mode_can_auto_allocate_or_preserve_manual_free_ports(self):
        base_db = {
            "nodes": {
                "internal": {
                    "role": "internal",
                    "status": "online",
                    "stats": {"listening_tcp_ports": [7000, 7001]},
                },
                "external": {"role": "external", "status": "online", "stats": {}},
            },
            "links": {},
            "settings": {"tunnel_profiles": app.default_tunnel_profiles()},
        }
        auto_db = json.loads(json.dumps(base_db))
        handled, payload, status = self.dispatch_link(
            "/api/links",
            {
                "name": "easy auto ports",
                "internal_node_id": "internal",
                "external_node_id": "external",
                "easy_mode": True,
                "auto_allocate_ports": True,
                "bridge_port": 7000,
                "sync_port": 7001,
            },
            auto_db,
        )
        self.assertTrue(handled)
        self.assertEqual(status, 200)
        auto_link = auto_db["links"][payload["link_id"]]
        self.assertEqual((auto_link["bridge_port"], auto_link["sync_port"]), (7002, 7003))

        manual_db = json.loads(json.dumps(base_db))
        handled, payload, status = self.dispatch_link(
            "/api/links",
            {
                "name": "easy manual ports",
                "internal_node_id": "internal",
                "external_node_id": "external",
                "easy_mode": True,
                "auto_allocate_ports": False,
                "bridge_port": 7440,
                "sync_port": 7441,
            },
            manual_db,
        )
        self.assertTrue(handled)
        self.assertEqual(status, 200)
        manual_link = manual_db["links"][payload["link_id"]]
        self.assertEqual((manual_link["bridge_port"], manual_link["sync_port"]), (7440, 7441))

        collision_db = json.loads(json.dumps(base_db))
        handled, payload, status = self.dispatch_link(
            "/api/links",
            {
                "name": "easy occupied manual ports",
                "internal_node_id": "internal",
                "external_node_id": "external",
                "easy_mode": True,
                "auto_allocate_ports": False,
                "bridge_port": 7000,
                "sync_port": 7001,
            },
            collision_db,
        )
        self.assertTrue(handled)
        self.assertEqual(status, 409)
        self.assertIn("occupied", payload["error"])

    def test_generic_engine_preview_does_not_masquerade_as_xray(self):
        db_data = {
            "nodes": {"external": {"ip": "203.0.113.10"}},
            "links": {
                "builtin-link": {
                    "engine": "builtin",
                    "internal_node_id": "internal",
                    "external_node_id": "external",
                    "bridge_port": 7000,
                    "sync_port": 7001,
                    "transport": "websocket",
                    "tunnel_mode": "websocket",
                    "data_plane_architecture": "shared_mux",
                }
            },
        }
        handled, payload, status = dispatch_links_get(
            "/api/links/engine-config",
            {"id": ["builtin-link"]},
            db_data=db_data,
            save_db=lambda: None,
            log_event=lambda *_args: None,
            list_runtime_sessions=lambda: [],
            hysteria2_config_for_link=lambda *_args: {},
            muxquantum_config_for_link=lambda *_args: {},
            xray_config_for_link=lambda *_args: {"unexpected": "xray"},
        )
        self.assertTrue(handled)
        self.assertEqual(status, 200)
        self.assertEqual(payload["internal"]["engine"], "builtin")
        self.assertEqual(payload["internal"]["runtime"], "p00rija-builtin-compatible")
        self.assertNotIn("unexpected", payload["internal"])

    def test_adaptive_smux_changes_are_part_of_runtime_signature(self):
        controller = app.IranNodeController.__new__(app.IranNodeController)
        base = {
            "engine": "builtin",
            "data_plane_architecture": "shared_mux",
            "adaptive_smux_enabled": True,
            "smux_min_connections": 2,
            "smux_max_connections": 4,
            "smux_min_streams": 8,
        }
        changed = {**base, "smux_max_connections": 8}
        self.assertNotEqual(controller.link_signature(base), controller.link_signature(changed))

    def test_link_api_accepts_eight_mux_carriers(self):
        db_data = {
            "nodes": {
                "internal": {"role": "internal", "status": "online"},
                "external": {"role": "external", "status": "online"},
            },
            "links": {},
            "settings": {"tunnel_profiles": app.default_tunnel_profiles()},
        }
        handled, payload, status = self.dispatch_link(
            "/api/links",
            {
                "name": "eight carrier mux",
                "internal_node_id": "internal",
                "external_node_id": "external",
                "engine": "builtin",
                "transport": "reverse_tcp",
                "network": "tcp",
                "tunnel_mode": "reverse_tcp",
                "bridge_port": 7600,
                "sync_port": 7601,
                "data_plane_architecture": "shared_mux",
                "mux_carriers": 8,
            },
            db_data,
        )
        self.assertTrue(handled)
        self.assertEqual(status, 200)
        link = db_data["links"][payload["link_id"]]
        self.assertEqual(link["mux_carriers"], 8)
        self.assertEqual(link["pool_size"], 8)

    def test_node_version_compatibility_states(self):
        nodes = {
            "current": {
                "status": "online", "last_seen": 9999999999,
                "stats": {"app_version": app.APP_VERSION, "app_build": app.APP_BUILD},
            },
            "old": {
                "status": "online", "last_seen": 9999999999,
                "stats": {"app_version": "1.9.7", "app_build": "old"},
            },
            "incompatible": {
                "status": "online", "last_seen": 9999999999,
                "stats": {"app_version": "1.8.9", "app_build": "old"},
            },
        }
        result = node_version_status(nodes, app.APP_VERSION, app.APP_BUILD)
        self.assertEqual(result["nodes"]["current"]["state"], "current")
        self.assertEqual(result["nodes"]["old"]["state"], "outdated")
        self.assertEqual(result["nodes"]["incompatible"]["state"], "incompatible")

    def test_engine_update_checker_compares_release_tags(self):
        catalog = {"xray": {"repo": "XTLS/Xray-core", "bins": ["xray"]}}
        manifest = {"engines": {"xray": {"tag": "v1.0.0"}}}
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        response.read.return_value = json.dumps({"tag_name": "v1.1.0"}).encode()
        response.headers.items.return_value = [("X-RateLimit-Remaining", "50")]
        with mock.patch("urllib.request.urlopen", return_value=response):
            result = check_engine_updates(catalog, manifest, engine_id="xray", cache_seconds=0)
        self.assertTrue(result["engines"]["xray"]["reachable"])
        self.assertTrue(result["engines"]["xray"]["update_available"])

    def test_edit_allows_the_active_link_to_keep_its_own_runtime_ports(self):
        existing = {
            "name": "Existing tunnel",
            "internal_node_id": "internal",
            "external_node_id": "external",
            "direction": "external_to_internal",
            "engine": "builtin",
            "transport": "reverse_tcp",
            "network": "tcp",
            "tunnel_mode": "reverse_tcp",
            "bridge_port": 6666,
            "sync_port": 6591,
            "pool_size": 80,
            "ports": [],
        }
        db_data = {
            "nodes": {
                "internal": {
                    "role": "internal",
                    "status": "online",
                    "stats": {"listening_tcp_ports": [6666, 6591, 9990]},
                },
                "external": {
                    "role": "external",
                    "status": "online",
                    "stats": {"listening_tcp_ports": [6666]},
                },
            },
            "links": {"link_existing": dict(existing)},
            "settings": {"tunnel_profiles": app.default_tunnel_profiles()},
        }
        handled, payload, status = self.dispatch_link(
            "/api/links/edit",
            {**existing, "id": "link_existing", "name": "Existing tunnel edited"},
            db_data,
        )
        self.assertTrue(handled)
        self.assertEqual(status, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(db_data["links"]["link_existing"]["bridge_port"], 6666)
        self.assertEqual(db_data["links"]["link_existing"]["sync_port"], 6591)
        self.assertEqual(db_data["links"]["link_existing"]["pool_size"], 80)

    def test_edit_still_rejects_a_different_runtime_listener(self):
        existing = {
            "name": "Existing tunnel",
            "internal_node_id": "internal",
            "external_node_id": "external",
            "direction": "external_to_internal",
            "engine": "builtin",
            "transport": "reverse_tcp",
            "network": "tcp",
            "tunnel_mode": "reverse_tcp",
            "bridge_port": 6666,
            "sync_port": 6591,
            "pool_size": 4,
            "ports": [],
        }
        db_data = {
            "nodes": {
                "internal": {
                    "role": "internal",
                    "status": "online",
                    "stats": {"listening_tcp_ports": [6666, 6591, 7777]},
                },
                "external": {"role": "external", "status": "online", "stats": {}},
            },
            "links": {"link_existing": dict(existing)},
            "settings": {"tunnel_profiles": app.default_tunnel_profiles()},
        }
        handled, payload, status = self.dispatch_link(
            "/api/links/edit",
            {**existing, "id": "link_existing", "bridge_port": 7777},
            db_data,
        )
        self.assertTrue(handled)
        self.assertEqual(status, 409)
        self.assertIn("already occupied", payload["error"])

    def test_edit_still_rejects_ports_reserved_by_another_link(self):
        existing = {
            "name": "Existing tunnel",
            "internal_node_id": "internal",
            "external_node_id": "external",
            "direction": "external_to_internal",
            "engine": "builtin",
            "transport": "reverse_tcp",
            "network": "tcp",
            "tunnel_mode": "reverse_tcp",
            "bridge_port": 6666,
            "sync_port": 6591,
            "pool_size": 4,
            "ports": [],
        }
        db_data = {
            "nodes": {
                "internal": {
                    "role": "internal",
                    "status": "online",
                    "stats": {"listening_tcp_ports": [6666, 6591]},
                },
                "external": {"role": "external", "status": "online", "stats": {}},
            },
            "links": {
                "link_existing": dict(existing),
                "link_other": {
                    **existing,
                    "name": "Other tunnel",
                    "bridge_port": 7777,
                    "sync_port": 7778,
                },
            },
            "settings": {"tunnel_profiles": app.default_tunnel_profiles()},
        }
        handled, payload, status = self.dispatch_link(
            "/api/links/edit",
            {**existing, "id": "link_existing", "bridge_port": 7777},
            db_data,
        )
        self.assertTrue(handled)
        self.assertEqual(status, 409)
        self.assertIn("already occupied", payload["error"])

    def test_portable_backup_is_encrypted_and_contains_panel_state(self):
        with tempfile.TemporaryDirectory(prefix="p00rija-portable-backup-") as root:
            config_dir = os.path.join(root, "panel")
            app_root = os.path.join(root, "app")
            os.makedirs(os.path.join(config_dir, "certs"))
            os.makedirs(os.path.join(app_root, "p00rija_core"))
            os.makedirs(os.path.join(app_root, "fonts"))
            with open(os.path.join(config_dir, "p00rija_config.json"), "w") as output:
                json.dump({"role": "panel", "port": 9990, "api_port": 8000}, output)
            with open(os.path.join(config_dir, "p00rija_db.json"), "w") as output:
                json.dump({"nodes": {"n1": {}}, "links": {"l1": {}}, "settings": {}}, output)
            for path, content in (
                (os.path.join(config_dir, "panel_secret"), "secret"),
                (os.path.join(config_dir, "certs", "cert.pem"), "certificate"),
                (os.path.join(app_root, "P00RIJA.py"), "print('ok')\n"),
                (os.path.join(app_root, "download_engines.py"), "print('engines')\n"),
                (os.path.join(app_root, "p00rija_core", "__init__.py"), ""),
            ):
                with open(path, "w") as output:
                    output.write(content)
            result = build_encrypted_backup(
                config_dir=config_dir,
                app_root=app_root,
                engines_dir=os.path.join(root, "engines"),
                password="backup-password",
                app_version="test",
                app_build="test-build",
                include_engines=False,
            )
            self.assertGreater(result["size"], 0)
            plain = os.path.join(root, "plain.tar.gz")
            proc = subprocess.run(
                [
                    "openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "200000",
                    "-pass", "stdin", "-in", result["path"], "-out", plain,
                ],
                input=b"backup-password",
                capture_output=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr.decode(errors="replace"))
            with tarfile.open(plain, "r:gz") as archive:
                names = set(archive.getnames())
            self.assertIn("p00rija-panel-backup/state/p00rija_db.json", names)
            self.assertIn("p00rija-panel-backup/state/panel_secret", names)
            self.assertIn("p00rija-panel-backup/state/certs/cert.pem", names)
            self.assertIn("p00rija-panel-backup/app/P00RIJA.py", names)
            self.assertIn("p00rija-panel-backup/restore-panel.sh", names)

    def test_local_restore_replaces_state_and_creates_rollback_snapshot(self):
        with tempfile.TemporaryDirectory(prefix="p00rija-local-restore-") as root:
            config_dir = os.path.join(root, "panel")
            app_root = os.path.join(root, "app")
            os.makedirs(config_dir)
            os.makedirs(os.path.join(app_root, "p00rija_core"))
            os.makedirs(os.path.join(app_root, "fonts"))
            original_db = {"nodes": {"restored": {"name": "restored node"}}, "links": {}, "settings": {}}
            with open(os.path.join(config_dir, "p00rija_config.json"), "w") as output:
                json.dump({"role": "panel", "port": 9990, "api_port": 8000}, output)
            with open(os.path.join(config_dir, "p00rija_db.json"), "w") as output:
                json.dump(original_db, output)
            with open(os.path.join(app_root, "P00RIJA.py"), "w") as output:
                output.write("APP_VERSION = 'test'\n")
            backup = build_encrypted_backup(
                config_dir=config_dir,
                app_root=app_root,
                engines_dir=os.path.join(root, "engines"),
                password="restore-password",
                app_version=app.APP_VERSION,
                app_build="restore-test",
                include_engines=False,
            )
            with open(os.path.join(config_dir, "p00rija_db.json"), "w") as output:
                json.dump({"nodes": {"current": {}}, "links": {}, "settings": {}}, output)
            result = restore_encrypted_backup(
                backup_path=backup["path"],
                password="restore-password",
                config_dir=config_dir,
            )
            with open(os.path.join(config_dir, "p00rija_db.json")) as source:
                restored = json.load(source)
            self.assertIn("restored", restored["nodes"])
            self.assertTrue(os.path.isdir(result["rollback_path"]))
            with open(os.path.join(result["rollback_path"], "p00rija_db.json")) as source:
                rollback = json.load(source)
            self.assertIn("current", rollback["nodes"])
            self.assertEqual(result["manifest"]["app_build"], "restore-test")

    def test_remote_migration_explicitly_invokes_bash_for_fish_login_shells(self):
        self.assertTrue(_remote_restore_script().startswith("#!/usr/bin/env bash\nset -euo pipefail"))
        with tempfile.NamedTemporaryFile() as backup:
            calls = []

            def fake_run(command, **kwargs):
                calls.append(command)
                if command[-1] == "id -u":
                    return subprocess.CompletedProcess(command, 0, stdout="0\n", stderr="")
                return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

            with mock.patch("p00rija_core.backup_migration.shutil.which", return_value="/usr/bin/sshpass"):
                with mock.patch("p00rija_core.backup_migration.subprocess.run", side_effect=fake_run):
                    result = migrate_backup_over_ssh(
                        backup_path=backup.name,
                        backup_password="restore-password",
                        host="203.0.113.10",
                        port=22,
                        username="root",
                        password="ssh-password",
                        new_panel_url="https://panel.example.com:8000",
                    )
            self.assertTrue(result["success"])
            remote_commands = [command[-1] for command in calls if command and isinstance(command[-1], str)]
            self.assertTrue(any(command.startswith("/bin/bash /tmp/p00rija-migration-") for command in remote_commands))
            self.assertFalse(any(command.startswith("set -e;") for command in remote_commands))

    def test_link_guardian_is_lightweight_and_does_not_close_idle_user_sessions(self):
        class FakeSession:
            link_id = "link_guard"
            last_activity = 0
            closed = False

            def close(self):
                self.closed = True

        session = FakeSession()
        original_controller = app.runtime_controller
        try:
            app.runtime_controller = None
            with app.active_bridges_lock:
                app.active_bridges["guardian-session"] = session
            with mock.patch.object(app.time, "time", return_value=1000):
                result = app.optimize_runtime_resources("thread_guard", link_id="link_guard")
            self.assertEqual(result["closed_idle_sessions"], 0)
            self.assertFalse(session.closed)
            with app.active_bridges_lock:
                self.assertIn("guardian-session", app.active_bridges)
        finally:
            with app.active_bridges_lock:
                app.active_bridges.pop("guardian-session", None)
            app.runtime_controller = original_controller

    def test_pressure_optimizer_preserves_sessions_when_pressure_is_normal(self):
        class FakeSession:
            link_id = "link_pressure"
            last_activity = 0
            closed = False

            def close(self):
                self.closed = True

        session = FakeSession()
        original_controller = app.runtime_controller
        try:
            app.runtime_controller = None
            with app.active_bridges_lock:
                app.active_bridges["pressure-session"] = session
            with mock.patch.object(app.time, "time", return_value=1000):
                with mock.patch.object(app.threading, "active_count", return_value=10):
                    with mock.patch.object(app, "get_own_rss_kb", return_value=64 * 1024):
                        with mock.patch.object(app, "get_ram_percent", return_value=20):
                            result = app.optimize_runtime_resources("pressure", link_id="link_pressure")
            self.assertEqual(result["pressure_level"], "normal")
            self.assertEqual(result["closed_idle_sessions"], 0)
            self.assertFalse(session.closed)
        finally:
            with app.active_bridges_lock:
                app.active_bridges.pop("pressure-session", None)
            app.runtime_controller = original_controller

    def test_guardian_keeps_active_sessions_plus_ready_reserve(self):
        self.assertEqual(app.desired_reverse_workers(16, active_sessions=5, min_ready=2), 7)
        with mock.patch.object(app.threading, "active_count", return_value=app.THREAD_PRESSURE_HARD + 1):
            self.assertEqual(app.desired_reverse_workers(16, active_sessions=5, min_ready=2), 6)

    def test_node_optimizer_commands_are_deduplicated(self):
        original_nodes = app.db.data.get("nodes")
        original_commands = app.db.data.get("node_commands")
        try:
            now = app.time.time()
            app.db.data["nodes"] = {
                "node_one": {"status": "online", "last_seen": now, "name": "Node One"}
            }
            app.db.data["node_commands"] = {}
            first = app.queue_node_optimization("gc")
            second = app.queue_node_optimization("gc")
            self.assertEqual(first, 1)
            self.assertEqual(second, 0)
            self.assertEqual(len(app.db.data["node_commands"]["node_one"]), 1)
        finally:
            if original_nodes is None:
                app.db.data.pop("nodes", None)
            else:
                app.db.data["nodes"] = original_nodes
            if original_commands is None:
                app.db.data.pop("node_commands", None)
            else:
                app.db.data["node_commands"] = original_commands

    def test_host_control_request_bridge_and_status(self):
        with tempfile.TemporaryDirectory(prefix="p00rija-host-control-") as root:
            control = os.path.join(root, "host_control")
            os.makedirs(os.path.join(control, "requests"))
            os.makedirs(os.path.join(control, "results"))
            with open(os.path.join(control, "agent-heartbeat.json"), "w") as output:
                json.dump({"timestamp": app.time.time()}, output)
            self.assertTrue(host_control_available(root))
            queued = submit_host_control(
                root,
                "panel_ports",
                {"web_port": 9443, "api_port": 9000},
            )
            self.assertTrue(queued["queued"])
            request_path = os.path.join(control, "requests", f"{queued['request_id']}.json")
            with open(request_path) as source:
                request = json.load(source)
            self.assertEqual(request["action"], "panel_ports")
            self.assertEqual(request["payload"]["web_port"], 9443)
            pending = host_control_status(root, queued["request_id"])
            self.assertTrue(pending["pending"])
            with open(os.path.join(control, "results", f"{queued['request_id']}.json"), "w") as output:
                json.dump({"success": True, "pending": False, "web_port": 9443}, output)
            result = host_control_status(root, queued["request_id"])
            self.assertTrue(result["success"])
            self.assertFalse(result["pending"])

    def test_hidden_panel_path_requires_signed_gate_cookie(self):
        settings = app.db.data.setdefault("settings", {})
        old_enabled = settings.get("hidden_panel_path_enabled")
        old_path = settings.get("hidden_panel_path")
        try:
            settings["hidden_panel_path_enabled"] = True
            settings["hidden_panel_path"] = "/manage-1234567890abcdef1234567890"
            handler = object.__new__(app.P00RIJAHTTPHandler)
            handler.headers = {}
            self.assertTrue(handler.is_panel_page_path("/manage-1234567890abcdef1234567890"))
            self.assertFalse(handler.is_panel_page_path("/"))
            self.assertFalse(handler.has_panel_gate())
            handler.headers = {"Cookie": f"p00rija_panel_gate={handler.panel_gate_value()}"}
            self.assertTrue(handler.has_panel_gate())
        finally:
            if old_enabled is None:
                settings.pop("hidden_panel_path_enabled", None)
            else:
                settings["hidden_panel_path_enabled"] = old_enabled
            if old_path is None:
                settings.pop("hidden_panel_path", None)
            else:
                settings["hidden_panel_path"] = old_path

    def test_panel_handoff_writes_new_endpoint_and_fallback_atomically(self):
        original_path = app.CONFIG_PATH
        try:
            with tempfile.TemporaryDirectory(prefix="p00rija-handoff-") as root:
                app.CONFIG_PATH = os.path.join(root, "p00rija_config.json")
                with open(app.CONFIG_PATH, "w") as output:
                    json.dump(
                        {"role": "internal", "panel_url": "https://old.example.com:8000", "token": "t"},
                        output,
                    )
                result = app.apply_panel_handoff(
                    "https://new.example.com:8000",
                    "https://old.example.com:8000",
                )
                with open(app.CONFIG_PATH) as source:
                    saved = json.load(source)
                self.assertTrue(result["success"])
                self.assertEqual(saved["panel_url"], "https://new.example.com:8000")
                self.assertEqual(saved["panel_fallback_url"], "https://old.example.com:8000")
                self.assertFalse(os.path.exists(f"{app.CONFIG_PATH}.handoff.tmp"))
        finally:
            app.CONFIG_PATH = original_path

    def test_panel_fallback_recovers_to_primary_without_becoming_sticky(self):
        controller = app.ForeignNodeController(
            "https://new.example.com:8000",
            "token",
            fallback_panel_url="https://old.example.com:8000",
        )
        attempts = []
        now = [100.0]
        primary_failed_once = [False]

        def request(endpoint, *_args, **_kwargs):
            attempts.append(endpoint)
            if endpoint == "https://new.example.com:8000" and not primary_failed_once[0]:
                primary_failed_once[0] = True
                raise RuntimeError("primary temporarily unavailable")
            return endpoint.encode()

        with mock.patch.object(app, "make_panel_request", side_effect=request), mock.patch.object(
            app.time, "monotonic", side_effect=lambda: now[0]
        ):
            self.assertEqual(
                controller.panel_request("/api/report"),
                b"https://old.example.com:8000",
            )
            self.assertEqual(controller.primary_panel_url, "https://new.example.com:8000")
            self.assertEqual(controller.panel_url, "https://old.example.com:8000")
            self.assertTrue(controller.panel_endpoint_status()["using_fallback"])

            attempts.clear()
            now[0] = 102.0
            self.assertEqual(
                controller.panel_request("/api/report"),
                b"https://old.example.com:8000",
            )
            self.assertEqual(attempts, ["https://old.example.com:8000"])

            attempts.clear()
            now[0] = 106.0
            self.assertEqual(
                controller.panel_request("/api/report"),
                b"https://new.example.com:8000",
            )
            self.assertEqual(attempts, ["https://new.example.com:8000"])
            self.assertEqual(controller.panel_url, "https://new.example.com:8000")
            self.assertFalse(controller.panel_endpoint_status()["using_fallback"])

            controller._record_panel_success("https://old.example.com:8000")
            self.assertEqual(controller.panel_url, "https://new.example.com:8000")
            self.assertFalse(controller.panel_endpoint_status()["using_fallback"])

    def test_panel_url_validation_rejects_credentialed_urls(self):
        self.assertEqual(
            normalize_panel_url("https://panel.example.com:8000/"),
            "https://panel.example.com:8000",
        )
        self.assertEqual(
            normalize_panel_url(
                "https://panel.example.com:9990/manage-1234567890abcdef"
            ),
            "https://panel.example.com:9990",
        )
        self.assertEqual(
            app.normalize_node_panel_url(
                "https://panel.example.com:9990/manage-1234567890abcdef"
            ),
            "https://panel.example.com:9990",
        )
        with self.assertRaises(ValueError):
            normalize_panel_url("https://root:secret@panel.example.com:8000")

    def test_transport_2026_profiles_build_real_engine_configs(self):
        base = {
            "bridge_port": 8443,
            "ports": [{"target_port": 51820}],
            "xray_uuid": "11111111-1111-1111-1111-111111111111",
            "xray_private_key": "private",
            "xray_public_key": "public",
            "xray_shortid": "0123456789abcdef",
            "xray_sni": "example.com",
            "tls_sni": "example.com",
            "obfs_path": "/transport",
            "external_ip": "203.0.113.10",
        }
        xray = app.xray_config_for_link({**base, "transport": "xhttp", "tunnel_mode": "xhttp"}, "internal")
        stream = xray["outbounds"][0]["streamSettings"]
        self.assertEqual(stream["network"], "xhttp")
        self.assertEqual(stream["xhttpSettings"]["path"], "/transport")

        singbox = app.singbox_config_for_link({
            **base,
            "ech_enabled": True,
            "ech_config": "ECH-CONFIG",
            "smux_max_connections": 6,
            "tcp_brutal_enabled": True,
            "tcp_brutal_up_mbps": 40,
            "tcp_brutal_down_mbps": 80,
        }, "internal")
        outbound = singbox["outbounds"][0]
        self.assertTrue(outbound["tls"]["ech"]["enabled"])
        self.assertEqual(outbound["multiplex"]["max_connections"], 6)
        self.assertEqual(outbound["multiplex"]["brutal"]["down_mbps"], 80)

        masque = app.masque_config_for_link({**base, "masque_mode": "connect-ip"}, "internal")
        self.assertEqual(masque["protocol"], "CONNECT-IP")
        self.assertTrue(masque["connect_ip"])

    def test_node_and_tunnel_reordering_is_persisted(self):
        node_db = {
            "nodes": {
                "n1": {"name": "one", "role": "internal", "ip": "1.1.1.1"},
                "n2": {"name": "two", "role": "external", "ip": "2.2.2.2"},
            }
        }
        handled, payload, status = app.dispatch_nodes_post(
            "/api/nodes/reorder",
            {"order": ["n2", "n1"]},
            db_data=node_db,
            node_api_key="key",
            client_ip="127.0.0.1",
            normalize_role=app.normalize_role,
            normalize_tags=app.normalize_tags,
            make_node_keypair=app.make_node_keypair,
            save_db=lambda: None,
            log_event=lambda *_args: None,
        )
        self.assertTrue(handled)
        self.assertEqual(status, 200)
        self.assertEqual(node_db["nodes"]["n2"]["display_order"], 0)
        self.assertEqual(payload["order"], ["n2", "n1"])

    def test_smart_profile_objective_changes_weighting(self):
        profile = {
            "name": "Objective profile",
            "engine": "xray",
            "network": "tcp",
            "transport": "xhttp",
            "tunnel_mode": "xhttp",
            "ratings": {"speed": "excellent", "stability": "good", "security": "excellent"},
        }
        path = {"avg_ms": 80, "loss": 1, "pressure": 20, "throughput_mbps": 250}
        speed = app.score_tunnel_profile("objective", profile, path, objective="speed")
        security = app.score_tunnel_profile("objective", profile, path, objective="security")
        self.assertEqual(speed["objective"], "speed")
        self.assertEqual(security["objective"], "security")
        self.assertNotEqual(speed["total_score"], security["total_score"])

    def test_speedtest_job_rejects_invalid_mode(self):
        with self.assertRaises(ValueError):
            app.start_speedtest_job({"mode": "invalid", "node_ids": []})

    def test_speedtest_preflight_waits_for_first_run_install(self):
        original_data = app.db.data
        app.db.data = {
            "nodes": {
                "source": {
                    "name": "Source",
                    "status": "online",
                    "last_seen": 9999999999,
                    "stats": {"transport_capabilities": {"iperf3": False}},
                },
                "target": {
                    "name": "Target",
                    "status": "online",
                    "last_seen": 9999999999,
                    "stats": {"transport_capabilities": {"iperf3": True}},
                },
            },
            "node_commands": {},
        }
        try:
            with mock.patch.object(app, "queue_speedtest_command", return_value="install-command") as queue:
                with mock.patch.object(app, "wait_for_node_command_result", return_value={
                    "id": "install-command",
                    "result": {"success": True, "binary": "/usr/bin/iperf3"},
                }) as wait:
                    result = app.ensure_speedtest_nodes_ready(("source", "target"), timeout=660)
            queue.assert_called_once_with("source", "speedtest_iperf_install")
            wait.assert_called_once_with("source", "install-command", timeout=660)
            self.assertTrue(result["source"]["success"])
        finally:
            app.db.data = original_data

    def test_pair_speedtest_always_queues_server_cleanup(self):
        original_data = app.db.data
        app.db.data = {
            "nodes": {
                "source": {
                    "name": "Source",
                    "ip": "192.0.2.10",
                    "status": "online",
                    "last_seen": 9999999999,
                    "stats": {"transport_capabilities": {"iperf3": True}},
                },
                "target": {
                    "name": "Target",
                    "ip": "192.0.2.20",
                    "status": "online",
                    "last_seen": 9999999999,
                    "stats": {"transport_capabilities": {"iperf3": True}},
                },
            },
            "node_commands": {},
        }
        commands = []

        def queue(node_id, command_type, **payload):
            commands.append((node_id, command_type, payload))
            return {"speedtest_iperf_server": "server-command", "speedtest_iperf_client": "client-command"}.get(
                command_type, "stop-command"
            )

        def wait(_node_id, command_id, timeout):
            if command_id == "server-command":
                return {"id": command_id, "result": {"success": True, "network_mode": "host"}}
            return {
                "id": command_id,
                "result": {
                    "success": True,
                    "upload_mbps": 100,
                    "download_mbps": 100,
                },
            }

        try:
            with mock.patch.object(app, "queue_speedtest_command", side_effect=queue):
                with mock.patch.object(app, "wait_for_node_command_result", side_effect=wait):
                    result = app.run_node_pair_iperf_test(
                        "source",
                        "target",
                        {"port": 5201, "duration": 2, "_iperf_preflight_done": True},
                    )
            self.assertTrue(result["success"])
            self.assertEqual(commands[-1][1], "speedtest_iperf_stop")
            self.assertEqual(commands[-1][2]["server_id"], "server-command")
            self.assertEqual(commands[-1][2]["port"], 5201)
        finally:
            app.db.data = original_data


if __name__ == "__main__":
    unittest.main()
