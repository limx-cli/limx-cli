import argparse
import io
import json
import mimetypes
import os
import signal
import shutil
import subprocess
import sys
import threading
import time
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, quote, urlparse

from .client import SignalingClient


DEFAULT_LISTEN_HOST = "0.0.0.0"
DEFAULT_LISTEN_PORT = 6080
DEFAULT_ROBOT_HOST = "10.192.1.2"
DEFAULT_ROBOT_PORT = 5000
DEFAULT_COMMAND_TIMEOUT = 700.0
DEFAULT_MENU_TIMEOUT = 20.0
DEFAULT_PYTHON = "python3"
DEFAULT_STATIC_DIR = str(Path(__file__).resolve().parent.parent / "scratch-static")
READ_ONLY_BRIDGE_COMMANDS = {
    "lock_info",
    "action_status",
    "action_list",
    "dance_list",
    "emoji_list",
    "state",
    "work_mode",
}
SCRATCH_EXTENSION_ID = "limxRobot"


SCRATCH_EXTENSION_JS = r"""
(function (Scratch) {
  'use strict';

  let baseUrl = 'http://127.0.0.1:6080';
  try {
    if (typeof document !== 'undefined' && document.currentScript && document.currentScript.src) {
      baseUrl = document.currentScript.src.replace(/\/extension\.js.*/, '');
    } else if (typeof location !== 'undefined' && /\/extension\.js/.test(location.href)) {
      baseUrl = location.href.replace(/\/extension\.js.*/, '');
    }
  } catch (error) {
    baseUrl = 'http://127.0.0.1:6080';
  }

  async function run(command, args) {
    const response = await fetch(baseUrl + '/run', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({command, args: args || {}})
    });
    const data = await response.json();
    return JSON.stringify(data);
  }

  let commandQueue = Promise.resolve();

  function enqueue(command, args) {
    const task = commandQueue.then(function () {
      return run(command, args);
    });
    commandQueue = task.catch(function () {
      return undefined;
    });
    return task;
  }

  function parseResult(text) {
    try {
      return JSON.parse(text);
    } catch (error) {
      return {};
    }
  }

  function normalizeLanguage(value) {
    const text = String(value || '').toLowerCase().replace('_', '-');
    if (text.indexOf('zh') === 0 || text === 'chinese') return 'zh-cn';
    if (text.indexOf('en') === 0 || text === 'english') return 'en';
    return '';
  }

  const __INITIAL_LANG__ = __LIMX_LANG__;

  function locale() {
    const injected = normalizeLanguage(__INITIAL_LANG__);
    if (injected) return injected;
    try {
      if (typeof Scratch !== 'undefined' && Scratch.translate) {
        const sl = normalizeLanguage(Scratch.translate.language);
        if (sl) return sl;
      }
    } catch (_) {}
    return normalizeLanguage(__INITIAL_LANG__) || normalizeLanguage(navigator.language) || 'zh-cn';
  }

  function isChinese() {
    return locale().indexOf('zh') === 0;
  }

  function t(zh, en) {
    return isChinese() ? zh : en;
  }

  function menuLabel(item) {
    if (typeof item === 'string') return item;
    const zh = item.zh || item.cn || item.text || item.value;
    const en = item.en || item.text || item.value || zh;
    return t(zh, en);
  }

  function menuValue(item) {
    if (typeof item === 'string') return item;
    return item.value || item.en || item.zh || item.text || '';
  }

  function addMenuAlias(valuesByLabel, alias, value) {
    const key = String(alias || '').trim();
    const realValue = String(value || '').trim();
    if (!key || !realValue) return;
    valuesByLabel[key] = realValue;
    const normalized = key
      .toLowerCase()
      .replace(/[（(].*?[）)]/g, '')
      .replace(/[\s_\-\/]+/g, '')
      .trim();
    if (normalized) valuesByLabel[normalized] = realValue;
  }

  function resolveMenuValue(valuesByLabel, value) {
    const key = String(value || '').trim();
    if (!key) return key;
    const normalized = key
      .toLowerCase()
      .replace(/[（(].*?[）)]/g, '')
      .replace(/[\s_\-\/]+/g, '')
      .trim();
    return valuesByLabel[key] || valuesByLabel[normalized] || key;
  }

  function initialMenu(items, fallback, valuesByLabel) {
    if (!Array.isArray(items) || !items.length) {
      items = fallback.slice();
    }
    return items.map(function (item) {
      const label = String(menuLabel(item));
      const value = String(menuValue(item));
      addMenuAlias(valuesByLabel, label, value);
      addMenuAlias(valuesByLabel, value, value);
      if (item && typeof item === 'object') {
        Object.keys(item).forEach(function (key) {
          if (key !== 'value') addMenuAlias(valuesByLabel, item[key], value);
        });
      }
      return label;
    });
  }

  const initialActionMenu = __LIMX_ACTION_MENU__;
  const initialDanceMenu = __LIMX_DANCE_MENU__;
  const initialEmojiMenu = __LIMX_EMOJI_MENU__;
  const robotName = __LIMX_ROBOT_NAME__;
  const supportsPostureBlocks = __LIMX_SUPPORTS_POSTURE_BLOCKS__;
  const supportsEmojiBlocks = __LIMX_SUPPORTS_EMOJI_BLOCKS__;
  const LIMX_BLOCK_PRIMARY = '#17C7FF';
  const LIMX_BLOCK_SECONDARY = '#0F8FBD';
  const LIMX_BLOCK_TERTIARY = '#075C86';
  const LIMX_DANGER_PRIMARY = '#FF5A66';
  const LIMX_DANGER_SECONDARY = '#D9364A';
  const LIMX_DANGER_TERTIARY = '#981B2D';

  function postureBlocks() {
    if (!supportsPostureBlocks) {
      return [];
    }
    return [
      {
        opcode: 'standup',
        blockType: Scratch.BlockType.COMMAND,
        text: t('站起', 'stand up')
      },
      {
        opcode: 'sit',
        blockType: Scratch.BlockType.COMMAND,
        text: t('坐下', 'sit')
      },
      {
        opcode: 'lieDown',
        blockType: Scratch.BlockType.COMMAND,
        text: t('躺下', 'lie down')
      }
    ];
  }

  function emojiBlocks() {
    if (!supportsEmojiBlocks) {
      return [];
    }
    return [
      {
        opcode: 'emojiSet',
        blockType: Scratch.BlockType.COMMAND,
        text: t('切换表情 [NAME]', 'set emoji [NAME]'),
        arguments: {
          NAME: {
            type: Scratch.ArgumentType.STRING,
            menu: 'emojiNames',
            defaultValue: this.emojiMenu[0] || 'screen-default'
          }
        }
      }
    ];
  }

  class LimXRobotExtension {
    getInfo() {
      return {
        id: 'limxRobot',
        name: robotName + ' Robot',
        color1: LIMX_BLOCK_PRIMARY,
        color2: LIMX_BLOCK_SECONDARY,
        color3: LIMX_BLOCK_TERTIARY,
        blocks: [
          {
            opcode: 'state',
            blockType: Scratch.BlockType.REPORTER,
            text: t('机器人状态 [KIND]', 'robot state [KIND]'),
            arguments: {
              KIND: {
                type: Scratch.ArgumentType.STRING,
                menu: 'stateKinds',
                defaultValue: t('运行', 'running')
              }
            }
          },
          {
            opcode: 'walk',
            blockType: Scratch.BlockType.COMMAND,
            text: t('行走 前后 [X] 左右 [Y] 转向 [YAW] 秒 [DURATION]', 'walk x [X] y [Y] yaw [YAW] seconds [DURATION]'),
            arguments: {
              X: {type: Scratch.ArgumentType.NUMBER, defaultValue: 0.2},
              Y: {type: Scratch.ArgumentType.NUMBER, defaultValue: 0},
              YAW: {type: Scratch.ArgumentType.NUMBER, defaultValue: 0},
              DURATION: {type: Scratch.ArgumentType.NUMBER, defaultValue: 2}
            }
          },
          {
            opcode: 'actionRun',
            blockType: Scratch.BlockType.COMMAND,
            text: t('动作 [NAME]', 'action [NAME]'),
            arguments: {
              NAME: {
                type: Scratch.ArgumentType.STRING,
                menu: 'actionNames',
                defaultValue: this.actionMenu[0] || '挥手告别'
              }
            }
          },
          {
            opcode: 'danceRun',
            blockType: Scratch.BlockType.COMMAND,
            text: t('跳舞 [RC_MAPPING]', 'dance [RC_MAPPING]'),
            arguments: {
              RC_MAPPING: {
                type: Scratch.ArgumentType.STRING,
                menu: 'danceMappings',
                defaultValue: this.danceMenu[0] || '孤身摇'
              }
            }
          },
          ...emojiBlocks.call(this),
          ...postureBlocks(),
          {
            opcode: 'enterStandMode',
            blockType: Scratch.BlockType.COMMAND,
            text: t('进入站立模式', 'enter standing mode')
          },
          {
            opcode: 'enterWalkMode',
            blockType: Scratch.BlockType.COMMAND,
            text: t('进入行走模式', 'enter walk mode')
          },
          {
            opcode: 'enterActionMode',
            blockType: Scratch.BlockType.COMMAND,
            text: t('进入动作模式', 'enter action mode')
          },
          {
            opcode: 'enterDanceMode',
            blockType: Scratch.BlockType.COMMAND,
            text: t('进入舞蹈模式', 'enter dance mode')
          },
          {
            opcode: 'enterDampedMode',
            blockType: Scratch.BlockType.COMMAND,
            text: t('进入阻尼模式', 'enter damped mode'),
            color1: LIMX_DANGER_PRIMARY,
            color2: LIMX_DANGER_SECONDARY,
            color3: LIMX_DANGER_TERTIARY
          },
          {
            opcode: 'enterZeroTorqueMode',
            blockType: Scratch.BlockType.COMMAND,
            text: t('进入零力矩模式', 'enter zero torque mode'),
            color1: LIMX_DANGER_PRIMARY,
            color2: LIMX_DANGER_SECONDARY,
            color3: LIMX_DANGER_TERTIARY
          }
        ],
        menus: {
          stateKinds: {
            acceptReporters: true,
            items: [t('运行', 'running'), t('关节', 'joint'), t('IMU', 'imu')]
          },
          actionNames: {
            acceptReporters: false,
            items: this.actionMenu
          },
          danceMappings: {
            acceptReporters: false,
            items: this.danceMenu
          },
          emojiNames: {
            acceptReporters: false,
            items: this.emojiMenu
          }
        }
      };
    }

    constructor() {
      this.last = '';
      this.actionValuesByLabel = {};
      this.danceValuesByLabel = {};
      this.emojiValuesByLabel = {};
      this.stateValuesByLabel = {};
      this.stateValuesByLabel[t('运行', 'running')] = 'work_mode';
      this.stateValuesByLabel[t('关节', 'joint')] = 'joint';
      this.stateValuesByLabel[t('IMU', 'imu')] = 'imu';
      this.actionMenu = initialMenu(initialActionMenu, [{value: 'wave_greet_bye', zh: '挥手告别', en: 'wave_greet_bye'}], this.actionValuesByLabel);
      this.danceMenu = initialMenu(initialDanceMenu, [{value: 'solo_shake', zh: '孤身摇', en: 'solo_shake'}], this.danceValuesByLabel);
      this.emojiMenu = initialMenu(initialEmojiMenu, [{value: 'screen-default', zh: 'screen-default', en: 'screen-default'}], this.emojiValuesByLabel);
    }

    async remember(promise) {
      this.last = await promise;
      return this.last;
    }

    getActionMenu() {
      return this.actionMenu;
    }

    getDanceMenu() {
      return this.danceMenu;
    }

    getEmojiMenu() {
      return this.emojiMenu;
    }

    async refreshActionMenu() {
      const data = parseResult(await enqueue('action_list'));
      const motions = Array.isArray(data.motion_list) ? data.motion_list : [];
      const items = [];
      const seen = new Set();
      for (const motion of motions) {
        const value = motion.motion_name_en;
        if (!value || seen.has(value)) continue;
        seen.add(value);
        items.push({
          value: String(value),
          zh: String(motion.motion_name_cn || motion.name_cn || motion.chinese_name || value),
          en: String(motion.motion_name_en || value)
        });
      }
      if (items.length) {
        this.actionValuesByLabel = {};
        this.actionMenu = initialMenu(items, [], this.actionValuesByLabel);
      }
    }

    async refreshDanceMenu() {
      const data = parseResult(await enqueue('dance_list'));
      const dances = Array.isArray(data.dances) ? data.dances : [];
      const items = [];
      const seen = new Set();
      for (const dance of dances) {
        const value = dance.rc_mapping;
        if (!value || seen.has(value)) continue;
        seen.add(value);
        items.push({
          value: String(value),
          zh: String(dance.name_cn || dance.dance_name_cn || dance.chinese_name || dance.name || value),
          en: String(dance.english_name || dance.name_en || dance.dance_name_en || dance.name || value)
        });
      }
      if (items.length) {
        this.danceValuesByLabel = {};
        this.danceMenu = initialMenu(items, [], this.danceValuesByLabel);
      }
    }

    async refreshEmojiMenu() {
      if (!supportsEmojiBlocks) return;
      const data = parseResult(await enqueue('emoji_list'));
      const emojis = Array.isArray(data.emoji_list) ? data.emoji_list : [];
      const items = [];
      const seen = new Set();
      for (const emoji of emojis) {
        const value = String(emoji || '').trim();
        if (!value || seen.has(value)) continue;
        seen.add(value);
        items.push({value, zh: value, en: value});
      }
      if (items.length) {
        this.emojiValuesByLabel = {};
        this.emojiMenu = initialMenu(items, [], this.emojiValuesByLabel);
      }
    }

    async loadMenus() {
      await Promise.all([this.refreshActionMenu(), this.refreshDanceMenu(), this.refreshEmojiMenu()]);
      this.last = JSON.stringify({
        result: 'success',
        action_menu_count: this.actionMenu.length,
        dance_menu_count: this.danceMenu.length,
        emoji_menu_count: this.emojiMenu.length
      });
      return this.last;
    }

    lockInfo() {
      return this.remember(enqueue('lock_info'));
    }

    actionStatus() {
      return this.remember(enqueue('action_status'));
    }

    actionList() {
      return this.remember(enqueue('action_list'));
    }

    danceList() {
      return this.remember(enqueue('dance_list'));
    }

    emojiList() {
      return this.remember(enqueue('emoji_list'));
    }

    refreshMenus() {
      return this.remember(this.loadMenus());
    }

    state(args) {
      const kind = this.stateValuesByLabel[args.KIND] || args.KIND;
      if (kind === 'work_mode') {
        return this.remember(enqueue('work_mode'));
      }
      return this.remember(enqueue('state', {kind}));
    }

    enterActionMode() {
      return this.remember(enqueue('action_enter'));
    }

    enterStandMode() {
      return this.remember(enqueue('stand_mode'));
    }

    enterDampedMode() {
      return this.remember(enqueue('damped_mode'));
    }

    enterZeroTorqueMode() {
      return this.remember(enqueue('zero_torque'));
    }

    enterWalkMode() {
      return this.remember(enqueue('walk_mode'));
    }

    enterDanceMode() {
      return this.remember(enqueue('dance_mode'));
    }

    actionRun(args) {
      return this.remember(enqueue('action_run', {name: resolveMenuValue(this.actionValuesByLabel, args.NAME)}));
    }

    danceRun(args) {
      return this.remember(enqueue('dance_run', {rc_mapping: resolveMenuValue(this.danceValuesByLabel, args.RC_MAPPING)}));
    }

    walk(args) {
      return this.remember(enqueue('walk', {
        x: args.X,
        y: args.Y,
        yaw: args.YAW,
        duration: args.DURATION
      }));
    }

    standup() {
      return this.remember(enqueue('standup'));
    }

    sit() {
      return this.remember(enqueue('sit'));
    }

    lieDown() {
      return this.remember(enqueue('lie_down'));
    }

    emojiSet(args) {
      return this.remember(enqueue('emoji_set', {name: resolveMenuValue(this.emojiValuesByLabel, args.NAME)}));
    }

    volumeSet(args) {
      return this.remember(enqueue('volume_set', {volume: args.VOLUME}));
    }

    lastResult() {
      return this.last;
    }
  }

  Scratch.extensions.register(new LimXRobotExtension());
})(Scratch);
"""


class BridgeConfig:
    def __init__(
        self,
        robot_host: str,
        robot_port: int,
        command_timeout: float,
        dry_run: bool = False,
        python: str = DEFAULT_PYTHON,
        menu_timeout: float = DEFAULT_MENU_TIMEOUT,
        node: Optional[str] = None,
        action_menu: Optional[List[Dict[str, str]]] = None,
        dance_menu: Optional[List[Dict[str, str]]] = None,
        emoji_menu: Optional[List[Dict[str, str]]] = None,
        static_dir: Optional[str] = None,
        robot_accid: str = "",
        robot_name: str = "LimX",
    ) -> None:
        self.robot_host = robot_host
        self.robot_port = robot_port
        self.command_timeout = command_timeout
        self.menu_timeout = menu_timeout
        self.dry_run = dry_run
        self.python = python
        self.node = node or default_node_path()
        self.action_menu = action_menu or [{"value": "wave_greet_bye", "zh": "挥手告别", "en": "wave_greet_bye"}]
        self.dance_menu = dance_menu or [{"value": "solo_shake", "zh": "孤身摇", "en": "solo_shake"}]
        self.emoji_menu = emoji_menu or [{"value": "screen-default", "zh": "screen-default", "en": "screen-default"}]
        self.static_dir = static_dir
        self.robot_accid = robot_accid
        self.robot_name = robot_name
        self.ui_lang = ""
        self.command_lock = threading.Lock()
        self.active_command_lock = threading.Lock()
        self.active_command: Optional[subprocess.Popen] = None
        self.project_dir = ""
        self.scratch_app_dir = default_scratch_app_dir()
        self.listen_port = DEFAULT_LISTEN_PORT
        self.runner: Optional["ProjectRunner"] = None


LEGACY_PROJECT_DIR = Path(__file__).resolve().parent.parent / "scratch-projects"
DEFAULT_PROJECT_DIR = str(Path.home() / ".scratch-projects")
RUNNER_SCRIPT = str(Path(__file__).resolve().parent / "scratch_runner.js")


def default_scratch_app_dir() -> str:
    package_dir = Path(__file__).resolve().parent
    vendor_dir = package_dir / "vendor" / "scratch-app"
    vendor_vm = vendor_dir / "node_modules" / "scratch-vm" / "src" / "index.js"
    if vendor_vm.exists():
        return str(vendor_dir)
    return str(package_dir.parent / "scratch-app")


def default_node_path() -> str:
    env_node = os.environ.get("LIMX_SCRATCH_NODE")
    if env_node:
        return env_node

    package_dir = Path(__file__).resolve().parent
    target_node = package_dir.parent.parent / "node" / "bin" / "node"
    if target_node.exists():
        return str(target_node)

    return "node"


def sanitize_scratch_project(data: bytes) -> bytes:
    """Normalize locally managed .sb3 metadata before saving it."""
    try:
        with zipfile.ZipFile(io.BytesIO(data), "r") as zin:
            entries = [(info, zin.read(info.filename)) for info in zin.infolist()]
    except zipfile.BadZipFile:
        return data

    changed = False
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for info, payload in entries:
            if info.filename == "project.json":
                try:
                    project = json.loads(payload.decode("utf-8"))
                except Exception:
                    zout.writestr(info, payload)
                    continue
                normalized = normalize_project_json(project)
                next_payload = json.dumps(normalized, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                changed = changed or next_payload != payload
                payload = next_payload
            zout.writestr(info, payload)
    return output.getvalue() if changed else data


def normalize_project_json(project: Any) -> Any:
    if not isinstance(project, dict):
        return project

    meta = project.get("meta")
    if isinstance(meta, dict):
        # TurboWarp writes this as source metadata. It is not required for local LimX projects.
        meta.pop("platform", None)

    normalize_extension_metadata(project)
    for target in project.get("targets", []):
        if isinstance(target, dict):
            normalize_extension_metadata(target)
    return project


def normalize_extension_metadata(container: Dict[str, Any]) -> None:
    extension_urls = container.get("extensionURLs")
    if isinstance(extension_urls, dict):
        extension_urls.pop(SCRATCH_EXTENSION_ID, None)
        if extension_urls:
            container["extensionURLs"] = extension_urls
        else:
            container.pop("extensionURLs", None)


class ProjectRunner:
    """Manages a headless scratch-vm Node.js subprocess."""

    def __init__(self, config: "BridgeConfig") -> None:
        self._config = config
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._project_name = ""
        self._started_at = 0.0
        self._events: List[Dict[str, Any]] = []

    @property
    def project_dir(self) -> str:
        d = robot_project_dir(self._config)
        os.makedirs(d, exist_ok=True)
        self._migrate_legacy_projects(d)
        return d

    def _migrate_legacy_projects(self, dest_dir: str) -> None:
        dest = Path(dest_dir).expanduser().resolve()
        legacy = LEGACY_PROJECT_DIR.resolve()
        if dest == legacy or not legacy.is_dir():
            return
        try:
            has_projects = any(dest.glob("*.sb3"))
            legacy_projects = list(legacy.glob("*.sb3"))
        except OSError:
            return
        if has_projects or not legacy_projects:
            return
        for project in legacy_projects:
            target = dest / project.name
            if not target.exists():
                try:
                    shutil.copy2(project, target)
                except OSError as exc:
                    print(f"[scratch-bridge] failed to migrate project {project.name}: {exc}", file=sys.stderr)

    def save_project(self, name: str, data: bytes) -> str:
        name = os.path.basename(name)
        if not name.endswith(".sb3"):
            name += ".sb3"
        dest = os.path.join(self.project_dir, name)
        if os.path.exists(dest):
            raise FileExistsError(f'project already exists: {name}')
        with open(dest, "wb") as f:
            f.write(sanitize_scratch_project(data))
        return dest

    def overwrite_project(self, name: str, data: bytes) -> str:
        name = os.path.basename(name)
        if not name:
            raise ValueError("name is required")
        if not name.endswith(".sb3"):
            name += ".sb3"
        dest = os.path.join(self.project_dir, name)
        if not os.path.isfile(dest):
            raise FileNotFoundError(f"project not found: {name}")
        with open(dest, "wb") as f:
            f.write(sanitize_scratch_project(data))
        return dest

    def create_empty_project(self, name: str) -> str:
        name = os.path.basename(name)
        if not name:
            raise ValueError("name is required")
        if not name.endswith(".sb3"):
            name += ".sb3"
        dest = os.path.join(self.project_dir, name)
        if os.path.exists(dest):
            raise FileExistsError(f'project already exists: {name}')
        project = {
            "targets": [
                {
                    "isStage": True,
                    "name": "Stage",
                    "variables": {},
                    "lists": {},
                    "broadcasts": {},
                    "blocks": {},
                    "comments": {},
                    "currentCostume": 0,
                    "costumes": [
                        {
                            "name": "backdrop1",
                            "bitmapResolution": 1,
                            "dataFormat": "svg",
                            "assetId": "cd21514d0531fdffb22204e0ec5ed84a",
                            "md5ext": "cd21514d0531fdffb22204e0ec5ed84a.svg",
                            "rotationCenterX": 0,
                            "rotationCenterY": 0,
                        }
                    ],
                    "sounds": [],
                    "volume": 100,
                    "layerOrder": 0,
                    "tempo": 60,
                    "videoTransparency": 50,
                    "videoState": "on",
                    "textToSpeechLanguage": None,
                }
            ],
            "monitors": [],
            "extensions": [],
        "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": "limx-scratch-bridge"},
        }
        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360"></svg>'
        with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("project.json", json.dumps(project, ensure_ascii=False))
            zf.writestr("cd21514d0531fdffb22204e0ec5ed84a.svg", svg)
        return dest

    def list_projects(self) -> List[Dict[str, Any]]:
        result = []
        d = self.project_dir
        for fname in sorted(os.listdir(d)):
            if fname.endswith(".sb3"):
                fpath = os.path.join(d, fname)
                result.append({
                    "name": fname,
                    "size": os.path.getsize(fpath),
                    "modified": os.path.getmtime(fpath),
                })
        return result

    def delete_project(self, name: str) -> bool:
        name = os.path.basename(name)
        fpath = os.path.join(self.project_dir, name)
        if os.path.isfile(fpath) and fpath.endswith(".sb3"):
            os.remove(fpath)
            return True
        return False

    def rename_project(self, old_name: str, new_name: str) -> str:
        old_name = os.path.basename(old_name)
        new_name = os.path.basename(new_name)
        if not old_name or not new_name:
            raise ValueError("old_name and new_name are required")
        if not old_name.endswith(".sb3"):
            old_name += ".sb3"
        if not new_name.endswith(".sb3"):
            new_name += ".sb3"
        src = os.path.join(self.project_dir, old_name)
        dest = os.path.join(self.project_dir, new_name)
        if not os.path.isfile(src):
            raise FileNotFoundError(f"project not found: {old_name}")
        if os.path.exists(dest):
            raise FileExistsError(f'project already exists: {new_name}')
        os.rename(src, dest)
        if self._project_name == old_name:
            self._project_name = new_name
        return new_name

    def start(self, project_path: str) -> Dict[str, Any]:
        with self._lock:
            if self._process and self._process.poll() is None:
                return {"result": "fail", "message": "runner already active, stop first"}
            bridge_url = f"http://127.0.0.1:{self._config.listen_port}"
            env = os.environ.copy()
            env["LIMX_BRIDGE_URL"] = bridge_url
            if self._config.scratch_app_dir:
                env["LIMX_SCRATCH_APP_DIR"] = self._config.scratch_app_dir
            self._process = subprocess.Popen(
                [self._config.node, RUNNER_SCRIPT, project_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self._project_name = os.path.basename(project_path)
            self._started_at = time.time()
            self._events = []

            threading.Thread(target=self._read_stdout, daemon=True).start()
            threading.Thread(target=self._read_stderr, daemon=True).start()

            return {"result": "success", "project": self._project_name, "pid": self._process.pid}

    def stop(self) -> Dict[str, Any]:
        with self._lock:
            if not self._process or self._process.poll() is not None:
                return {"result": "success", "message": "not running"}
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=3)
            return {"result": "success", "message": "stopped"}

    def status(self) -> Dict[str, Any]:
        with self._lock:
            if not self._process:
                return {"state": "idle"}
            rc = self._process.poll()
            if rc is not None:
                return {"state": "exited", "exit_code": rc, "project": self._project_name}
            elapsed = time.time() - self._started_at
            return {
                "state": "running",
                "project": self._project_name,
                "pid": self._process.pid,
                "elapsed_seconds": round(elapsed, 1),
            }

    def _read_stdout(self) -> None:
        try:
            for line in self._process.stdout:
                text = line.decode("utf-8", errors="replace").strip()
                if text:
                    try:
                        evt = json.loads(text)
                        self._events.append(evt)
                    except json.JSONDecodeError:
                        pass
                    print(f"[runner:out] {text}", file=sys.stderr)
        except Exception:
            pass

    def _read_stderr(self) -> None:
        try:
            for line in self._process.stderr:
                text = line.decode("utf-8", errors="replace").strip()
                if text:
                    print(f"[runner:err] {text}", file=sys.stderr)
        except Exception:
            pass


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="limx-scratch-bridge",
        description="Local HTTP bridge that lets Scratch blocks call limx-cli.",
    )
    parser.add_argument("--listen-host", default=DEFAULT_LISTEN_HOST)
    parser.add_argument("--listen-port", type=int, default=DEFAULT_LISTEN_PORT)
    parser.add_argument("--robot-host", default=DEFAULT_ROBOT_HOST)
    parser.add_argument("--robot-port", type=int, default=DEFAULT_ROBOT_PORT)
    parser.add_argument("--command-timeout", type=float, default=DEFAULT_COMMAND_TIMEOUT)
    parser.add_argument(
        "--menu-timeout",
        type=float,
        default=DEFAULT_MENU_TIMEOUT,
        help="Seconds to wait for startup action/dance menu preload in the background.",
    )
    parser.add_argument("--python", default=os.environ.get("LIMX_SCRATCH_PYTHON", DEFAULT_PYTHON))
    parser.add_argument(
        "--node",
        default=default_node_path(),
        help="Node.js executable for headless Scratch project runner.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Add --dry-run to all limx-cli commands")
    parser.add_argument(
        "--static-dir",
        default=DEFAULT_STATIC_DIR,
        help="Directory with Scratch editor static build. Set to empty to disable.",
    )
    parser.add_argument(
        "--project-dir",
        default=DEFAULT_PROJECT_DIR,
        help="Directory to store uploaded .sb3 projects for background execution.",
    )
    parser.add_argument(
        "--scratch-app-dir",
        default=os.environ.get("LIMX_SCRATCH_APP_DIR", default_scratch_app_dir()),
        help="scratch-app source directory used by the headless background runner.",
    )
    args = parser.parse_args(argv)

    static_dir = args.static_dir if args.static_dir and os.path.isdir(args.static_dir) else None
    config = BridgeConfig(
        robot_host=args.robot_host,
        robot_port=args.robot_port,
        command_timeout=args.command_timeout,
        dry_run=args.dry_run,
        python=args.python,
        node=args.node,
        menu_timeout=args.menu_timeout,
        static_dir=static_dir,
    )
    config.project_dir = args.project_dir
    config.scratch_app_dir = args.scratch_app_dir
    config.listen_port = args.listen_port
    config.runner = ProjectRunner(config)
    handler = make_handler(config)
    server = ThreadingHTTPServer((args.listen_host, args.listen_port), handler)
    host_display = args.listen_host if args.listen_host != "0.0.0.0" else "127.0.0.1"
    print(
        f"LimX Scratch bridge listening on http://{host_display}:{args.listen_port}",
        file=sys.stderr,
    )
    if static_dir:
        print(
            f"Scratch editor: http://{host_display}:{args.listen_port}/editor.html",
            file=sys.stderr,
        )
    else:
        print(
            f"Load Scratch extension: http://{host_display}:{args.listen_port}/extension.js",
            file=sys.stderr,
        )
    print(
        f"Scratch menus start with defaults: actions={len(config.action_menu)}, dances={len(config.dance_menu)}, emojis={len(config.emoji_menu)}",
        file=sys.stderr,
    )
    start_menu_preload(config)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 130
    finally:
        server.server_close()
    return 0


def render_extension_js(config: BridgeConfig, lang: str = "") -> str:
    ensure_robot_info(config)
    return (
        SCRATCH_EXTENSION_JS.replace("__LIMX_ACTION_MENU__", json.dumps(config.action_menu, ensure_ascii=False))
        .replace("__LIMX_DANCE_MENU__", json.dumps(config.dance_menu, ensure_ascii=False))
        .replace("__LIMX_EMOJI_MENU__", json.dumps(config.emoji_menu, ensure_ascii=False))
        .replace("__LIMX_ROBOT_NAME__", json.dumps(config.robot_name, ensure_ascii=False))
        .replace(
            "__LIMX_SUPPORTS_POSTURE_BLOCKS__",
            json.dumps(robot_supports_posture_blocks(config.robot_accid), ensure_ascii=False),
        )
        .replace(
            "__LIMX_SUPPORTS_EMOJI_BLOCKS__",
            json.dumps(robot_supports_emoji_blocks(config.robot_accid), ensure_ascii=False),
        )
        .replace("__LIMX_LANG__", json.dumps(normalize_bridge_lang(lang), ensure_ascii=False))
    )


def start_menu_preload(config: BridgeConfig) -> threading.Thread:
    thread = threading.Thread(
        target=refresh_startup_menus,
        args=(config,),
        name="limx-scratch-menu-preload",
        daemon=True,
    )
    thread.start()
    return thread


def refresh_startup_menus(config: BridgeConfig) -> None:
    ensure_robot_info(config)
    menu_config = BridgeConfig(
        robot_host=config.robot_host,
        robot_port=config.robot_port,
        command_timeout=config.menu_timeout,
        dry_run=config.dry_run,
        python=config.python,
        node=config.node,
        menu_timeout=config.menu_timeout,
    )
    try:
        action_data = run_bridge_command("action_list", {}, menu_config)
        action_menu = extract_action_menu(action_data)
        if action_menu:
            config.action_menu = action_menu
    except Exception as exc:
        print(f"[scratch-bridge] failed to preload action list: {exc}", file=sys.stderr)

    try:
        dance_data = run_bridge_command("dance_list", {}, menu_config)
        dance_menu = extract_dance_menu(dance_data)
        if dance_menu:
            config.dance_menu = dance_menu
    except Exception as exc:
        print(f"[scratch-bridge] failed to preload dance list: {exc}", file=sys.stderr)

    if robot_supports_emoji_blocks(config.robot_accid):
        try:
            emoji_data = run_bridge_command("emoji_list", {}, menu_config)
            emoji_menu = extract_emoji_menu(emoji_data)
            if emoji_menu:
                config.emoji_menu = emoji_menu
        except Exception as exc:
            print(f"[scratch-bridge] failed to preload emoji list: {exc}", file=sys.stderr)

    print(
        f"[scratch-bridge] Scratch menus loaded: actions={len(config.action_menu)}, dances={len(config.dance_menu)}, emojis={len(config.emoji_menu)}",
        file=sys.stderr,
    )


def robot_name_from_accid(accid: str) -> str:
    value = str(accid or "").strip().upper()
    if value.startswith("HU_D"):
        return "Oli"
    if value.startswith("HU_L"):
        return "Luna"
    return "LimX"


def robot_project_name(config: BridgeConfig) -> str:
    if config.robot_accid:
        name = robot_name_from_accid(config.robot_accid)
    else:
        name = config.robot_name or ""
    return name if name in ("Oli", "Luna") else ""


def robot_project_dir(config: BridgeConfig) -> str:
    ensure_robot_info(config)
    base_dir = config.project_dir or DEFAULT_PROJECT_DIR
    robot_name = os.path.basename(robot_project_name(config))
    if not robot_name:
        return base_dir
    return os.path.join(base_dir, robot_name)


def robot_supports_posture_blocks(accid: str) -> bool:
    return not str(accid or "").strip().upper().startswith("HU_L")


def robot_supports_emoji_blocks(accid: str) -> bool:
    return str(accid or "").strip().upper().startswith("HU_L")


def ensure_robot_info(config: BridgeConfig) -> None:
    if config.robot_accid or config.dry_run:
        return
    try:
        client = SignalingClient(
            config.robot_host,
            config.robot_port,
            connect_timeout=config.menu_timeout,
            default_timeout=config.menu_timeout,
        )
        try:
            client.connect()
            config.robot_accid = client.accid or ""
            config.robot_name = robot_name_from_accid(config.robot_accid)
        finally:
            client.close()
    except Exception as exc:
        print(f"[scratch-bridge] failed to detect robot accid: {exc}", file=sys.stderr)


def robot_info(config: BridgeConfig) -> Dict[str, str]:
    ensure_robot_info(config)
    return {
        "accid": config.robot_accid,
        "robot_name": config.robot_name,
        "robot_type": config.robot_name,
    }


def extract_action_menu(data: Dict[str, Any]) -> List[Dict[str, str]]:
    motions = data.get("motion_list")
    if not isinstance(motions, list):
        return []
    items = []
    seen = set()
    for motion in motions:
        if not isinstance(motion, dict):
            continue
        value = motion.get("motion_name_en")
        item = make_menu_item(value, motion, ["motion_name_cn", "name_cn", "chinese_name"], ["motion_name_en"])
        if item and item["value"] not in seen:
            seen.add(item["value"])
            items.append(item)
    return items


def extract_dance_menu(data: Dict[str, Any]) -> List[Dict[str, str]]:
    dances = data.get("dances")
    if not isinstance(dances, list):
        return []
    items = []
    seen = set()
    for dance in dances:
        if not isinstance(dance, dict):
            continue
        value = dance.get("rc_mapping")
        item = make_menu_item(value, dance, ["name_cn", "dance_name_cn", "chinese_name", "name"], ["english_name", "name_en", "dance_name_en", "name"])
        if item and item["value"] not in seen:
            seen.add(item["value"])
            items.append(item)
    return items


def extract_emoji_menu(data: Dict[str, Any]) -> List[Dict[str, str]]:
    emojis = data.get("emoji_list")
    if not isinstance(emojis, list):
        return []
    items = []
    seen = set()
    for emoji in emojis:
        if emoji is None:
            continue
        value = str(emoji).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        items.append({"value": value, "zh": value, "en": value})
    return items


def make_menu_item(value: Any, data: Dict[str, Any], zh_keys: List[str], en_keys: List[str]) -> Optional[Dict[str, str]]:
    if value is None:
        return None
    api_value = str(value).strip()
    if not api_value:
        return None
    zh = first_non_empty(data, zh_keys) or api_value
    en = first_non_empty(data, en_keys) or api_value
    return {"value": api_value, "zh": zh, "en": en}


def first_non_empty(data: Dict[str, Any], keys: List[str]) -> str:
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def unique_menu_values(values) -> List[str]:
    items = []
    seen = set()
    for value in values:
        if value is None:
            continue
        item = str(value).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        items.append(item)
    return items


def normalize_bridge_lang(value: str) -> str:
    text = str(value or "").strip().lower().replace("_", "-")
    if text.startswith("zh") or text == "chinese":
        return "zh-cn"
    if text.startswith("en") or text == "english":
        return "en"
    return ""


def make_handler(config: BridgeConfig):
    class ScratchBridgeHandler(BaseHTTPRequestHandler):
        server_version = "LimXScratchBridge/0.1"

        def do_OPTIONS(self) -> None:
            self.send_empty(204)

        def lang_from_request(self) -> str:
            query = parse_qs(urlparse(self.path).query)
            for key in ("language", "lang", "locale"):
                for value in query.get(key, []):
                    lang = normalize_bridge_lang(value)
                    if lang:
                        config.ui_lang = lang
                        return lang

            cookie = self.headers.get("Cookie", "")
            for part in cookie.split(";"):
                part = part.strip()
                if part.startswith("limx_lang="):
                    lang = normalize_bridge_lang(part.split("=", 1)[1])
                    if lang:
                        config.ui_lang = lang
                        return lang

            referer = self.headers.get("Referer", "")
            if referer:
                ref_query = parse_qs(urlparse(referer).query)
                for key in ("language", "lang", "locale"):
                    for value in ref_query.get(key, []):
                        lang = normalize_bridge_lang(value)
                        if lang:
                            config.ui_lang = lang
                            return lang
            return config.ui_lang

        def remember_ui_lang(self) -> None:
            query = parse_qs(urlparse(self.path).query)
            for key in ("language", "lang", "locale"):
                for value in query.get(key, []):
                    lang = normalize_bridge_lang(value)
                    if lang:
                        config.ui_lang = lang
                        return
            cookie = self.headers.get("Cookie", "")
            for part in cookie.split(";"):
                part = part.strip()
                if part.startswith("limx_lang="):
                    lang = normalize_bridge_lang(part.split("=", 1)[1])
                    if lang:
                        config.ui_lang = lang
                        return

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/health":
                self.send_json({"result": "success", "service": "limx-scratch-bridge"})
                return
            if path == "/robot-info":
                self.send_json(robot_info(config))
                return
            if path == "/extension.js":
                lang = self.lang_from_request()
                self.send_text(render_extension_js(config, lang), "application/javascript")
                return
            if path == "/project/status":
                self.send_json(config.runner.status())
                return
            if path == "/project/stop-now":
                self.send_json(stop_project_execution(config))
                return
            if path == "/project/list":
                self.send_json({"result": "success", "projects": config.runner.list_projects()})
                return
            if path == "/project/download":
                qs = parse_qs(urlparse(self.path).query)
                name = os.path.basename(qs.get("name", [""])[0])
                if not name:
                    self.send_json({"result": "fail", "message": "name required"}, 400)
                    return
                fpath = os.path.join(config.runner.project_dir, name)
                if not os.path.isfile(fpath):
                    self.send_json({"result": "fail", "message": "not found"}, 404)
                    return
                try:
                    with open(fpath, "rb") as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Length", str(len(data)))
                    fallback_name = "".join(ch if ord(ch) < 128 and ch not in '"\\' else "_" for ch in name)
                    if not fallback_name or fallback_name == ".sb3":
                        fallback_name = "project.sb3"
                    encoded_name = quote(name.encode("utf-8"))
                    self.send_header(
                        "Content-Disposition",
                        f"attachment; filename=\"{fallback_name}\"; filename*=UTF-8''{encoded_name}",
                    )
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(data)
                except Exception as exc:
                    self.send_json({"result": "fail", "message": str(exc)}, 500)
                return
            if path == "/" and config.static_dir:
                self.send_redirect("/editor.html")
                return
            if config.static_dir:
                self.remember_ui_lang()
                served = self.serve_static(path)
                if served:
                    return
            if path == "/favicon.ico":
                self.send_empty(204)
                return
            self.send_json({"result": "fail_not_found", "path": path}, 404)

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if path == "/run":
                try:
                    payload = self.read_json()
                    command = str(payload.get("command", ""))
                    args = payload.get("args", {})
                    if not isinstance(args, dict):
                        raise ValueError("args must be an object")
                    result = run_bridge_command(command, args, config)
                    status = 200 if result.get("result") != "fail_bridge_error" else 400
                    self.send_json(result, status)
                except Exception as exc:
                    self.send_json({"result": "fail_bridge_error", "message": str(exc)}, 400)
                return

            if path == "/project/upload":
                try:
                    content_length = int(self.headers.get("Content-Length", "0"))
                    data = self.rfile.read(content_length)
                    qs = parse_qs(urlparse(self.path).query)
                    name = qs.get("name", ["project"])[0]
                    dest = config.runner.save_project(name, data)
                    self.send_json({"result": "success", "path": dest, "size": len(data)})
                except Exception as exc:
                    self.send_json({"result": "fail", "message": str(exc)}, 400)
                return

            if path == "/project/save":
                try:
                    content_length = int(self.headers.get("Content-Length", "0"))
                    data = self.rfile.read(content_length)
                    qs = parse_qs(urlparse(self.path).query)
                    name = qs.get("name", [""])[0]
                    dest = config.runner.overwrite_project(name, data)
                    self.send_json({"result": "success", "path": dest, "size": len(data)})
                except Exception as exc:
                    self.send_json({"result": "fail", "message": str(exc)}, 400)
                return

            if path == "/project/create_empty":
                try:
                    payload = self.read_json()
                    name = str(payload.get("name", ""))
                    dest = config.runner.create_empty_project(name)
                    self.send_json({"result": "success", "name": os.path.basename(dest), "path": dest})
                except Exception as exc:
                    self.send_json({"result": "fail", "message": str(exc)}, 400)
                return

            if path == "/project/start":
                try:
                    payload = self.read_json()
                    name = os.path.basename(str(payload.get("name", "")))
                    if not name:
                        raise ValueError("name is required")
                    if not name.endswith(".sb3"):
                        name += ".sb3"
                    project_path = os.path.join(config.runner.project_dir, name)
                    if not os.path.isfile(project_path):
                        self.send_json({"result": "fail", "message": f"project not found: {name}"}, 404)
                        return
                    stop_modes_result = stop_action_dance_modes(config)
                    result = config.runner.start(project_path)
                    result["stop_modes"] = stop_modes_result
                    self.send_json(result)
                except Exception as exc:
                    self.send_json({"result": "fail", "message": str(exc)}, 400)
                return

            if path == "/project/stop":
                self.send_json(stop_project_execution(config))
                return

            if path == "/project/stop-modes":
                self.send_json(stop_action_dance_modes(config))
                return

            if path == "/project/delete":
                try:
                    payload = self.read_json()
                    name = os.path.basename(str(payload.get("name", "")))
                    status = config.runner.status()
                    running_project = os.path.basename(str(status.get("project", "")))
                    if status.get("state") == "running" and running_project == name:
                        self.send_json({"result": "fail", "message": "running project cannot be deleted"}, 409)
                        return
                    if config.runner.delete_project(name):
                        self.send_json({"result": "success"})
                    else:
                        self.send_json({"result": "fail", "message": "not found"}, 404)
                except Exception as exc:
                    self.send_json({"result": "fail", "message": str(exc)}, 400)
                return

            if path == "/project/rename":
                try:
                    payload = self.read_json()
                    old_name = str(payload.get("old_name", ""))
                    new_name = str(payload.get("new_name", ""))
                    renamed = config.runner.rename_project(old_name, new_name)
                    self.send_json({"result": "success", "name": renamed})
                except Exception as exc:
                    self.send_json({"result": "fail", "message": str(exc)}, 400)
                return

            self.send_json({"result": "fail_not_found", "path": path}, 404)

        def read_json(self) -> Dict[str, Any]:
            content_length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(content_length).decode("utf-8")
            if not body:
                return {}
            value = json.loads(body)
            if not isinstance(value, dict):
                raise ValueError("request body must be a JSON object")
            return value

        def send_empty(self, status: int) -> None:
            self.send_response(status)
            self.send_cors_headers()
            self.end_headers()

        def send_text(self, text: str, content_type: str, status: int = 200) -> None:
            body = text.encode("utf-8")
            self.send_response(status)
            self.send_cors_headers()
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.write_body(body)

        def send_json(self, data: Dict[str, Any], status: int = 200) -> None:
            body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.write_body(body)

        def send_redirect(self, location: str) -> None:
            self.send_response(302)
            self.send_header("Location", location)
            self.end_headers()

        def serve_static(self, url_path: str) -> bool:
            safe = os.path.normpath(url_path.lstrip("/"))
            if safe.startswith(".."):
                return False
            full = os.path.join(config.static_dir, safe)
            if not os.path.isfile(full):
                return False
            ctype, _ = mimetypes.guess_type(full)
            if ctype is None:
                ctype = "application/octet-stream"
            try:
                with open(full, "rb") as f:
                    body = f.read()
            except OSError:
                return False
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            if ctype == "text/html" or safe == "static/bootstrap.js":
                self.send_header("Cache-Control", "no-store, max-age=0")
            else:
                self.send_header("Cache-Control", "public, max-age=3600")
            self.end_headers()
            self.write_body(body)
            return True

        def send_cors_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def write_body(self, body: bytes) -> None:
            try:
                self.wfile.write(body)
            except BrokenPipeError:
                pass

        def log_message(self, format: str, *args: Any) -> None:
            print(f"[scratch-bridge] {self.address_string()} - {format % args}", file=sys.stderr)

    return ScratchBridgeHandler


def run_bridge_command(command: str, args: Dict[str, Any], config: BridgeConfig) -> Dict[str, Any]:
    cli_args = build_cli_args(command, args, config)
    with config.command_lock:
        process = subprocess.Popen(
            [config.python, "-m", "agent_harness.cli", *cli_args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        with config.active_command_lock:
            config.active_command = process
        try:
            stdout, stderr = process.communicate(timeout=config.command_timeout)
        except subprocess.TimeoutExpired:
            terminate_process(process)
            stdout, stderr = process.communicate()
        finally:
            with config.active_command_lock:
                if config.active_command is process:
                    config.active_command = None
        completed = subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)
    data = parse_cli_json(completed.stdout)
    data.setdefault("result", "success" if completed.returncode == 0 else "fail_cli_command")
    data["ok"] = completed.returncode == 0
    data["returncode"] = completed.returncode
    if completed.stderr.strip():
        data["stderr"] = completed.stderr.strip()
    if command == "work_mode":
        data.update(normalize_work_mode(data))
    return data


def stop_project_execution(config: BridgeConfig) -> Dict[str, Any]:
    command_result = stop_active_command(config)
    modes_result = stop_action_dance_modes(config)
    robot_result = stop_robot_motion(config)
    if config.runner:
        threading.Thread(target=config.runner.stop, daemon=True).start()
        runner_result = {"result": "success", "message": "runner stop requested"}
    else:
        runner_result = {"result": "success", "message": "no runner"}
    return {
        "result": "success",
        "command": command_result,
        "robot_stop": robot_result,
        "stop_modes": modes_result,
        "runner": runner_result,
    }


def stop_active_command(config: BridgeConfig) -> Dict[str, Any]:
    with config.active_command_lock:
        process = config.active_command
    if not process or process.poll() is not None:
        return {"result": "success", "message": "no active command"}
    terminate_process(process)
    with config.active_command_lock:
        if config.active_command is process:
            config.active_command = None
    return {"result": "success", "message": "active command stopped", "returncode": process.returncode}


def terminate_process(process: subprocess.Popen) -> None:
    try:
        process.terminate()
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


def stop_robot_motion(config: BridgeConfig) -> Dict[str, Any]:
    if config.dry_run:
        return {"result": "success", "dry_run": True}
    stop = {"x": 0.0, "y": 0.0, "yaw": 0.0}
    client = SignalingClient(
        config.robot_host,
        config.robot_port,
        connect_timeout=min(config.menu_timeout, 3.0),
        default_timeout=2.0,
    )
    try:
        client.connect()
        results = []
        for _ in range(3):
            results.append(client.request("request_set_walk_vel_sync", stop, 2.0))
            time.sleep(0.05)
        ok = any(bridge_result_is_success(result) for result in results)
        return {"result": "success" if ok else "fail_robot_stop", "requests": results}
    except Exception as exc:
        return {"result": "fail_robot_stop", "message": str(exc)}
    finally:
        client.close()


def stop_action_dance_modes(config: BridgeConfig) -> Dict[str, Any]:
    if config.dry_run:
        return {
            "result": "success",
            "dry_run": True,
            "requests": [
                {"title": "request_set_motion_engine", "data": {"mode": 0}},
                {"title": "request_enter_dance_mode", "data": {"mode": 0}},
            ],
        }
    client = SignalingClient(
        config.robot_host,
        config.robot_port,
        connect_timeout=min(config.menu_timeout, 3.0),
        default_timeout=3.0,
    )
    try:
        client.connect()
        action_result = client.request("request_set_motion_engine", {"mode": 0}, 3.0)
        dance_result = client.request("request_enter_dance_mode", {"mode": 0}, 3.0)
        ok = bridge_result_is_success(action_result) or bridge_result_is_success(dance_result)
        return {
            "result": "success" if ok else "fail_stop_modes",
            "action_exit": action_result,
            "dance_exit": dance_result,
        }
    except Exception as exc:
        return {"result": "fail_stop_modes", "message": str(exc)}
    finally:
        client.close()


def bridge_result_is_success(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    return result.get("result", "success") == "success"


def build_cli_args(command: str, args: Dict[str, Any], config: BridgeConfig) -> List[str]:
    base = [
        "--host",
        config.robot_host,
        "--port",
        str(config.robot_port),
    ]
    if config.dry_run and command not in READ_ONLY_BRIDGE_COMMANDS:
        base.append("--dry-run")

    if command == "lock_info":
        return [*base, "lock", "info"]
    if command == "action_status":
        return [*base, "action", "status"]
    if command == "action_list":
        return [*base, "action", "list"]
    if command == "dance_list":
        return [*base, "dance", "list"]
    if command == "emoji_list":
        return [*base, "emoji", "list"]
    if command == "state":
        return [*base, "state", state_kind(args)]
    if command == "work_mode":
        return [*base, "state", "mode"]
    if command == "action_enter":
        return [*base, "action", "enter"]
    if command == "action_exit":
        return [*base, "action", "exit"]
    if command == "action_stop":
        return [*base, "action", "stop"]
    if command == "dance_mode":
        return [*base, "dance", "enter"]
    if command == "dance_stop":
        return [*base, "dance", "stop"]
    if command == "dance_exit":
        return [*base, "dance", "exit"]
    if command == "walk_mode":
        return [*base, "raw", "request_set_walk_mode", "--data", "{}"]
    if command == "stand_mode":
        return [*base, "raw", "request_standup", "--data", '{"mode": "hanging"}']
    if command == "damped_mode":
        return [*base, "raw", "request_damping", "--data", "{}"]
    if command == "action_run":
        return [
            *base,
            "action",
            "run",
            "--name",
            action_name(args, config),
            "--timeout",
            "120",
        ]
    if command == "dance_run":
        return [*base, "dance", "run", "--rc-mapping", dance_rc_mapping(args, config)]
    if command == "walk":
        return [
            *base,
            "motion",
            "walk",
            "--x",
            str(number_arg(args, "x", 0.0)),
            "--y",
            str(number_arg(args, "y", 0.0)),
            "--yaw",
            str(number_arg(args, "yaw", 0.0)),
            "--duration",
            str(number_arg(args, "duration", 2.0)),
            "--rate-hz",
            str(number_arg(args, "rate_hz", 10.0)),
        ]
    if command == "standup":
        return [*base, "motion", "standup"]
    if command == "sit":
        return [*base, "motion", "sit"]
    if command == "prepare":
        return [*base, "motion", "prepare"]
    if command == "lie_down":
        return [*base, "motion", "lie-down"]
    if command == "zero_torque":
        return [*base, "motion", "zero-torque"]
    if command == "emoji_set":
        return [*base, "emoji", "set", required_string(args, "name")]
    if command == "volume_set":
        return [*base, "audio", "set-volume", str(int(number_arg(args, "volume", 60)))]

    raise ValueError(f"unsupported command: {command}")


def parse_cli_json(stdout: str) -> Dict[str, Any]:
    text = stdout.strip()
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {"stdout": text}
    return value if isinstance(value, dict) else {"stdout": value}


def normalize_work_mode(data: Dict[str, Any]) -> Dict[str, Any]:
    current_state = str(data.get("current_state") or data.get("robot_status") or "").strip()
    if current_state:
        zh = {
            "ZeroTorque": "零力矩",
            "Damped": "阻尼",
            "Damping": "阻尼",
            "ExceptionWithDamped": "阻尼异常",
            "DampedException": "阻尼异常",
            "Menu": "动作库",
            "ActionLibrary": "动作库",
            "GCDance": "跳舞",
            "MotionEdit": "动作执行",
            "Walk": "行走",
            "HumanLikeWalking": "行走",
            "HighkneeWalk": "行走",
            "LieDown": "躺着",
            "NoActionLieDown": "躺着",
            "Sitting": "坐着",
            "SitDown": "坐着",
            "LieSit": "坐着",
            "StandSit": "坐着",
            "Standing": "站立",
            "StandUp": "站立",
            "IkStand": "站立",
            "SitStand": "站立",
            "FromBoxStandUp": "站立",
        }.get(current_state, current_state)
        return {"work_mode": current_state, "work_mode_zh": zh, "message": zh}

    mode = str(data.get("action_library_mode") or "").strip()
    state = str(data.get("action_library_state") or "").strip()
    if mode == "action_library":
        if state == "running":
            return {"work_mode": "action_library_running", "work_mode_zh": "动作/舞蹈执行中", "message": "动作/舞蹈执行中"}
        return {"work_mode": "action_library", "work_mode_zh": "动作库", "message": "动作库"}
    if mode == "remote_control":
        return {"work_mode": "remote_control", "work_mode_zh": "遥控/行走", "message": "遥控/行走"}
    return {"work_mode": "unknown", "work_mode_zh": "未知", "message": "未知"}


def required_string(args: Dict[str, Any], name: str) -> str:
    value = str(args.get(name, "")).strip()
    if not value:
        raise ValueError(f"missing required argument: {name}")
    return value


def normalize_menu_key(value: Any) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("_", "")
        .replace("-", "")
        .replace("/", "")
        .replace(" ", "")
        .replace("（", "(")
        .replace("）", ")")
    )


def resolve_menu_value(value: str, menu: List[Dict[str, str]]) -> str:
    text = str(value or "").strip()
    if not text:
        return text
    aliases: Dict[str, str] = {}
    for item in menu:
        real_value = str(item.get("value") or item.get("en") or "").strip()
        if not real_value:
            continue
        for candidate in item.values():
            candidate_text = str(candidate or "").strip()
            if not candidate_text:
                continue
            aliases[candidate_text] = real_value
            aliases[normalize_menu_key(candidate_text)] = real_value
        aliases[real_value] = real_value
        aliases[normalize_menu_key(real_value)] = real_value
    return aliases.get(text) or aliases.get(normalize_menu_key(text)) or text


def action_name(args: Dict[str, Any], config: BridgeConfig) -> str:
    value = str(args.get("name", "")).strip()
    if value:
        return resolve_menu_value(value, config.action_menu)
    return "wave_greet_bye"


def dance_rc_mapping(args: Dict[str, Any], config: BridgeConfig) -> str:
    value = str(args.get("name") or args.get("rc_mapping") or "").strip()
    if not value:
        raise ValueError("missing required argument: name")
    return resolve_menu_value(value, config.dance_menu)


def number_arg(args: Dict[str, Any], name: str, default: float) -> float:
    value = args.get(name, default)
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc


def state_kind(args: Dict[str, Any]) -> str:
    kind = str(args.get("kind", "joint")).strip()
    if kind not in {"joint", "imu"}:
        raise ValueError("state kind must be one of: joint, imu")
    return kind


if __name__ == "__main__":
    raise SystemExit(main())
