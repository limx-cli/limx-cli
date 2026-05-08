import io
import json
import unittest
import zipfile
from unittest import mock

from agent_harness.scratch_bridge import (
    SCRATCH_EXTENSION_JS,
    BridgeConfig,
    ProjectRunner,
    build_cli_args,
    extract_action_menu,
    extract_dance_menu,
    normalize_work_mode,
    parse_cli_json,
    render_extension_js,
    robot_name_from_accid,
    sanitize_scratch_project,
)


class ScratchBridgeTest(unittest.TestCase):
    def config(self, dry_run=False):
        return BridgeConfig(
            robot_host="127.0.0.1",
            robot_port=5000,
            command_timeout=10.0,
            dry_run=dry_run,
            python="python3",
        )

    def test_dance_run_builds_rc_mapping_cli(self):
        argv = build_cli_args("dance_run", {"rc_mapping": "solo_shake"}, self.config())

        self.assertEqual(
            [
                "--host",
                "127.0.0.1",
                "--port",
                "5000",
                "dance",
                "run",
                "--rc-mapping",
                "solo_shake",
            ],
            argv,
        )

    def test_walk_builds_bounded_motion_cli(self):
        argv = build_cli_args(
            "walk",
            {"x": 0.2, "y": 0, "yaw": 0.1, "duration": 2},
            self.config(dry_run=True),
        )

        self.assertIn("--dry-run", argv)
        self.assertEqual("motion", argv[argv.index("--dry-run") + 1])
        self.assertIn("--duration", argv)
        self.assertEqual("2.0", argv[argv.index("--duration") + 1])
        self.assertIn("--rate-hz", argv)

    def test_read_only_commands_do_not_add_dry_run(self):
        argv = build_cli_args("dance_list", {}, self.config(dry_run=True))

        self.assertNotIn("--dry-run", argv)
        self.assertEqual(["dance", "list"], argv[-2:])

    def test_action_mode_commands_are_exposed(self):
        self.assertEqual(
            ["--host", "127.0.0.1", "--port", "5000", "--dry-run", "action", "enter"],
            build_cli_args("action_enter", {}, self.config(dry_run=True)),
        )
        self.assertEqual(
            ["--host", "127.0.0.1", "--port", "5000", "--dry-run", "dance", "enter"],
            build_cli_args("dance_mode", {}, self.config(dry_run=True)),
        )
        self.assertEqual(
            [
                "--host",
                "127.0.0.1",
                "--port",
                "5000",
                "--dry-run",
                "raw",
                "request_standup",
                "--data",
                '{"mode": "hanging"}',
            ],
            build_cli_args("stand_mode", {}, self.config(dry_run=True)),
        )
        self.assertEqual(["motion", "standup"], build_cli_args("standup", {}, self.config())[-2:])

    def test_walk_mode_uses_raw_request_set_walk_mode(self):
        argv = build_cli_args("walk_mode", {}, self.config(dry_run=True))

        self.assertEqual(
            [
                "--host",
                "127.0.0.1",
                "--port",
                "5000",
                "--dry-run",
                "raw",
                "request_set_walk_mode",
                "--data",
                "{}",
            ],
            argv,
        )

    def test_damped_mode_uses_raw_request_damping(self):
        argv = build_cli_args("damped_mode", {}, self.config(dry_run=True))

        self.assertEqual(
            [
                "--host",
                "127.0.0.1",
                "--port",
                "5000",
                "--dry-run",
                "raw",
                "request_damping",
                "--data",
                "{}",
            ],
            argv,
        )

    def test_action_run_uses_action_sync_name(self):
        argv = build_cli_args("action_run", {"name": "wave_greet_bye"}, self.config())

        self.assertEqual(
            [
                "--host",
                "127.0.0.1",
                "--port",
                "5000",
                "action",
                "run",
                "--name",
                "wave_greet_bye",
                "--timeout",
                "120",
            ],
            argv,
        )

    def test_action_run_defaults_empty_name(self):
        argv = build_cli_args("action_run", {"name": ""}, self.config())

        self.assertEqual("wave_greet_bye", argv[argv.index("--name") + 1])

    def test_dance_run_resolves_menu_label_to_rc_mapping(self):
        config = self.config()
        config.dance_menu = [
            {"value": "warm_dance", "zh": "热烈", "en": "Warm dance"},
        ]

        argv = build_cli_args("dance_run", {"name": "热烈"}, config)

        self.assertEqual("warm_dance", argv[argv.index("--rc-mapping") + 1])

    def test_dance_run_keeps_legacy_rc_mapping_argument(self):
        argv = build_cli_args("dance_run", {"rc_mapping": "solo_shake"}, self.config())

        self.assertEqual("solo_shake", argv[argv.index("--rc-mapping") + 1])

    def test_state_query_is_read_only_and_validated(self):
        argv = build_cli_args("state", {"kind": "joint"}, self.config(dry_run=True))

        self.assertNotIn("--dry-run", argv)
        self.assertEqual(["state", "joint"], argv[-2:])
        self.assertEqual(["state", "mode"], build_cli_args("work_mode", {}, self.config(dry_run=True))[-2:])
        with self.assertRaises(ValueError):
            build_cli_args("state", {"kind": "pose"}, self.config())

    def test_work_mode_prefers_robot_status(self):
        self.assertEqual(
            {"work_mode": "Damped", "work_mode_zh": "阻尼", "message": "阻尼"},
            normalize_work_mode(
                {
                    "robot_status": "Damped",
                    "action_library_mode": "remote_control",
                    "action_library_state": "idle",
                }
            ),
        )

    def test_robot_name_from_accid(self):
        self.assertEqual("Oli", robot_name_from_accid("HU_D_001"))
        self.assertEqual("Luna", robot_name_from_accid("HU_L_001"))
        self.assertEqual("LimX", robot_name_from_accid(""))

    def test_motion_mode_commands_are_exposed(self):
        self.assertEqual(["motion", "prepare"], build_cli_args("prepare", {}, self.config())[-2:])
        self.assertEqual(["motion", "lie-down"], build_cli_args("lie_down", {}, self.config())[-2:])
        self.assertEqual(["motion", "zero-torque"], build_cli_args("zero_torque", {}, self.config())[-2:])

    def test_rejects_unknown_command(self):
        with self.assertRaises(ValueError):
            build_cli_args("shell", {}, self.config())

    def test_project_runner_uses_configured_node_binary(self):
        config = self.config()
        config.node = "/opt/limx/node/bin/node"
        runner = ProjectRunner(config)

        fake_process = mock.Mock()
        fake_process.pid = 123
        fake_process.poll.return_value = None
        fake_process.stdout = []
        fake_process.stderr = []
        with mock.patch("agent_harness.scratch_bridge.subprocess.Popen", return_value=fake_process) as popen:
            result = runner.start("/tmp/project.sb3")

        self.assertEqual("success", result["result"])
        self.assertEqual("/opt/limx/node/bin/node", popen.call_args.args[0][0])

    def test_parse_cli_json_keeps_non_json_stdout(self):
        self.assertEqual({"stdout": "hello"}, parse_cli_json("hello\n"))

    def test_sanitize_scratch_project_removes_turbowarp_platform(self):
        project = {
            "targets": [
                {
                    "isStage": True,
                    "blocks": {
                        "a": {"opcode": "limxRobot_walk", "next": None, "parent": None}
                    },
                }
            ],
            "extensions": ["limxRobot"],
            "extensionURLs": {"limxRobot": "http://127.0.0.1:6080/extension.js"},
            "meta": {
                "semver": "3.0.0",
                "vm": "0.2.0",
                "agent": "",
                "platform": {"name": "TurboWarp", "url": "https://turbowarp.org/"},
            },
        }
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("project.json", json.dumps(project, ensure_ascii=False))
            zf.writestr("asset.txt", "keep")

        sanitized = sanitize_scratch_project(buf.getvalue())

        with zipfile.ZipFile(io.BytesIO(sanitized), "r") as zf:
            next_project = json.loads(zf.read("project.json").decode("utf-8"))
            self.assertEqual("keep", zf.read("asset.txt").decode("utf-8"))

        self.assertEqual(["limxRobot"], next_project["extensions"])
        self.assertNotIn("extensionURLs", next_project)
        self.assertNotIn("platform", next_project["meta"])
        self.assertEqual("limxRobot_walk", next_project["targets"][0]["blocks"]["a"]["opcode"])

    def test_extension_can_load_in_sandboxed_editors(self):
        self.assertNotIn("must run unsandboxed", SCRATCH_EXTENSION_JS)
        self.assertIn("Scratch.extensions.register", SCRATCH_EXTENSION_JS)
        self.assertIn("function enqueue", SCRATCH_EXTENSION_JS)
        self.assertIn("commandQueue", SCRATCH_EXTENSION_JS)
        self.assertIn("进入动作模式", SCRATCH_EXTENSION_JS)
        self.assertIn("进入舞蹈模式", SCRATCH_EXTENSION_JS)
        self.assertIn("进入行走模式", SCRATCH_EXTENSION_JS)
        self.assertIn("进入阻尼模式", SCRATCH_EXTENSION_JS)
        self.assertIn("进入零力矩模式", SCRATCH_EXTENSION_JS)
        self.assertIn("动作 [NAME]", SCRATCH_EXTENSION_JS)
        self.assertNotIn("执行动作", SCRATCH_EXTENSION_JS)
        self.assertNotIn("刷新动作和舞蹈列表", SCRATCH_EXTENSION_JS)
        self.assertIn("运行", SCRATCH_EXTENSION_JS)
        self.assertNotIn("运行状态", SCRATCH_EXTENSION_JS)
        self.assertNotIn("当前工作模式", SCRATCH_EXTENSION_JS)
        self.assertIn("defaultValue: t('运行', 'running')", SCRATCH_EXTENSION_JS)
        self.assertNotIn("准备站立", SCRATCH_EXTENSION_JS)
        self.assertNotIn("空闲时退出动作模式", SCRATCH_EXTENSION_JS)
        self.assertNotIn("位姿", SCRATCH_EXTENSION_JS)
        self.assertIn("actionNames", SCRATCH_EXTENSION_JS)
        self.assertIn("danceMappings", SCRATCH_EXTENSION_JS)
        self.assertIn("items: this.actionMenu", SCRATCH_EXTENSION_JS)
        self.assertIn("items: this.danceMenu", SCRATCH_EXTENSION_JS)
        self.assertNotIn("items: 'getActionMenu'", SCRATCH_EXTENSION_JS)
        self.assertNotIn("items: 'getDanceMenu'", SCRATCH_EXTENSION_JS)
        self.assertNotIn("this.getActionMenu.bind(this)", SCRATCH_EXTENSION_JS)
        self.assertNotIn("this.getDanceMenu.bind(this)", SCRATCH_EXTENSION_JS)

    def test_render_extension_js_injects_startup_menus(self):
        config = self.config(dry_run=True)
        config.action_menu = [
            {"value": "wave_greet_bye", "zh": "挥手告别", "en": "Wave goodbye"},
            {"value": "turn_left", "zh": "左转", "en": "Turn left"},
        ]
        config.dance_menu = [
            {"value": "solo_shake", "zh": "孤身摇", "en": "Solo shake"},
            {"value": "happy_dance", "zh": "开心舞", "en": "Happy dance"},
        ]

        js = render_extension_js(config)

        self.assertIn('"value": "wave_greet_bye"', js)
        self.assertIn('"zh": "挥手告别"', js)
        self.assertIn('"value": "solo_shake"', js)
        self.assertIn('"en": "Solo shake"', js)
        self.assertNotIn("__LIMX_ACTION_MENU__", js)
        self.assertNotIn("__LIMX_DANCE_MENU__", js)
        self.assertNotIn("__LIMX_ROBOT_NAME__", js)
        self.assertNotIn("__LIMX_LANG__", js)
        self.assertIn('const __INITIAL_LANG__ = "";', js)

        en_js = render_extension_js(config, "en")
        self.assertIn('const __INITIAL_LANG__ = "en";', en_js)

        config.robot_name = "Luna"
        luna_js = render_extension_js(config)
        self.assertIn('const robotName = "Luna";', luna_js)
        self.assertIn("name: robotName + ' Robot'", luna_js)

    def test_extract_startup_menus(self):
        self.assertEqual(
            [
                {"value": "Wave", "zh": "Wave", "en": "Wave"},
                {"value": "turn_left", "zh": "turn_left", "en": "turn_left"},
            ],
            extract_action_menu(
                {
                    "motion_list": [
                        {"rc_mapping": "wave_greet_bye", "motion_name_en": "Wave"},
                        {"rc_mapping": "", "motion_name_en": "turn_left"},
                        {"rc_mapping": "wave_greet_bye"},
                    ]
                }
            ),
        )
        self.assertEqual(
            [
                {"value": "solo_shake", "zh": "solo_shake", "en": "solo_shake"},
            ],
            extract_dance_menu(
                {
                    "dances": [
                        {"rc_mapping": "solo_shake"},
                        {"id": "happy"},
                        {"rc_mapping": "solo_shake"},
                    ]
                }
            ),
        )


if __name__ == "__main__":
    unittest.main()
