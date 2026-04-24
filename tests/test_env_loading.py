import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import search


class EnvLoadingTests(unittest.TestCase):
    def test_load_env_file_reads_plugin_local_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin_dir = Path(tmp) / "web-search-plus"
            plugin_dir.mkdir()
            fake_script = plugin_dir / "search.py"
            fake_script.write_text("# fake")
            (plugin_dir / ".env").write_text("LINKUP_API_KEY=local-plugin-key\n")

            with mock.patch.object(search, "__file__", str(fake_script)):
                with mock.patch.dict(os.environ, {}, clear=True):
                    search._load_env_file()
                    self.assertEqual(os.environ.get("LINKUP_API_KEY"), "local-plugin-key")


if __name__ == "__main__":
    unittest.main()
