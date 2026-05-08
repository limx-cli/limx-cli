import io
import json
import unittest
from contextlib import redirect_stdout

from limx_agent_harness.cli import (
    action_library_is_running,
    build_parser,
    command_count,
    main,
    seated_state_is_ready,
    sit_result_is_success,
    standing_state_is_ready,
    walk_mode_is_ready,
)


class CliTest(unittest.TestCase):
    def run_cli(self, argv):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(argv)
        return code, stdout.getvalue()

    def test_raw_dry_run_json(self):
        code, output = self.run_cli(
            [
                "--dry-run",
                "raw",
                "request_get_joint_state",
                "--data",
                "{}",
            ]
        )

        self.assertEqual(0, code)
        data = json.loads(output)
        self.assertTrue(data["dry_run"])
        self.assertEqual("request_get_joint_state", data["requests"][0]["title"])

    def test_state_mode_uses_robot_status_request(self):
        code, output = self.run_cli(["--dry-run", "state", "mode"])

        self.assertEqual(0, code)
        data = json.loads(output)
        self.assertEqual("request_get_robot_status", data["requests"][0]["title"])

    def test_walk_dry_run_includes_stop(self):
        code, output = self.run_cli(
            [
                "--dry-run",
                "motion",
                "walk",
                "--x",
                "0.1",
                "--duration",
                "1",
            ]
        )

        self.assertEqual(0, code)
        data = json.loads(output)
        self.assertEqual("request_set_walk_mode", data["requests"][0]["title"])
        self.assertEqual("repeat", data["requests"][1]["title"])
        self.assertEqual("request_set_walk_vel_sync", data["requests"][1]["data"]["title"])
        self.assertEqual(10.0, data["requests"][1]["data"]["rate_hz"])
        self.assertEqual(10, data["requests"][1]["data"]["count"])
        self.assertEqual({"x": 0.0, "y": 0.0, "yaw": 0.0}, data["requests"][2]["data"])

    def test_sit_dry_run_includes_recovery_steps(self):
        code, output = self.run_cli(["--dry-run", "motion", "sit"])

        self.assertEqual(0, code)
        data = json.loads(output)
        titles = [item["title"] for item in data["requests"]]
        self.assertEqual(
            [
                "request_get_action_library_status",
                "request_set_motion_engine",
                "request_from_stand_to_sit",
                "request_set_walk_mode",
                "request_from_stand_to_sit",
            ],
            titles,
        )

    def test_standup_dry_run_includes_prepare_fallback(self):
        code, output = self.run_cli(["--dry-run", "motion", "standup"])

        self.assertEqual(0, code)
        data = json.loads(output)
        self.assertEqual("request_standup", data["requests"][0]["title"])
        self.assertEqual("request_set_walk_mode", data["requests"][1]["title"])
        self.assertEqual("request_prepare", data["requests"][2]["title"])

    def test_dance_run_uses_rc_mapping_value(self):
        code, output = self.run_cli(["--dry-run", "dance", "run", "--rc-mapping", "solo_shake"])

        self.assertEqual(0, code)
        data = json.loads(output)
        self.assertEqual("request_dance", data["requests"][0]["title"])
        self.assertEqual({"name": "solo_shake"}, data["requests"][0]["data"])

    def test_dance_enter_uses_enter_dance_mode_request(self):
        code, output = self.run_cli(["--dry-run", "dance", "enter"])

        self.assertEqual(0, code)
        data = json.loads(output)
        self.assertEqual("request_enter_dance_mode", data["requests"][0]["title"])
        self.assertEqual({"mode": 1}, data["requests"][0]["data"])

    def test_action_sync_uses_request_action_sync_name(self):
        code, output = self.run_cli(
            ["--dry-run", "action", "run", "--name", "wave_greet_bye"]
        )

        self.assertEqual(0, code)
        data = json.loads(output)
        self.assertEqual("request_action_sync", data["requests"][0]["title"])
        self.assertEqual({"name": "wave_greet_bye"}, data["requests"][0]["data"])

    def test_lock_dry_run_prints_identity(self):
        code, output = self.run_cli(
            ["--dry-run", "--user", "agent", "--device", "cursor", "lock", "acquire"]
        )

        self.assertEqual(0, code)
        data = json.loads(output)
        self.assertEqual("request_lock_robot_control", data["requests"][0]["title"])
        self.assertEqual("cursor", data["requests"][0]["data"]["device_id"])

    def test_invalid_raw_data_returns_error(self):
        code, _output = self.run_cli(["--dry-run", "raw", "request_get_joint_state", "--data", "[]"])

        self.assertEqual(1, code)

    def test_action_exit_dry_run_checks_status_first(self):
        code, output = self.run_cli(["--dry-run", "action", "exit"])

        self.assertEqual(0, code)
        data = json.loads(output)
        self.assertEqual("request_get_action_library_status", data["requests"][0]["title"])
        self.assertEqual("request_set_motion_engine", data["requests"][1]["title"])

    def test_action_library_running_helper(self):
        self.assertTrue(
            action_library_is_running(
                {
                    "action_library_mode": "action_library",
                    "action_library_state": "running",
                }
            )
        )
        self.assertFalse(
            action_library_is_running(
                {
                    "action_library_mode": "action_library",
                    "action_library_state": "idle",
                }
            )
        )

    def test_tts_command_is_not_registered(self):
        parser = build_parser()

        with self.assertRaises(SystemExit) as context:
            parser.parse_args(["tts"])

        self.assertEqual(2, context.exception.code)

    def test_walk_mode_ready_accepts_already_walk_state(self):
        self.assertTrue(
            walk_mode_is_ready(
                {
                    "result": "fail_state_not_allowed",
                    "current_state": "Walk",
                    "allowed_events": ["Menu"],
                }
            )
        )
        self.assertFalse(
            walk_mode_is_ready(
                {
                    "result": "fail_state_not_allowed",
                    "current_state": "ActionLibrary",
                }
            )
        )

    def test_command_count_uses_duration_and_rate(self):
        self.assertEqual(10, command_count(1.0, 10.0))
        self.assertEqual(20, command_count(2.0, 10.0))
        self.assertEqual(1, command_count(0.01, 10.0))

    def test_sit_helpers_accept_already_seated_state(self):
        response = {"result": "fail_invalid_mode", "current_state": "StandSit"}

        self.assertTrue(seated_state_is_ready(response, "StandSit"))
        self.assertTrue(sit_result_is_success(response, "StandSit"))
        self.assertFalse(seated_state_is_ready(response, "SitDown"))

    def test_standup_helper_accepts_walk_as_standing(self):
        self.assertTrue(standing_state_is_ready({"current_state": "Walk"}))
        self.assertTrue(standing_state_is_ready({"current_state": "IkStand"}))
        self.assertFalse(standing_state_is_ready({"current_state": "Damped"}))


if __name__ == "__main__":
    unittest.main()
