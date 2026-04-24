import os
import tempfile
import unittest
from pathlib import Path

from aegis.shell.config import (
    DEFAULT_BASE_URL,
    ENV_API_KEY,
    ENV_BASE_URL,
    load_user_config,
    resolve_runtime_config,
    write_user_config,
)


class TestShellConfig(unittest.TestCase):
    def test_read_write_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ".aegis" / "config.json"
            write_user_config(api_key="k1", base_url="http://localhost:9000", path=path)

            payload = load_user_config(path=path)
            self.assertEqual(payload["api_key"], "k1")
            self.assertEqual(payload["base_url"], "http://localhost:9000")

    def test_runtime_config_env_overrides(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ".aegis" / "config.json"
            write_user_config(api_key="file-key", base_url="http://from-file", path=path)

            with unittest.mock.patch.dict(
                os.environ,
                {ENV_API_KEY: "env-key", ENV_BASE_URL: "http://from-env"},
                clear=False,
            ):
                resolved = resolve_runtime_config(path=path)

            self.assertEqual(resolved["api_key"], "env-key")
            self.assertEqual(resolved["base_url"], "http://from-env")

    def test_runtime_config_defaults_when_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ".aegis" / "config.json"
            with unittest.mock.patch.dict(
                os.environ,
                {ENV_API_KEY: "", ENV_BASE_URL: ""},
                clear=False,
            ):
                resolved = resolve_runtime_config(path=path)

            self.assertIsNone(resolved["api_key"])
            self.assertEqual(resolved["base_url"], DEFAULT_BASE_URL)
