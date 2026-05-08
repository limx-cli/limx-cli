#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const Module = require('module');
const http = require('http');
const https = require('https');

const SCRATCH_APP = path.resolve(process.env.LIMX_SCRATCH_APP_DIR || path.resolve(__dirname, '../scratch-app'));
const SCRATCH_VM_ENTRY = path.join(SCRATCH_APP, 'node_modules/scratch-vm/src/index.js');
if (!fs.existsSync(SCRATCH_VM_ENTRY)) {
  process.stderr.write(JSON.stringify({
    error: 'scratch-vm not found',
    scratchApp: SCRATCH_APP,
    expected: SCRATCH_VM_ENTRY,
    hint: 'Set LIMX_SCRATCH_APP_DIR to the built scratch-app source directory or deploy scratch-app beside limx_agent_harness.'
  }) + '\n');
  process.exit(1);
}

// ── Stub browser-only modules for headless Node.js ──

const origResolve = Module._resolveFilename;
Module._resolveFilename = function (request, parent, isMain, options) {
  if (request === 'scratch-render-fonts') {
    return path.join(__dirname, '_stub_fonts.js');
  }
  if (request === 'text-encoding') {
    return path.join(__dirname, '_stub_text_encoding.js');
  }
  if (/\.woff2$/.test(request) || /\.png$/.test(request) || /\.svg$/.test(request) ||
      /\.gif$/.test(request) || /\.jpg$/.test(request) || /\.cur$/.test(request) ||
      /\.css$/.test(request) || /\.mp3$/.test(request) || /\.wav$/.test(request)) {
    return path.join(__dirname, '_stub_asset.js');
  }
  return origResolve.call(this, request, parent, isMain, options);
};

// Provide minimal canvas/DOM stubs for headless execution
if (typeof globalThis.document === 'undefined') {
  const stubCtx = () => ({fillRect(){}, drawImage(){}, getImageData: () => ({data: new Uint8Array(0)}), putImageData(){}, clearRect(){}, save(){}, restore(){}, translate(){}, scale(){}, rotate(){}, setTransform(){}, createLinearGradient: () => ({addColorStop(){}}), createRadialGradient: () => ({addColorStop(){}}), measureText: () => ({width: 0}), fillText(){}, strokeText(){}, beginPath(){}, closePath(){}, moveTo(){}, lineTo(){}, arc(){}, arcTo(){}, bezierCurveTo(){}, quadraticCurveTo(){}, rect(){}, fill(){}, stroke(){}, clip(){}, isPointInPath: () => false, createImageData: () => ({data: new Uint8Array(0)}), canvas: {width: 480, height: 360}});
  globalThis.document = {
    createElement(tag) {
      if (tag === 'canvas') return {getContext: stubCtx, width: 480, height: 360, toDataURL: () => '', style: {}};
      if (tag === 'img') return {addEventListener(){}, removeEventListener(){}, set src(_) {}, style: {}};
      return {style: {}, appendChild(){}, setAttribute(){}, getAttribute: () => '', addEventListener(){}, removeEventListener(){}, childNodes: [], children: []};
    },
    createElementNS() { return this.createElement('svg'); },
    getElementById: () => null,
    querySelector: () => null,
    querySelectorAll: () => [],
    createTextNode: () => ({nodeValue: ''}),
    body: {appendChild(){}, insertBefore(){}, style: {}},
    head: {appendChild(){}},
    fonts: {load: () => Promise.resolve()},
    cookie: ''
  };
  globalThis.window = globalThis;
  Object.defineProperty(globalThis, 'navigator', {
    value: {userAgent: 'node', platform: 'linux', language: 'en'},
    writable: true, configurable: true
  });
  globalThis.Image = function () { this.addEventListener = () => {}; this.removeEventListener = () => {}; };
  globalThis.XMLSerializer = function () { this.serializeToString = () => ''; };
  globalThis.DOMParser = function () {
    this.parseFromString = () => {
      const empty = {querySelector: () => null, querySelectorAll: () => [], setAttribute(){}, getAttribute: () => '', getElementsByTagName: () => [], childNodes: [], children: [], nodeName: '', nodeType: 1, textContent: '', innerHTML: '', outerHTML: ''};
      return {querySelector: () => null, querySelectorAll: () => [], documentElement: empty, getElementsByTagName: () => []};
    };
  };
  globalThis.AudioContext = function () { this.createGain = () => ({connect(){}, gain: {value: 1}}); this.destination = {}; this.decodeAudioData = (_, ok) => { if (ok) ok({}); return Promise.resolve({}); }; this.createBufferSource = () => ({connect(){}, start(){}, stop(){}, buffer: null}); this.sampleRate = 48000; };
  globalThis.webkitAudioContext = globalThis.AudioContext;
  if (typeof globalThis.performance === 'undefined') {
    globalThis.performance = {now: () => Date.now()};
  }
  globalThis.requestAnimationFrame = (cb) => setTimeout(cb, 16);
  globalThis.cancelAnimationFrame = (id) => clearTimeout(id);
  globalThis.HTMLCanvasElement = function () {};
  globalThis.HTMLImageElement = function () {};
  globalThis.HTMLVideoElement = function () {};
  globalThis.location = {href: 'http://localhost/', protocol: 'http:', host: 'localhost', hostname: 'localhost', pathname: '/', search: '', hash: ''};
}

const VirtualMachine = require(SCRATCH_VM_ENTRY);

// ── Bridge communication ──

const BRIDGE_URL = process.env.LIMX_BRIDGE_URL || 'http://127.0.0.1:6080';
const PROJECT_FILE = process.argv[2];

if (!PROJECT_FILE) {
  process.stderr.write(JSON.stringify({error: 'usage: scratch_runner.js <project.sb3>'}) + '\n');
  process.exit(1);
}

let commandQueue = Promise.resolve();

function postJson(url, payload) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const body = JSON.stringify(payload);
    const transport = parsed.protocol === 'https:' ? https : http;
    const req = transport.request({
      protocol: parsed.protocol,
      hostname: parsed.hostname,
      port: parsed.port,
      path: parsed.pathname + parsed.search,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body)
      }
    }, res => {
      let text = '';
      res.setEncoding('utf8');
      res.on('data', chunk => {
        text += chunk;
      });
      res.on('end', () => {
        try {
          resolve(JSON.parse(text || '{}'));
        } catch (err) {
          reject(new Error(`invalid JSON response: ${err.message}`));
        }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

async function run(command, args) {
  pendingCommands++;
  try {
    return await postJson(BRIDGE_URL + '/run', {command, args: args || {}});
  } catch (err) {
    process.stderr.write(`[runner] run(${command}) error: ${err.message}\n`);
    return {result: 'error', message: err.message};
  } finally {
    pendingCommands--;
  }
}

function enqueue(command, args) {
  const task = commandQueue.then(() => run(command, args));
  commandQueue = task.catch(() => undefined);
  return task;
}

function menuLabel(item) {
  if (typeof item === 'string') return item;
  return item.zh || item.cn || item.text || item.value;
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

function buildMenu(items, fallback, valuesByLabel) {
  if (!Array.isArray(items) || !items.length) items = fallback.slice();
  return items.map(item => {
    const label = String(menuLabel(item));
    const value = String(menuValue(item));
    addMenuAlias(valuesByLabel, label, value);
    addMenuAlias(valuesByLabel, value, value);
    if (item && typeof item === 'object') {
      Object.keys(item).forEach(key => {
        if (key !== 'value') addMenuAlias(valuesByLabel, item[key], value);
      });
    }
    return label;
  });
}

class LimXRobotExtension {
  getInfo() {
    return {
      id: 'limxRobot',
      name: 'LimX Robot',
      blocks: [
        {opcode: 'state', blockType: 'reporter', text: 'robot state [KIND]',
          arguments: {KIND: {type: 'string', menu: 'stateKinds', defaultValue: 'running'}}},
        {opcode: 'walk', blockType: 'command', text: 'walk x [X] y [Y] yaw [YAW] seconds [DURATION]',
          arguments: {
            X: {type: 'number', defaultValue: 0.2}, Y: {type: 'number', defaultValue: 0},
            YAW: {type: 'number', defaultValue: 0}, DURATION: {type: 'number', defaultValue: 2}
          }},
        {opcode: 'actionRun', blockType: 'command', text: 'action [NAME]',
          arguments: {NAME: {type: 'string', menu: 'actionNames', defaultValue: this.actionMenu[0] || 'wave_greet_bye'}}},
        {opcode: 'danceRun', blockType: 'command', text: 'dance [RC_MAPPING]',
          arguments: {RC_MAPPING: {type: 'string', menu: 'danceMappings', defaultValue: this.danceMenu[0] || 'solo_shake'}}},
        {opcode: 'standup', blockType: 'command', text: 'stand up'},
        {opcode: 'sit', blockType: 'command', text: 'sit'},
        {opcode: 'lieDown', blockType: 'command', text: 'lie down'},
        {opcode: 'enterStandMode', blockType: 'command', text: 'enter standing mode'},
        {opcode: 'enterWalkMode', blockType: 'command', text: 'enter walk mode'},
        {opcode: 'enterActionMode', blockType: 'command', text: 'enter action mode'},
        {opcode: 'enterDanceMode', blockType: 'command', text: 'enter dance mode'},
        {opcode: 'enterDampedMode', blockType: 'command', text: 'enter damped mode'},
        {opcode: 'enterZeroTorqueMode', blockType: 'command', text: 'enter zero torque mode'}
      ],
      menus: {
        stateKinds: {acceptReporters: true, items: ['running', 'joint', 'imu']},
        actionNames: {acceptReporters: false, items: this.actionMenu},
        danceMappings: {acceptReporters: false, items: this.danceMenu}
      }
    };
  }

  constructor() {
    this.last = '';
    this.actionValuesByLabel = {};
    this.danceValuesByLabel = {};
    this.stateValuesByLabel = {running: 'work_mode', joint: 'joint', imu: 'imu'};
    this.actionMenu = buildMenu(
      [{value: 'wave_greet_bye', zh: '挥手告别', en: 'wave_greet_bye'}],
      [], this.actionValuesByLabel
    );
    this.danceMenu = buildMenu(
      [{value: 'solo_shake', zh: '孤身摇', en: 'solo_shake'}],
      [], this.danceValuesByLabel
    );
  }

  async remember(promise) {
    const result = await promise;
    this.last = JSON.stringify(result);
    return this.last;
  }

  state(args) {
    const kind = this.stateValuesByLabel[args.KIND] || args.KIND;
    if (kind === 'work_mode') return this.remember(enqueue('work_mode'));
    return this.remember(enqueue('state', {kind}));
  }

  enterActionMode() { return this.remember(enqueue('action_enter')); }
  enterStandMode() { return this.remember(enqueue('stand_mode')); }
  enterDampedMode() { return this.remember(enqueue('damped_mode')); }
  enterZeroTorqueMode() { return this.remember(enqueue('zero_torque')); }
  enterWalkMode() { return this.remember(enqueue('walk_mode')); }
  enterDanceMode() { return this.remember(enqueue('dance_mode')); }

  actionRun(args) {
    return this.remember(enqueue('action_run', {name: resolveMenuValue(this.actionValuesByLabel, args.NAME)}));
  }

  danceRun(args) {
    return this.remember(enqueue('dance_run', {name: resolveMenuValue(this.danceValuesByLabel, args.RC_MAPPING)}));
  }

  walk(args) {
    return this.remember(enqueue('walk', {x: args.X, y: args.Y, yaw: args.YAW, duration: args.DURATION}));
  }

  standup() { return this.remember(enqueue('standup')); }
  sit() { return this.remember(enqueue('sit')); }
  lieDown() { return this.remember(enqueue('lie_down')); }
}

// ── VM lifecycle ──

let vm = null;
let running = false;
let watchInterval = null;
let pendingCommands = 0;

function status() {
  if (!vm) return {state: 'idle'};
  const threads = vm.runtime.threads;
  let active = 0;
  for (let i = 0; i < threads.length; i++) {
    if (!threads[i].updateMonitor) active++;
  }
  return {state: running ? 'running' : 'stopped', active_threads: active, pending_commands: pendingCommands, project: PROJECT_FILE};
}

async function startProject() {
  const buffer = fs.readFileSync(PROJECT_FILE);

  vm = new VirtualMachine();
  vm.extensionManager.addBuiltinExtension('limxRobot', LimXRobotExtension);

  vm.runtime.on('SAY', (_target, _type, text) => {
    process.stderr.write(`[say] ${text}\n`);
  });

  vm.runtime.on('RUNTIME_STARTED', () => {
    process.stderr.write(`[runner] Runtime started\n`);
  });

  vm.setCompatibilityMode(true);
  vm.clear();
  await vm.loadProject(buffer);
  vm.start();
  vm.greenFlag();

  // Also start top-level blocks that don't have hat blocks (e.g. bare control_forever)
  for (const target of vm.runtime.targets) {
    if (!target.blocks) continue;
    const allBlocks = target.blocks._blocks || {};
    for (const [id, block] of Object.entries(allBlocks)) {
      if (block.topLevel && !block.parent) {
        const opcode = block.opcode || '';
        const isHat = opcode.startsWith('event_') || opcode.startsWith('procedures_definition');
        if (!isHat) {
          process.stderr.write(`[runner] Starting orphan top-level block: ${opcode} (id=${id})\n`);
          vm.runtime.toggleScript(id, {target: target, stackClick: true});
        }
      }
    }
  }

  process.stderr.write(`[runner] Threads: ${vm.runtime.threads.length}\n`);
  running = true;

  process.stderr.write(`[runner] Project started: ${PROJECT_FILE}\n`);
  process.stdout.write(JSON.stringify({event: 'started', project: PROJECT_FILE}) + '\n');

  watchInterval = setInterval(() => {
    const s = status();
    if (s.active_threads === 0 && pendingCommands === 0 && running) {
      process.stderr.write('[runner] All threads finished\n');
      process.stdout.write(JSON.stringify({event: 'finished'}) + '\n');
      stopProject();
      process.exit(0);
    }
  }, 2000);
}

function stopProject() {
  if (!running) return;
  running = false;
  if (watchInterval) {
    clearInterval(watchInterval);
    watchInterval = null;
  }
  if (vm) {
    vm.stopAll();
    vm.quit();
  }
  process.stderr.write('[runner] Project stopped\n');
  process.stdout.write(JSON.stringify({event: 'stopped'}) + '\n');
}

process.on('SIGTERM', () => { stopProject(); process.exit(0); });
process.on('SIGINT', () => { stopProject(); process.exit(0); });

process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => {
  for (const line of chunk.split('\n')) {
    if (!line.trim()) continue;
    try {
      const msg = JSON.parse(line);
      if (msg.action === 'stop') {
        stopProject();
        process.exit(0);
      } else if (msg.action === 'status') {
        process.stdout.write(JSON.stringify({event: 'status', ...status()}) + '\n');
      }
    } catch (_) {}
  }
});

startProject().catch(err => {
  process.stderr.write(`[runner] Error: ${err.message}\n${err.stack}\n`);
  process.stdout.write(JSON.stringify({event: 'error', message: err.message}) + '\n');
  process.exit(1);
});
