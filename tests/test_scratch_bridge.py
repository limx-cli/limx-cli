import io
import importlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest import mock

scratch_bridge = importlib.import_module("limx-cli.scratch_bridge")
SCRATCH_EXTENSION_JS = scratch_bridge.SCRATCH_EXTENSION_JS
BridgeConfig = scratch_bridge.BridgeConfig
ProjectRunner = scratch_bridge.ProjectRunner
build_cli_args = scratch_bridge.build_cli_args
extract_action_menu = scratch_bridge.extract_action_menu
extract_dance_menu = scratch_bridge.extract_dance_menu
extract_emoji_menu = scratch_bridge.extract_emoji_menu
normalize_work_mode = scratch_bridge.normalize_work_mode
parse_cli_json = scratch_bridge.parse_cli_json
render_extension_js = scratch_bridge.render_extension_js
robot_name_from_accid = scratch_bridge.robot_name_from_accid
robot_project_dir = scratch_bridge.robot_project_dir
robot_project_name = scratch_bridge.robot_project_name
robot_supports_emoji_blocks = scratch_bridge.robot_supports_emoji_blocks
robot_supports_posture_blocks = scratch_bridge.robot_supports_posture_blocks
sanitize_scratch_project = scratch_bridge.sanitize_scratch_project


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

    def test_dance_run_cli_accepts_underscore_rc_mapping(self):
        build_parser = importlib.import_module("limx-cli.cli").build_parser

        args = build_parser().parse_args([
            "--host",
            "127.0.0.1",
            "dance",
            "run",
            "--rc_mapping",
            "whatever",
        ])

        self.assertEqual("whatever", args.rc_mapping)

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

        emoji_argv = build_cli_args("emoji_list", {}, self.config(dry_run=True))
        self.assertNotIn("--dry-run", emoji_argv)
        self.assertEqual(["emoji", "list"], emoji_argv[-2:])

    def test_action_mode_commands_are_exposed(self):
        self.assertEqual(
            ["--host", "127.0.0.1", "--port", "5000", "--dry-run", "action", "enter"],
            build_cli_args("action_enter", {}, self.config(dry_run=True)),
        )
        self.assertEqual(
            ["--host", "127.0.0.1", "--port", "5000", "--dry-run", "action", "stop"],
            build_cli_args("action_stop", {}, self.config(dry_run=True)),
        )
        self.assertEqual(
            ["--host", "127.0.0.1", "--port", "5000", "--dry-run", "dance", "enter"],
            build_cli_args("dance_mode", {}, self.config(dry_run=True)),
        )
        self.assertEqual(
            ["--host", "127.0.0.1", "--port", "5000", "--dry-run", "dance", "stop"],
            build_cli_args("dance_stop", {}, self.config(dry_run=True)),
        )
        self.assertEqual(
            ["--host", "127.0.0.1", "--port", "5000", "--dry-run", "dance", "exit"],
            build_cli_args("dance_exit", {}, self.config(dry_run=True)),
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

    def test_hu_l_does_not_support_posture_blocks(self):
        self.assertTrue(robot_supports_posture_blocks("HU_D_001"))
        self.assertFalse(robot_supports_posture_blocks("HU_L_001"))
        self.assertFalse(robot_supports_posture_blocks(" hu_l_001 "))

    def test_hu_l_supports_emoji_blocks(self):
        self.assertFalse(robot_supports_emoji_blocks("HU_D_001"))
        self.assertTrue(robot_supports_emoji_blocks("HU_L_001"))
        self.assertTrue(robot_supports_emoji_blocks(" hu_l_001 "))

    def test_motion_mode_commands_are_exposed(self):
        self.assertEqual(["motion", "prepare"], build_cli_args("prepare", {}, self.config())[-2:])
        self.assertEqual(["motion", "lie-down"], build_cli_args("lie_down", {}, self.config())[-2:])
        self.assertEqual(["motion", "zero-torque"], build_cli_args("zero_torque", {}, self.config())[-2:])
        self.assertEqual(["emoji", "set", "screen-default"], build_cli_args("emoji_set", {"name": "screen-default"}, self.config())[-3:])

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
        with mock.patch.object(scratch_bridge.subprocess, "Popen", return_value=fake_process) as popen:
            result = runner.start("/tmp/project.sb3")

        self.assertEqual("success", result["result"])
        self.assertEqual("/opt/limx/node/bin/node", popen.call_args.args[0][0])

    def test_project_dir_is_split_by_robot_type(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self.config()
            config.project_dir = temp_dir
            config.robot_accid = "HU_D_001"
            oli_dir = robot_project_dir(config)

            config.robot_accid = "HU_L_001"
            luna_dir = robot_project_dir(config)

        self.assertTrue(oli_dir.endswith("/Oli"))
        self.assertTrue(luna_dir.endswith("/Luna"))
        self.assertNotEqual(oli_dir, luna_dir)

    def test_unknown_robot_uses_base_project_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self.config(dry_run=True)
            config.project_dir = temp_dir

            self.assertEqual("", robot_project_name(config))
            self.assertEqual(temp_dir, robot_project_dir(config))

            config.robot_accid = "HU_X_001"
            self.assertEqual("", robot_project_name(config))
            self.assertEqual(temp_dir, robot_project_dir(config))

    def test_project_runner_uses_robot_specific_project_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self.config()
            config.project_dir = temp_dir
            config.robot_accid = "HU_L_001"
            runner = ProjectRunner(config)

            project_dir = runner.project_dir

            self.assertEqual(str(Path(temp_dir) / "Luna"), project_dir)
            self.assertTrue(Path(project_dir).is_dir())

    def test_project_runner_starts_one_main_program_stack(self):
        runner = Path(__file__).resolve().parents[1] / "limx-cli" / "scratch_runner.js"
        source = runner.read_text(encoding="utf-8")

        self.assertNotIn("vm.greenFlag();", source)
        self.assertIn("mainProgramBlock", source)
        self.assertIn("topLevelProgramBlocksForTarget", source)
        self.assertIn("vm.runtime._pushThread(program.id", source)
        self.assertNotIn("Starting orphan top-level block", source)

    def test_project_start_and_stop_exit_action_or_dance_modes(self):
        root = Path(__file__).resolve().parents[1]
        bridge = (root / "limx-cli" / "scratch_bridge.py").read_text(encoding="utf-8")
        cli = (root / "limx-cli" / "cli.py").read_text(encoding="utf-8")

        self.assertIn('commands.add_parser("stop", help="Interrupt current action', cli)
        self.assertIn('commands.add_parser("stop", help="Interrupt current dance', cli)
        self.assertIn('client.request("request_set_motion_engine", {"mode": 0}', bridge)
        self.assertIn('client.request("request_enter_dance_mode", {"mode": 0}', bridge)
        self.assertNotIn("request_unlock_robot_control", bridge)
        self.assertNotIn("client.lock(", bridge)
        self.assertIn('"title": "request_enter_dance_mode"', bridge)
        self.assertIn('path == "/project/stop-modes"', bridge)
        self.assertIn("stop_modes_result = stop_action_dance_modes(config)", bridge)
        self.assertIn('result["stop_modes"] = stop_modes_result', bridge)

    def test_editor_green_flag_runs_current_workspace_program(self):
        root = Path(__file__).resolve().parents[1]
        controls = (root / "scratch-app" / "src" / "containers" / "controls.jsx").read_text(encoding="utf-8")
        overlay = (root / "scratch-app" / "src" / "containers" / "green-flag-overlay.jsx").read_text(
            encoding="utf-8"
        )
        blocks = (root / "scratch-app" / "src" / "containers" / "blocks.jsx").read_text(encoding="utf-8")
        runner = (root / "scratch-app" / "src" / "lib" / "limx-run-program.js").read_text(encoding="utf-8")
        confirm = (root / "scratch-app" / "src" / "lib" / "limx-confirm.js").read_text(encoding="utf-8")
        bootstrap = (root / "scratch-app" / "static" / "static" / "bootstrap.js").read_text(encoding="utf-8")

        self.assertNotIn("vm.greenFlag()", controls)
        self.assertNotIn("vm.greenFlag()", overlay)
        self.assertIn("await runCurrentProgram(this.props.vm)", controls)
        self.assertIn("runCurrentProgram(this.props.vm)", overlay)
        self.assertIn("await runCurrentProgram(this.props.vm)", overlay)
        self.assertIn("toggleScript(blockId", runner)
        self.assertIn("stopDanceAndActionModes", runner)
        self.assertIn("/project/stop-modes", runner)
        self.assertIn("mainProgramBlock", runner)
        self.assertIn("MAIN_PROGRAM_RUN_INTERVAL_MS", runner)
        self.assertIn("No program blocks to run", runner)
        self.assertIn("confirmRunProgram", runner)
        self.assertIn("limxConfirm('确定要运行当前程序吗？')", runner)
        self.assertIn("确定要运行当前程序吗？", runner)
        self.assertIn("installRunGuards", runner)
        self.assertIn("allowNextStackClickRun", runner)
        self.assertIn("__limxStackClickRunGuarded", runner)
        self.assertIn("__limxAllowStackClickRun", runner)
        self.assertIn("__limxFlyoutStackClickGroupUntil", runner)
        self.assertIn("__limxSkipNextBootstrapStackClickConfirm", runner)
        self.assertIn("__limxAllowNextSourceStackClickRun", runner)
        self.assertIn("handleWorkspaceBlockEvent", blocks)
        self.assertIn("handleFlyoutBlockEvent", blocks)
        self.assertIn("__limxFlyoutStackClickGroupUntil", blocks)
        self.assertIn("installRunGuards(this.props.vm)", blocks)
        self.assertIn("event.element === 'click'", blocks)
        self.assertIn("this.flyoutWorkspace.addChangeListener(this.handleFlyoutBlockEvent)", blocks)
        self.assertIn("this.props.vm.monitorBlockListener", blocks)
        self.assertIn("确定要后台运行该项目吗？", bootstrap)
        self.assertIn("limxConfirm", confirm)
        self.assertIn("limx-confirm-overlay", confirm)
        self.assertIn("var(--ui-modal-background", confirm)
        self.assertIn("async function saveCurrentProject", bootstrap)
        self.assertIn("async function handleProjectAction", bootstrap)
        self.assertIn("await limxConfirm(bgMsg('确定要后台运行该项目吗？'", bootstrap)
        self.assertIn("await limxConfirm(bgMsg('确定删除该项目？'", bootstrap)
        self.assertIn("await limxConfirm(bgMsg('停止后台运行？'", bootstrap)
        self.assertNotIn("confirm(", bootstrap)
        self.assertIn("hookBlocklyStackClickBlocker", bootstrap)
        self.assertIn("installStackClickRunGuard", bootstrap)
        self.assertIn("__limxBlockStackClickBlockedUntil", bootstrap)
        self.assertIn("isBlocklyFlyoutBlockArea", bootstrap)
        self.assertIn("__limxFlyoutStackClickGroupUntil", bootstrap)
        self.assertIn("__limxFlyoutStackClickAllowCount", bootstrap)
        self.assertIn("__limxSkipNextBootstrapStackClickConfirm", bootstrap)
        self.assertIn("__limxAllowNextSourceStackClickRun", bootstrap)
        self.assertIn("runtime.toggleScript", bootstrap)
        self.assertIn("postJson('/project/stop-modes'", bootstrap)
        self.assertNotIn("startBrowserTopLevelScripts", bootstrap)
        self.assertNotIn("_pushThread", bootstrap)
        self.assertNotIn("isGreenFlagControl", bootstrap)

    def test_editor_restores_background_running_state_on_reload(self):
        root = Path(__file__).resolve().parents[1]
        bootstrap = (root / "scratch-app" / "static" / "static" / "bootstrap.js").read_text(encoding="utf-8")

        self.assertIn("function applyBgStatus(data, startPoll)", bootstrap)
        self.assertIn("if (!bgStatusChecked) checkBgStatus();", bootstrap)
        self.assertIn("showBgIndicator(true);", bootstrap)
        self.assertIn("updateProjectButtons();", bootstrap)
        self.assertIn("applyBgStatus(data, false);", bootstrap)
        self.assertNotIn("__limxStopAllPatched", bootstrap)
        self.assertNotIn("vm.stopAll = function", bootstrap)

    def test_readonly_project_blocks_dragging_from_flyout(self):
        root = Path(__file__).resolve().parents[1]
        bootstrap = (root / "scratch-app" / "static" / "static" / "bootstrap.js").read_text(encoding="utf-8")

        self.assertIn("function projectReadonlyActive()", bootstrap)
        self.assertIn("node.closest('.blocklyFlyout')", bootstrap)
        self.assertIn("function blockReadonlyDrag(e)", bootstrap)
        self.assertIn("e.stopImmediatePropagation();", bootstrap)
        self.assertIn("hookReadonlyDragBlocker();", bootstrap)
        self.assertIn("workspace.classList.add('limx-project-readonly');", bootstrap)
        self.assertIn("workspace.classList.remove('limx-project-readonly');", bootstrap)

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
        self.assertIn("emojiNames", SCRATCH_EXTENSION_JS)
        self.assertIn("items: this.actionMenu", SCRATCH_EXTENSION_JS)
        self.assertIn("items: this.danceMenu", SCRATCH_EXTENSION_JS)
        self.assertIn("items: this.emojiMenu", SCRATCH_EXTENSION_JS)
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
        config.emoji_menu = [
            {"value": "screen-default", "zh": "screen-default", "en": "screen-default"},
            {"value": "voice-listen", "zh": "voice-listen", "en": "voice-listen"},
        ]

        js = render_extension_js(config)

        self.assertIn('"value": "wave_greet_bye"', js)
        self.assertIn('"zh": "挥手告别"', js)
        self.assertIn('"value": "solo_shake"', js)
        self.assertIn('"en": "Solo shake"', js)
        self.assertIn('"value": "screen-default"', js)
        self.assertNotIn("__LIMX_ACTION_MENU__", js)
        self.assertNotIn("__LIMX_DANCE_MENU__", js)
        self.assertNotIn("__LIMX_EMOJI_MENU__", js)
        self.assertNotIn("__LIMX_ROBOT_NAME__", js)
        self.assertNotIn("__LIMX_LANG__", js)
        self.assertNotIn("__LIMX_SUPPORTS_POSTURE_BLOCKS__", js)
        self.assertNotIn("__LIMX_SUPPORTS_EMOJI_BLOCKS__", js)
        self.assertIn('const __INITIAL_LANG__ = "";', js)
        self.assertIn("const supportsPostureBlocks = true;", js)
        self.assertIn("const supportsEmojiBlocks = false;", js)
        self.assertIn("function emojiBlocks()", js)

        en_js = render_extension_js(config, "en")
        self.assertIn('const __INITIAL_LANG__ = "en";', en_js)

        config.robot_name = "Luna"
        luna_js = render_extension_js(config)
        self.assertIn('const robotName = "Luna";', luna_js)
        self.assertIn("name: robotName + ' Robot'", luna_js)

        config.robot_accid = "HU_L_001"
        luna_js = render_extension_js(config)
        self.assertIn("const supportsPostureBlocks = false;", luna_js)
        self.assertIn("const supportsEmojiBlocks = true;", luna_js)
        self.assertIn("切换表情 [NAME]", luna_js)

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
        self.assertEqual(
            [
                {"value": "screen-default", "zh": "screen-default", "en": "screen-default"},
                {"value": "voice-listen", "zh": "voice-listen", "en": "voice-listen"},
            ],
            extract_emoji_menu(
                {
                    "emoji_list": [
                        "screen-default",
                        "",
                        "voice-listen",
                        "screen-default",
                    ]
                }
            ),
        )


if __name__ == "__main__":
    unittest.main()
