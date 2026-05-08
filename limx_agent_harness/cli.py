import argparse
import json
import os
import sys
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .client import RobotLockIdentity, SignalingClient, SignalingError


READ_ONLY_TITLES = {
    "request_get_locker_info",
    "request_get_atomic_motion_list",
    "request_get_action_library_status",
    "request_get_dance_list",
    "request_get_joint_state",
    "request_get_imu_data",
    "request_get_pose",
    "request_get_move_pose",
    "request_get_move_servo_pose",
    "request_audio_get_wakeup_word",
    "request_emoji_list",
    "request_emoji_get_default",
    "request_script_status",
    "request_script_records",
}

LONG_TASK_TIMEOUT = 660.0


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.print_help()
        return 2

    try:
        result = args.handler(args)
    except (SignalingError, ValueError) as exc:
        emit({"result": "fail_cli_error", "message": str(exc)}, args, error=True)
        return 1
    except KeyboardInterrupt:
        emit({"result": "fail_interrupted", "message": "Interrupted"}, args, error=True)
        return 130

    return 0 if result_is_success(result) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="limx-cli",
        description="Agent-native CLI for LimX Robot signaling WebSocket skills.",
    )
    parser.add_argument("--host", default=env_default("HOST", "10.192.1.2"))
    parser.add_argument("--port", type=int, default=int(env_default("PORT", "5000")))
    parser.add_argument("--wss", action="store_true", help="Use wss:// instead of ws://")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--dry-run", action="store_true", help="Print planned request(s) without connecting")
    parser.add_argument("--no-lock", action="store_true", help="Do not acquire robot control for mutating commands")
    parser.add_argument("--keep-lock", action="store_true", help="Keep control lock after command completion")
    parser.add_argument("--user", default=env_default("USER", "agent"))
    parser.add_argument("--user-id", default=env_default("USER_ID", "agent"))
    parser.add_argument("--device-id", "--device", default=env_default("DEVICE_ID", "limx-agent-harness"))

    subparsers = parser.add_subparsers(dest="group")
    add_raw_commands(subparsers)
    add_lock_commands(subparsers)
    add_action_commands(subparsers)
    add_dance_commands(subparsers)
    add_audio_commands(subparsers)
    add_emoji_commands(subparsers)
    add_state_commands(subparsers)
    add_motion_commands(subparsers)
    return parser


def env_default(name: str, default: str) -> str:
    return os.environ.get(f"LIMX_ROBOT_{name}", default)


def add_raw_commands(subparsers: argparse._SubParsersAction) -> None:
    raw = subparsers.add_parser("raw", help="Send any request_* title")
    raw.add_argument("title")
    raw.add_argument("--data", default="{}", help="JSON request data object")
    raw.add_argument("--lock", action="store_true", help="Acquire control before sending")
    raw.set_defaults(handler=handle_raw)


def add_lock_commands(subparsers: argparse._SubParsersAction) -> None:
    lock = subparsers.add_parser("lock", help="Manage robot control lock")
    commands = lock.add_subparsers(dest="lock_command", required=True)
    commands.add_parser("acquire", help="Acquire robot control").set_defaults(handler=handle_lock_acquire)
    commands.add_parser("release", help="Release robot control").set_defaults(handler=handle_lock_release)
    commands.add_parser("info", help="Show current lock owner").set_defaults(handler=handle_lock_info)


def add_action_commands(subparsers: argparse._SubParsersAction) -> None:
    action = subparsers.add_parser("action", help="Action library and atomic motions")
    commands = action.add_subparsers(dest="action_command", required=True)
    commands.add_parser("list", help="List atomic motions").set_defaults(handler=handle_action_list)
    commands.add_parser("status", help="Show action library status").set_defaults(handler=handle_action_status)
    commands.add_parser("enter", help="Enter action library mode").set_defaults(handler=handle_action_enter)
    commands.add_parser("exit", help="Exit action library mode").set_defaults(handler=handle_action_exit)
    run = commands.add_parser("run", help="Run one atomic motion")
    run.add_argument("--name", required=True, help="Action-library name from action list")
    run.add_argument("--timeout", type=float, default=120.0)
    run.set_defaults(handler=handle_action_run)


def add_dance_commands(subparsers: argparse._SubParsersAction) -> None:
    dance = subparsers.add_parser("dance", help="Dance library")
    commands = dance.add_subparsers(dest="dance_command", required=True)
    commands.add_parser("enter", help="Enter dance mode").set_defaults(handler=handle_dance_enter)
    commands.add_parser("list", help="List dances").set_defaults(handler=handle_dance_list)
    run = commands.add_parser("run", help="Run a dance or comma-separated action sequence")
    run.add_argument("--rc-mapping", required=True, help="Dance rc_mapping value from `dance list`")
    run.add_argument("--music", help="Optional music file or comma-separated music list")
    run.add_argument("--timeout", type=float, default=LONG_TASK_TIMEOUT)
    run.set_defaults(handler=handle_dance_run)


def add_audio_commands(subparsers: argparse._SubParsersAction) -> None:
    audio = subparsers.add_parser("audio", help="Audio playback and volume")
    commands = audio.add_subparsers(dest="audio_command", required=True)
    volume = commands.add_parser("set-volume", help="Set audio volume")
    volume.add_argument("volume", type=int)
    volume.set_defaults(handler=handle_audio_set_volume)
    play = commands.add_parser("play-file", help="Play an audio file on robot")
    play.add_argument("path")
    play.set_defaults(handler=handle_audio_play_file)
    playback = commands.add_parser("playback", help="Enable or disable playback")
    playback.add_argument("enabled", choices=["on", "off"])
    playback.set_defaults(handler=handle_audio_playback)


def add_emoji_commands(subparsers: argparse._SubParsersAction) -> None:
    emoji = subparsers.add_parser("emoji", help="Robot screen emoji")
    commands = emoji.add_subparsers(dest="emoji_command", required=True)
    commands.add_parser("list", help="List emojis").set_defaults(handler=handle_emoji_list)
    set_emoji = commands.add_parser("set", help="Set current emoji")
    set_emoji.add_argument("name")
    set_emoji.set_defaults(handler=handle_emoji_set)
    set_default = commands.add_parser("set-default", help="Set default emoji")
    set_default.add_argument("name")
    set_default.set_defaults(handler=handle_emoji_set_default)
    commands.add_parser("get-default", help="Get default emoji").set_defaults(handler=handle_emoji_get_default)
    delete = commands.add_parser("delete", help="Delete emoji")
    delete.add_argument("name")
    delete.set_defaults(handler=handle_emoji_delete)


def add_state_commands(subparsers: argparse._SubParsersAction) -> None:
    state = subparsers.add_parser("state", help="Read robot state")
    commands = state.add_subparsers(dest="state_command", required=True)
    commands.add_parser("joint", help="Get joint state").set_defaults(handler=lambda args: request_once(args, "request_get_joint_state", {}, False))
    commands.add_parser("imu", help="Get IMU data").set_defaults(handler=lambda args: request_once(args, "request_get_imu_data", {}, False))
    commands.add_parser("mode", help="Get current robot work mode").set_defaults(handler=lambda args: request_once(args, "request_get_robot_status", {}, False))
    commands.add_parser("pose", help="Get robot pose").set_defaults(handler=lambda args: request_once(args, "request_get_pose", {}, False))


def add_motion_commands(subparsers: argparse._SubParsersAction) -> None:
    motion = subparsers.add_parser("motion", help="High-risk robot motion commands")
    commands = motion.add_subparsers(dest="motion_command", required=True)
    walk = commands.add_parser("walk", help="Send walking velocity with bounded duration")
    walk.add_argument("--x", type=float, default=0.0)
    walk.add_argument("--y", type=float, default=0.0)
    walk.add_argument("--yaw", type=float, default=0.0)
    walk.add_argument("--duration", type=float, default=3.0)
    walk.add_argument("--rate-hz", type=float, default=10.0, help="Velocity command refresh rate")
    walk.add_argument("--timeout", type=float, default=10.0)
    walk.set_defaults(handler=handle_motion_walk)
    standup = commands.add_parser("standup", help="Enter standup state with IkStand fallback")
    standup.add_argument("--no-recover", action="store_true", help="Do not fall back to prepare/IkStand")
    standup.set_defaults(handler=handle_motion_standup)
    sit = commands.add_parser("sit", help="Stand to sit with action-library recovery")
    sit.add_argument("--mode", choices=["StandSit", "SitDown"], default="StandSit")
    sit.add_argument("--no-recover", action="store_true", help="Do not auto-exit action library or retry")
    sit.set_defaults(handler=handle_motion_sit)
    commands.add_parser("lie-down", help="Lie down").set_defaults(handler=lambda args: request_once(args, "request_lie_down", {}, True, LONG_TASK_TIMEOUT))
    commands.add_parser("prepare", help="Prepare robot").set_defaults(handler=lambda args: request_once(args, "request_prepare", {}, True, LONG_TASK_TIMEOUT))
    commands.add_parser("zero-torque", help="Enter zero torque").set_defaults(handler=lambda args: request_once(args, "request_zero_torque", {}, True, LONG_TASK_TIMEOUT))
    commands.add_parser("calibrate", help="Calibrate robot").set_defaults(handler=lambda args: request_once(args, "request_calibrate", {}, True, LONG_TASK_TIMEOUT))


def handle_raw(args: argparse.Namespace) -> Dict[str, Any]:
    title = normalize_title(args.title)
    data = parse_json_object(args.data)
    mutating = args.lock or title not in READ_ONLY_TITLES
    return request_once(args, title, data, mutating)


def handle_lock_acquire(args: argparse.Namespace) -> Dict[str, Any]:
    if args.dry_run:
        result = dry_run_response([("request_lock_robot_control", identity(args).as_request_data())])
        emit(result, args)
        return result
    client = make_client(args)
    try:
        client.connect()
        result = client.lock(identity(args))
        emit(result, args)
        if result_is_success(result) and args.keep_lock:
            hold_lock_until_interrupt(client, args)
        return result
    finally:
        client.close()


def handle_lock_release(args: argparse.Namespace) -> Dict[str, Any]:
    return request_once(args, "request_unlock_robot_control", {}, False)


def handle_lock_info(args: argparse.Namespace) -> Dict[str, Any]:
    return request_once(args, "request_get_locker_info", {}, False)


def handle_action_list(args: argparse.Namespace) -> Dict[str, Any]:
    return request_once(args, "request_get_atomic_motion_list", {}, False)


def handle_action_status(args: argparse.Namespace) -> Dict[str, Any]:
    return request_once(args, "request_get_action_library_status", {}, False)


def handle_action_enter(args: argparse.Namespace) -> Dict[str, Any]:
    return request_once(args, "request_set_motion_engine", {"mode": 1}, True, 10.0)


def handle_action_exit(args: argparse.Namespace) -> Dict[str, Any]:
    requests = [
        ("request_get_action_library_status", {}),
        ("request_set_motion_engine", {"mode": 0, "when": "action_library_idle"}),
    ]
    if args.dry_run:
        result = dry_run_response(requests)
        emit(result, args)
        return result

    client = make_client(args)
    locked = False
    try:
        client.connect()
        locked = maybe_lock(client, args, mutating=True)
        status = client.request("request_get_action_library_status", {}, 5.0)
        if action_library_is_running(status):
            result = {
                "result": "fail_action_running",
                "message": "Refusing to exit action library while an action or dance is running.",
                "status": status,
            }
            emit(result, args)
            return result
        if status.get("action_library_mode") != "action_library":
            result = {"result": "success", "status": status, "exit": {"result": "success", "noop": True}}
            emit(result, args)
            return result
        exit_result = client.request("request_set_motion_engine", {"mode": 0}, 10.0)
        result = {
            "result": "success" if result_is_success(exit_result) else "fail_action_exit",
            "status": status,
            "exit": exit_result,
        }
        emit(result, args)
        if locked and args.keep_lock and result_is_success(result):
            hold_lock_until_interrupt(client, args)
        return result
    finally:
        if locked and not args.keep_lock:
            try:
                client.unlock()
            finally:
                client.close()
        else:
            client.close()


def handle_action_run(args: argparse.Namespace) -> Dict[str, Any]:
    return request_once(args, "request_action_sync", {"name": args.name}, True, args.timeout)


def handle_dance_list(args: argparse.Namespace) -> Dict[str, Any]:
    return request_once(args, "request_get_dance_list", {}, False)


def handle_dance_enter(args: argparse.Namespace) -> Dict[str, Any]:
    return request_once(args, "request_enter_dance_mode", {"mode": 1}, True, 10.0)


def handle_dance_run(args: argparse.Namespace) -> Dict[str, Any]:
    data = {"name": args.rc_mapping}
    if args.music:
        data["music"] = args.music
    return request_once(args, "request_dance", data, True, args.timeout)


def handle_audio_set_volume(args: argparse.Namespace) -> Dict[str, Any]:
    return request_once(args, "request_audio_set_volume", {"volume": args.volume}, True)


def handle_audio_play_file(args: argparse.Namespace) -> Dict[str, Any]:
    return request_once(args, "request_audio_play_file", {"path": args.path}, True)


def handle_audio_playback(args: argparse.Namespace) -> Dict[str, Any]:
    return request_once(args, "request_audio_playback_control", {"enable": args.enabled == "on"}, True)


def handle_emoji_list(args: argparse.Namespace) -> Dict[str, Any]:
    return request_once(args, "request_emoji_list", {}, False)


def handle_emoji_set(args: argparse.Namespace) -> Dict[str, Any]:
    return request_once(args, "request_emoji_set", {"name": args.name}, True)


def handle_emoji_set_default(args: argparse.Namespace) -> Dict[str, Any]:
    return request_once(args, "request_emoji_set_default", {"name": args.name}, True)


def handle_emoji_get_default(args: argparse.Namespace) -> Dict[str, Any]:
    return request_once(args, "request_emoji_get_default", {}, False)


def handle_emoji_delete(args: argparse.Namespace) -> Dict[str, Any]:
    return request_once(args, "request_emoji_delete", {"name": args.name}, True)


def handle_motion_walk(args: argparse.Namespace) -> Dict[str, Any]:
    if args.duration <= 0:
        raise ValueError("--duration must be > 0")
    if args.rate_hz <= 0:
        raise ValueError("--rate-hz must be > 0")
    start = {"x": args.x, "y": args.y, "yaw": args.yaw}
    stop = {"x": 0.0, "y": 0.0, "yaw": 0.0}
    requests = [
        ("request_set_walk_mode", {}),
        (
            "repeat",
            {
                "title": "request_set_walk_vel_sync",
                "data": start,
                "duration": args.duration,
                "rate_hz": args.rate_hz,
                "count": command_count(args.duration, args.rate_hz),
            },
        ),
        ("request_set_walk_vel_sync", stop),
    ]
    if args.dry_run:
        result = dry_run_response(requests)
        emit(result, args)
        return result

    client = make_client(args)
    locked = False
    try:
        client.connect()
        locked = maybe_lock(client, args, mutating=True)
        mode = client.request("request_set_walk_mode", {}, LONG_TASK_TIMEOUT)
        if not walk_mode_is_ready(mode):
            result = {
                "result": "fail_walk_mode",
                "mode": mode,
                "start": None,
                "stop": None,
                "duration": args.duration,
            }
            emit(result, args)
            return result
        repeat = send_repeated_walk_velocity(client, start, args.duration, args.rate_hz, args.timeout)
        stop_result = client.request("request_set_walk_vel_sync", stop, args.timeout)
        result = {
            "result": "success" if result_is_success(repeat) and result_is_success(stop_result) else "fail_walk_sequence",
            "mode": mode,
            "walk": repeat,
            "stop": stop_result,
            "duration": args.duration,
            "rate_hz": args.rate_hz,
        }
        emit(result, args)
        if locked and args.keep_lock and result_is_success(result):
            hold_lock_until_interrupt(client, args)
        return result
    finally:
        if locked and not args.keep_lock:
            try:
                client.unlock()
            finally:
                client.close()
        else:
            client.close()


def handle_motion_standup(args: argparse.Namespace) -> Dict[str, Any]:
    requests = [("request_standup", {}), ("request_set_walk_mode", {"when": "standup_success"})]
    if not args.no_recover:
        requests.append(("request_prepare", {"when": "standup_fails"}))
    if args.dry_run:
        result = dry_run_response(requests)
        emit(result, args)
        return result

    client = make_client(args)
    locked = False
    recovery: List[Dict[str, Any]] = []
    try:
        client.connect()
        locked = maybe_lock(client, args, mutating=True)
        first = client.request("request_standup", {}, LONG_TASK_TIMEOUT)
        if result_is_success(first):
            walk_mode = client.request("request_set_walk_mode", {}, LONG_TASK_TIMEOUT)
            result = {
                "result": "success" if result_is_success(walk_mode) or walk_mode_is_ready(walk_mode) else "fail_walk_mode_after_standup",
                "standup": first,
                "walk_mode": walk_mode,
                "recovery": recovery,
            }
            emit(result, args)
            return result

        if not args.no_recover and first.get("result") in {
            "fail_sequence_error",
            "fail_invalid_mode",
            "fail_timeout",
        }:
            recovery.append({"step": "standup_first", "response": first})
            prepare = client.request("request_prepare", {}, LONG_TASK_TIMEOUT)
            recovery.append({"step": "prepare_ikstand", "response": prepare})
            if result_is_success(prepare) or standing_state_is_ready(prepare):
                walk_mode = client.request("request_set_walk_mode", {}, LONG_TASK_TIMEOUT)
                recovery.append({"step": "walk_mode_after_standup", "response": walk_mode})
                result = {
                    "result": "success" if result_is_success(walk_mode) or walk_mode_is_ready(walk_mode) else "fail_walk_mode_after_standup",
                    "standup": normalize_standup_success(prepare),
                    "walk_mode": walk_mode,
                    "recovery": recovery,
                }
                emit(result, args)
                return result

        result = {"result": "fail_standup_sequence", "standup": first, "recovery": recovery}
        emit(result, args)
        return result
    finally:
        if locked and not args.keep_lock:
            try:
                client.unlock()
            finally:
                client.close()
        else:
            client.close()


def handle_motion_sit(args: argparse.Namespace) -> Dict[str, Any]:
    data = {"mode": args.mode}
    requests = [("request_from_stand_to_sit", data)]
    if not args.no_recover:
        requests = [
            ("request_get_action_library_status", {}),
            ("request_set_motion_engine", {"mode": 0, "when": "action_library"}),
            ("request_from_stand_to_sit", data),
            ("request_set_walk_mode", {"when": "sit_returns_fail_invalid_mode"}),
            ("request_from_stand_to_sit", data),
        ]
    if args.dry_run:
        result = dry_run_response(requests)
        emit(result, args)
        return result

    client = make_client(args)
    locked = False
    recovery: List[Dict[str, Any]] = []
    try:
        client.connect()
        locked = maybe_lock(client, args, mutating=True)

        if not args.no_recover:
            status = client.request("request_get_action_library_status", {}, 5.0)
            recovery.append({"step": "action_status", "response": status})
            if status.get("action_library_mode") == "action_library":
                if action_library_is_running(status):
                    result = {
                        "result": "fail_action_running",
                        "message": "Refusing to sit while an action or dance is running.",
                        "recovery": recovery,
                    }
                    emit(result, args)
                    return result
                exit_result = client.request("request_set_motion_engine", {"mode": 0}, 30.0)
                recovery.append({"step": "action_exit", "response": exit_result})

        first = client.request("request_from_stand_to_sit", data, LONG_TASK_TIMEOUT)
        if sit_result_is_success(first, args.mode):
            result = {
                "result": "success",
                "sit": normalize_sit_success(first, args.mode),
                "recovery": recovery,
            }
            emit(result, args)
            return result

        if not args.no_recover and first.get("result") == "fail_invalid_mode":
            recovery.append({"step": "sit_first", "response": first})
            walk_probe = client.request("request_set_walk_mode", {}, 30.0)
            recovery.append({"step": "walk_mode_probe", "response": walk_probe})

            if seated_state_is_ready(walk_probe, args.mode):
                result = {
                    "result": "success",
                    "sit": normalize_sit_success(walk_probe, args.mode),
                    "recovery": recovery,
                }
                emit(result, args)
                return result

            if walk_mode_is_ready(walk_probe):
                retry = client.request("request_from_stand_to_sit", data, LONG_TASK_TIMEOUT)
                recovery.append({"step": "sit_retry", "response": retry})
                if sit_result_is_success(retry, args.mode):
                    result = {
                        "result": "success",
                        "sit": normalize_sit_success(retry, args.mode),
                        "recovery": recovery,
                    }
                    emit(result, args)
                    return result

        result = {
            "result": "fail_sit_sequence",
            "sit": first,
            "recovery": recovery,
        }
        emit(result, args)
        return result
    finally:
        if locked and not args.keep_lock:
            try:
                client.unlock()
            finally:
                client.close()
        else:
            client.close()


def request_once(
    args: argparse.Namespace,
    title: str,
    data: Dict[str, Any],
    mutating: bool,
    timeout: Optional[float] = None,
) -> Dict[str, Any]:
    title = normalize_title(title)
    if args.dry_run:
        result = dry_run_response([(title, data)])
        emit(result, args)
        return result

    client = make_client(args)
    locked = False
    try:
        client.connect()
        locked = maybe_lock(client, args, mutating)
        result = client.request(title, data, timeout or args.timeout)
        emit(result, args)
        if locked and args.keep_lock and result_is_success(result):
            hold_lock_until_interrupt(client, args)
        return result
    finally:
        if locked and not args.keep_lock:
            try:
                client.unlock()
            finally:
                client.close()
        else:
            client.close()


def maybe_lock(client: SignalingClient, args: argparse.Namespace, mutating: bool) -> bool:
    if not mutating or args.no_lock:
        return False
    result = client.lock(identity(args))
    if not result_is_success(result):
        raise SignalingError(f"Failed to acquire robot control: {json.dumps(result, ensure_ascii=False)}")
    return True


def send_repeated_walk_velocity(
    client: SignalingClient,
    velocity: Dict[str, float],
    duration: float,
    rate_hz: float,
    timeout: float,
) -> Dict[str, Any]:
    interval = 1.0 / rate_hz
    count = command_count(duration, rate_hz)
    failures: List[Dict[str, Any]] = []
    start_time = time.monotonic()

    for index in range(count):
        result = client.request("request_set_walk_vel_sync", velocity, timeout)
        if not result_is_success(result):
            failures.append({"index": index, "response": result})
            break

        next_tick = start_time + ((index + 1) * interval)
        remaining = next_tick - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)

    elapsed = time.monotonic() - start_time
    if failures:
        return {
            "result": "fail_walk_tick",
            "sent": count - len(failures),
            "expected": count,
            "elapsed": elapsed,
            "failures": failures,
        }
    return {
        "result": "success",
        "sent": count,
        "expected": count,
        "elapsed": elapsed,
    }


def command_count(duration: float, rate_hz: float) -> int:
    return max(1, int(round(duration * rate_hz)))


def hold_lock_until_interrupt(client: SignalingClient, args: argparse.Namespace) -> None:
    print("lock: holding control connection; press Ctrl+C to release", file=sys.stderr)
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        try:
            client.unlock()
        except SignalingError:
            pass


def make_client(args: argparse.Namespace) -> SignalingClient:
    return SignalingClient(
        host=args.host,
        port=args.port,
        secure=args.wss,
        connect_timeout=args.connect_timeout,
        default_timeout=args.timeout,
    )


def identity(args: argparse.Namespace) -> RobotLockIdentity:
    return RobotLockIdentity(
        user_name=args.user,
        user_id=args.user_id,
        device_id=args.device_id,
    )


def normalize_title(title: str) -> str:
    return title if title.startswith("request_") else f"request_{title}"


def parse_json_object(text: str) -> Dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"--data must be a JSON object: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("--data must be a JSON object")
    return value


def dry_run_response(requests: Iterable[Tuple[str, Dict[str, Any]]]) -> Dict[str, Any]:
    planned = []
    for title, data in requests:
        planned.append({"title": title, "data": data})
    return {"result": "success", "dry_run": True, "requests": planned}


def result_is_success(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    return result.get("result", "success") == "success"


def action_library_is_running(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    return (
        result.get("action_library_mode") == "action_library"
        and result.get("action_library_state") == "running"
    )


def walk_mode_is_ready(result: Any) -> bool:
    if result_is_success(result):
        return True
    if not isinstance(result, dict):
        return False
    return (
        result.get("result") == "fail_state_not_allowed"
        and result.get("current_state") == "Walk"
    )


def sit_result_is_success(result: Any, mode: str) -> bool:
    if result_is_success(result):
        return True
    return seated_state_is_ready(result, mode)


def seated_state_is_ready(result: Any, mode: str) -> bool:
    if not isinstance(result, dict):
        return False
    target_states = {
        "StandSit": {"StandSit"},
        "SitDown": {"SitDown"},
    }
    return result.get("current_state") in target_states.get(mode, set())


def normalize_sit_success(result: Dict[str, Any], mode: str) -> Dict[str, Any]:
    if result_is_success(result):
        return result
    normalized = dict(result)
    normalized["result"] = "success"
    normalized["message"] = f"already in {normalized.get('current_state', mode)}"
    return normalized


def standing_state_is_ready(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    return result.get("current_state") in {"Walk", "IkStand", "StandUp", "SitStand"}


def normalize_standup_success(result: Dict[str, Any]) -> Dict[str, Any]:
    if result_is_success(result):
        normalized = dict(result)
        normalized.setdefault("message", "entered standing state")
        return normalized
    normalized = dict(result)
    normalized["result"] = "success"
    normalized["message"] = f"already in {normalized.get('current_state', 'standing state')}"
    return normalized


def emit(result: Dict[str, Any], args: argparse.Namespace, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), file=stream)


def format_human(value: Any, indent: int = 0) -> str:
    prefix = " " * indent
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.append(format_human(item, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {item}")
        return "\n".join(lines)
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, dict):
                lines.append(format_human(item, indent))
            else:
                lines.append(f"{prefix}- {item}")
        return "\n".join(lines)
    return f"{prefix}{value}"


if __name__ == "__main__":
    raise SystemExit(main())
