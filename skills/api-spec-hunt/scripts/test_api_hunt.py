#!/usr/bin/env python3
"""Offline regression tests for spec_hunt.py and spec_to_cli.py (no network).

Run: python3 test_api_hunt.py
"""
import importlib.util
import json
import os
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


hunt = load("spec_hunt")
gen = load("spec_to_cli")

FIXTURE = {
    "openapi": "3.0.4",
    "info": {"title": "Fixture API", "version": "1.2.3"},
    "servers": [{"url": "/api/v3"}],
    "paths": {
        "/pet": {"post": {"operationId": "addPet", "requestBody": {"content": {}}}},
        "/pet/{petId}": {
            "get": {"operationId": "getPetById",
                    "parameters": [{"name": "petId", "in": "path"},
                                   {"name": "verbose", "in": "query"}]},
        },
    },
}


class TestClassify(unittest.TestCase):
    def test_json_spec_detected(self):
        body = json.dumps(FIXTURE).encode()
        verdict, note = hunt.classify("openapi.json", 200, "application/json", body)
        self.assertEqual(verdict, "spec")
        self.assertIn("openapi=3.0.4", note)

    def test_gated_endpoint_reported(self):
        verdict, note = hunt.classify("api/", 401, "application/json", b"{}")
        self.assertEqual(verdict, "gated")

    def test_absent_on_404(self):
        self.assertEqual(hunt.classify("swagger.json", 404, "text/html", b"")[0], "absent")

    def test_swagger_ui_page_is_docs_ui(self):
        body = b"<html><body><div id='swagger-ui'>url: /openapi.json</div></body></html>"
        verdict, _ = hunt.classify("swagger-ui.html", 200, "text/html", body)
        self.assertEqual(verdict, "docs-ui")

    def test_json_but_not_a_spec(self):
        verdict, _ = hunt.classify("api/", 200, "application/json", b'{"hello": "world"}')
        self.assertEqual(verdict, "unknown")


class TestOperations(unittest.TestCase):
    def test_camel_case_slugging(self):
        self.assertEqual(gen.slug("addPet"), "add-pet")
        self.assertEqual(gen.slug("getUserByName"), "get-user-by-name")
        self.assertEqual(gen.slug("delete-pet-petId"), "delete-pet-pet-id")

    def test_operations_carry_path_and_query_params(self):
        ops = gen.operations_of(FIXTURE)
        self.assertIn("add-pet", ops)
        get = ops["get-pet-by-id"]
        self.assertEqual(get["method"], "GET")
        self.assertEqual(get["path"], "/pet/{petId}")
        self.assertEqual(get["path_params"], ["petId"])
        self.assertEqual(get["query"], ["verbose"])
        self.assertTrue(ops["add-pet"]["body"])

    def test_relative_server_url_is_returned_for_anchoring(self):
        self.assertEqual(gen.base_url_of(FIXTURE), "/api/v3")

    def test_swagger2_base_url(self):
        swagger2 = {"swagger": "2.0", "host": "api.example.com", "basePath": "/v1",
                    "schemes": ["http"]}
        self.assertEqual(gen.base_url_of(swagger2), "http://api.example.com/v1")

    def test_generated_cli_compiles(self):
        ops = gen.operations_of(FIXTURE)
        rendered = gen.TEMPLATE.format(title="Fixture API", version="1.2.3",
                                       base_url="https://example.test/api/v3",
                                       operations=ops, token_env="API_TOKEN")
        compile(rendered, "<generated>", "exec")
        self.assertIn("get-pet-by-id", rendered)


class TestVerify(unittest.TestCase):
    """spec_hunt.verify() is the gate before anything is called 'official'."""

    def _write(self, payload: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        self.addCleanup(os.unlink, path)
        return path

    def test_openapi3_fixture_verifies(self):
        self.assertTrue(hunt.verify(self._write(json.dumps(FIXTURE))))

    def test_swagger2_fixture_verifies(self):
        swagger2 = {"swagger": "2.0", "info": {"title": "Old API", "version": "1"},
                    "host": "api.example.com", "paths": {"/a": {}}}
        self.assertTrue(hunt.verify(self._write(json.dumps(swagger2))))

    def test_json_that_is_not_a_spec_fails(self):
        self.assertFalse(hunt.verify(self._write('{"hello": "world"}')))

    def test_unparseable_body_fails(self):
        self.assertFalse(hunt.verify(self._write("not json or yaml at all: [[[")))

    def test_unreachable_url_fails_without_raising(self):
        # .invalid never resolves (RFC 2606), so this exercises the transport path.
        self.assertFalse(hunt.verify("https://no-such-host.invalid/openapi.json"))


class TestUnreachableIsDistinct(unittest.TestCase):
    """A host that never answered must not be reported as 'no spec found'."""

    def test_classify_marks_dns_failure_unreachable_not_absent(self):
        verdict, note = hunt.classify("openapi.json", None, "", b"Name or service not known")
        self.assertEqual(verdict, "unreachable")
        self.assertIn("Name or service not known", note)


class TestNormalizeBase(unittest.TestCase):
    """A bare host must not blow up urlopen with 'unknown url type'."""

    def test_bare_host_gets_https(self):
        self.assertEqual(hunt.normalize_base("api.example.com"), "https://api.example.com")

    def test_explicit_http_scheme_is_honoured(self):
        self.assertEqual(hunt.normalize_base("http://192.168.1.10:8080"),
                         "http://192.168.1.10:8080")

    def test_trailing_slash_stripped(self):
        self.assertEqual(hunt.normalize_base("https://api.example.com/"), "https://api.example.com")


class TestYamlFallback(unittest.TestCase):
    def test_yaml_spec_verifies_with_or_without_pyyaml(self):
        yml = "openapi: 3.0.1\ninfo:\n  title: Yaml API\n  version: '1'\npaths:\n  /a: {}\n"
        self.assertTrue(hunt.verify(self._yaml_tmp(yml)))

    def _yaml_tmp(self, payload: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".yaml")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        self.addCleanup(os.unlink, path)
        return path


class TestLargeSpec(unittest.TestCase):
    """Regression: a spec over the old 400 KB scan cap must still be detected.

    Real specs are routinely >400 KB (a 50-path OpenAPI doc runs ~600 KB), and
    a truncating slice before json.loads misclassified them as "unknown".
    """

    def _big_spec(self) -> bytes:
        paths = {f"/resource{i}": {"get": {"summary": "x" * 200}} for i in range(3000)}
        return json.dumps({"openapi": "3.0.1",
                           "info": {"title": "Big API", "version": "1"},
                           "paths": paths}).encode()

    def test_classify_large_json_spec(self):
        body = self._big_spec()
        self.assertGreater(len(body), 400_000)
        verdict, note = hunt.classify("spec", 200, "text/plain", body)
        self.assertEqual(verdict, "spec")
        self.assertIn("openapi=3.0.1", note)

    def test_verify_large_json_spec(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "wb") as fh:
            fh.write(self._big_spec())
        self.addCleanup(os.unlink, path)
        self.assertTrue(hunt.verify(path))


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)