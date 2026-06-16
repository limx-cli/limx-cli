---
name: limx-cli
description: Control LimX robot skills through the signaling WebSocket request API using the limx-cli.
---

# LimX CLI Skill

Use `limx-cli` when you need to inspect or operate an LimX robot through the running
`signaling` WebSocket service.

## Connection

```bash
limx-cli --host <robot-ip> --port 5000 <command>
```

Environment variables:

- `LIMX_ROBOT_HOST`: default robot IP.
- `LIMX_ROBOT_PORT`: default WebSocket port.
- `LIMX_ROBOT_USER`, `LIMX_ROBOT_USER_ID`, `LIMX_ROBOT_DEVICE_ID`: identity used when `--lock` is requested.

## Important Rules

- CLI output is JSON by default for agent workflows.
- Run `--dry-run` before any motion, dance, action, audio playback, or emoji mutation.
- Mutating commands do not acquire `request_lock_robot_control` by default.
- Add global `--lock` before the command only when the user explicitly asks to
  own robot control for that operation, for example `limx-cli --lock motion walk ...`.
- When `--lock` is used, the CLI releases the control lock after the command
  finishes or raises an error.
- For movement, always use bounded commands such as `motion walk --duration`.
  Walking is step-based, so the CLI refreshes velocity at `--rate-hz` while the
  duration is active.
- For Scratch orchestration, start `limx-scratch` and load its
  `/extension.js` URL in Scratch. The bridge only exposes a safe allowlist of
  CLI commands.

## Discovery Commands

```bash
limx-cli lock info
limx-cli action status
limx-cli action list
limx-cli dance list
limx-cli emoji list
limx-cli state joint
```

## Action Library

```bash
limx-cli action enter
limx-cli action run --name <action-library-name> --timeout 120
limx-cli action exit
```

Use `action list` first to find valid `id`, `rc_mapping`, `motion_name_en`, or
`motion_name_cn` values. Action execution always maps to signaling
`request_action_sync` and sends the value as `data.name`; do not use the
`request_execute_atomic_motion` path.

## Dance

```bash
limx-cli dance list
limx-cli dance run --rc-mapping <dance-rc-mapping> --timeout 660
limx-cli dance run --rc-mapping "dance1,dance2" --music "song1.mp3,song2.mp3"
```

Use `dance list` first and pass the `rc_mapping` value, not the Chinese
display `name`. The signaling request still uses the protocol field
`data.name`, but that value must be a dance `rc_mapping`.

Do not stop a running dance with `action exit` or `request_set_motion_engine`
`mode=0`; the CLI refuses this when action-library state is `running`.

## Audio

```bash
limx-cli audio set-volume 60
limx-cli audio play-file /path/on/robot.wav
```

## Emoji

```bash
limx-cli emoji list
limx-cli emoji set smile
limx-cli emoji set-default smile
limx-cli emoji get-default
```

## Motion

```bash
limx-cli --dry-run motion walk --x 0.1 --duration 3 --rate-hz 10
limx-cli motion walk --x 0.1 --duration 3 --rate-hz 10
limx-cli motion standup
limx-cli motion sit
limx-cli motion lie-down
```

`motion walk` first sends `request_set_walk_mode`, then sends
`request_set_walk_vel_sync` repeatedly at the requested `--rate-hz`, and finally
sends a zero-velocity stop command.

`motion standup` first tries `request_standup`; if the robot is in Damped and the
controller sequence reports an error, it falls back to `request_prepare` to enter
IkStand.

Scratch's "enter standing mode" block is intentionally lighter than `motion standup`:
it sends raw `request_standup` with `{"mode": "hanging"}` so Damped can enter
IkStand quickly without waiting for the full sit/lie standup sequence. The
separate "stand up" block still uses the full `motion standup` flow.

`motion sit` first checks action-library status. If the robot is in idle action
library/Menu after a dance, it exits to Walk before requesting StandSit. If
action-library state is `running`, it fails instead of interrupting a dance or
action. If the server reports `current_state` as `StandSit` or `SitDown`, the
command treats the robot as already seated.

## Raw Escape Hatch

Use raw only when a command group does not yet expose the required request:

```bash
limx-cli raw request_get_joint_state --data '{}'
limx-cli --lock raw request_audio_play_file --data '{"path":"/path/on/robot.wav"}'
```

Raw requests are sent without a control lock by default. Add global `--lock` to
acquire robot control for a raw request.
