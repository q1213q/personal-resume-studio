"""Synthetic contract tests: no real accounts, external requests or uploads."""
import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import publish_hsk
from release_tools import file_digest


def wizard(*, ask=None, login=False, channel="anonymous"):
    recommendations = [{"next": "hsk-cli file-hosting <path> --format json"}]
    if login:
        recommendations.append({"next": "hsk-cli auth login --method loopback --format json"})
    return {"success": True, "data": {
        "schema_version": "0.2", "ask": ask or [],
        "claim_channel": {"claim_channel": channel, "logged_in": channel == "auth",
                          "api_key_configured": channel == "api_key"},
        "recommendations": recommendations,
    }}


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.release = self.root / "release"
        self.site = self.release / "site"
        (self.site / "assets").mkdir(parents=True)
        self.photo = bytes(range(256)) * 4
        (self.site / "index.html").write_text("<!doctype html><h1>合成测试</h1>", encoding="utf-8")
        (self.site / "assets" / "photo.png").write_bytes(self.photo)
        manifest = {"schema_version": 1, "entry": "index.html", "files": []}
        for name in ["index.html", "assets/photo.png"]:
            size, digest = file_digest(self.site / name)
            manifest["files"].append({"path": name, "bytes": size, "sha256": digest})
        (self.release / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.stdout, self.stderr = io.StringIO(), io.StringIO()

    def run_entry(self, *extra):
        with contextlib.redirect_stdout(self.stdout), contextlib.redirect_stderr(self.stderr):
            return publish_hsk.main(["--release", str(self.release), "--agent", "codex", *extra])

    def mock_steps(self, result, *extra):
        return patch.object(publish_hsk, "inspect_command", side_effect=[{"success": True}, result, *extra])

    def test_dry_run_keeps_photo_and_never_discovers_cli(self):
        with patch.object(publish_hsk, "cli_prefix", side_effect=AssertionError("network path")):
            self.assertEqual(self.run_entry("--dry-run"), 0)
        self.assertFalse(json.loads(self.stdout.getvalue())["uploaded"])
        self.assertEqual((self.site / "assets/photo.png").read_bytes(), self.photo)

    def test_extra_private_file_stops_before_any_cli(self):
        (self.site / "auth.json").write_text("{}")
        with patch.object(publish_hsk, "cli_prefix") as cli:
            self.assertEqual(self.run_entry(), 1)
            cli.assert_not_called()

    def test_changed_photo_stops_before_any_cli(self):
        (self.site / "assets/photo.png").write_bytes(b"modified")
        with patch.object(publish_hsk, "cli_prefix") as cli:
            self.assertEqual(self.run_entry(), 1)
            cli.assert_not_called()

    def test_symlink_is_not_uploaded(self):
        target = self.root / "private.txt"
        target.write_text("private synthetic data")
        try:
            (self.site / "leak.txt").symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        with patch.object(publish_hsk, "cli_prefix") as cli:
            self.assertEqual(self.run_entry(), 1)
            cli.assert_not_called()

    def test_questions_stop_before_upload(self):
        with patch.object(publish_hsk, "cli_prefix", return_value=["fake-hsk"]), self.mock_steps(
                wizard(ask=[{"field": "persistence", "options": ["temporary", "long_term"]}])), \
                patch.object(publish_hsk.subprocess, "call") as upload:
            self.assertEqual(self.run_entry(), 2)
            upload.assert_not_called()

    def test_login_recommendation_is_handed_off_before_upload(self):
        with patch.object(publish_hsk, "cli_prefix", return_value=["fake-hsk"]), self.mock_steps(wizard(login=True)), \
                patch.object(publish_hsk.subprocess, "call") as upload:
            self.assertEqual(self.run_entry(), 2)
            upload.assert_not_called()

    def test_auto_and_anonymous_both_upload_only_public_directory(self):
        for channel in ["anonymous", "auth", "api_key"]:
            with self.subTest(channel=channel), patch.object(publish_hsk, "cli_prefix", return_value=["fake-hsk"]), \
                    self.mock_steps(wizard(channel=channel, login=channel != "anonymous")) as inspect, \
                    patch.object(publish_hsk.subprocess, "call", return_value=0) as upload:
                self.assertEqual(self.run_entry(), 0)
                self.assertIn("doctor", inspect.call_args_list[0].args[0])
                self.assertIn("wizard", inspect.call_args_list[1].args[0])
                argv = upload.call_args.args[0]
                self.assertEqual(argv[1:3], ["file-hosting", str(self.site.resolve())])
                self.assertIn("--entry-file", argv)
                self.assertNotIn("--detach", argv)
                self.assertNotIn("--timeout", argv)
                self.assertNotIn("stdout", upload.call_args.kwargs)  # live handoff output
                self.assertEqual(upload.call_args.kwargs["env"]["AI_AGENT"], "codex")

    def test_failure_does_not_retry_upload(self):
        with patch.object(publish_hsk, "cli_prefix", return_value=["fake-hsk"]), self.mock_steps(wizard()), \
                patch.object(publish_hsk.subprocess, "call", return_value=4) as upload:
            self.assertEqual(self.run_entry(), 4)
            upload.assert_called_once()

    def test_wizard_answers_are_passed_through_stdin(self):
        answers = self.root / "wizard-answers.json"
        payload = {"schema_version": "0.2", "answers": [{"field": "persistence", "value": "temporary"}]}
        answers.write_text(json.dumps(payload))
        with patch.object(publish_hsk, "cli_prefix", return_value=["fake-hsk"]), \
                self.mock_steps(wizard(ask=[{"field": "persistence"}]), wizard()) as inspect, \
                patch.object(publish_hsk.subprocess, "call", return_value=0):
            self.assertEqual(self.run_entry("--wizard-answers", str(answers)), 0)
            last = inspect.call_args_list[-1].args
            self.assertIn("--stdin", last[0])
            self.assertEqual(json.loads(last[2]), payload)

    def test_directory_is_rechecked_after_wizard(self):
        calls = 0
        def inspect(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                (self.site / "index.html").write_text("modified during setup")
                return wizard()
            return {"success": True}
        with patch.object(publish_hsk, "cli_prefix", return_value=["fake-hsk"]), \
                patch.object(publish_hsk, "inspect_command", side_effect=inspect), \
                patch.object(publish_hsk.subprocess, "call") as upload:
            self.assertEqual(self.run_entry(), 1)
            upload.assert_not_called()

    def test_unknown_wizard_shape_and_non_host_recommendations_stop(self):
        result = wizard()
        bad = copy.deepcopy(result)
        bad["data"].pop("ask")
        unrelated = copy.deepcopy(result)
        unrelated["data"]["recommendations"] = [{"next": "hsk-cli tunnel --port 3000"}]
        for data in [bad, unrelated]:
            with patch.object(publish_hsk, "cli_prefix", return_value=["fake-hsk"]), self.mock_steps(data), \
                    patch.object(publish_hsk.subprocess, "call") as upload:
                self.assertNotEqual(self.run_entry(), 0)
                upload.assert_not_called()

    def test_doctor_failure_stops(self):
        failed = subprocess.CompletedProcess(["fake-hsk"], 1, '{"success":false,"message":"offline"}')
        with patch.object(publish_hsk, "cli_prefix", return_value=["fake-hsk"]), \
                patch.object(publish_hsk.subprocess, "run", return_value=failed), \
                patch.object(publish_hsk.subprocess, "call") as upload:
            self.assertEqual(self.run_entry(), 1)
            upload.assert_not_called()

    def test_stdout_parser_handles_official_formats_and_first_result(self):
        self.assertEqual(publish_hsk.first_json('{\n "success": true\n}'), {"success": True})
        self.assertEqual(publish_hsk.first_json('log\n{"success":true}\n{"success":false}'), {"success": True})
        with self.assertRaises(ValueError):
            publish_hsk.first_json("not JSON")

    def test_setup_result_cannot_be_mistaken_for_upload_result(self):
        result = subprocess.CompletedProcess([], 0, '{"success":true}\n')
        with contextlib.redirect_stdout(self.stdout), contextlib.redirect_stderr(self.stderr), \
                patch.object(publish_hsk.subprocess, "run", return_value=result):
            self.assertTrue(publish_hsk.inspect_command(["fake-hsk", "doctor"], {})["success"])
        self.assertEqual(self.stdout.getvalue(), "")
        self.assertIn('"success":true', self.stderr.getvalue())

    def test_npx_fallback_uses_named_official_package(self):
        paths = {"node": "/test/node", "npx": "/test/npx"}
        with patch.object(publish_hsk.shutil, "which", side_effect=paths.get), \
                patch.object(publish_hsk.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "v24.0.0")):
            self.assertEqual(publish_hsk.cli_prefix(), ["/test/npx", "--yes", "@aweray/hsk-cli@0.7.24"])


if __name__ == "__main__":
    unittest.main()
