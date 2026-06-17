# LimX CLI

[English](README.md) | 中文

LimX CLI 是运行在 LimX 机器人 WebSocket API 之上的技能控制与编排层。它把机器人复杂的 `request_*` 控制接口封装成两类更容易使用的入口：

- `limx-cli`：面向 AI Agent、自动化脚本和开发者的命令行工具。
- `limx-scratch`：面向 Scratch 图形化编程的本地服务，内置 `LimX Robot` 积木扩展。

它适用于机器人技能检查、演示、教学、自动化脚本和安全的 Agent 辅助操作。它不是机器人控制栈、固件、安全控制器或 signaling 服务本身的替代品；也不提供云账号管理、机群管理、长期生产编排，或超出 signaling 控制锁 API 之外的权限策略执行能力。

当前状态：`0.1.0` 首个开源发布候选版本。CLI 与 Scratch bridge 可用于本地开发和机器人冒烟测试；硬件覆盖当前聚焦 Oli 风格工作流，其它机器人系列和生产部署方式仍需额外验证。

![LimX CLI 软件架构](docs/limx-cli-architecture.svg)

## 1. 特性

- **低门槛使用**：普通用户可以用积木编排机器人行为，开发者和 Agent 可以用 CLI 调用同一套能力。
- **支持 Oli 机器人**：支持状态查询、运动控制、动作、舞蹈、表情和音量等常用技能，其它机器人敬请期待。
- **适合自动化**：CLI 支持 JSON 输出和 dry-run，便于脚本、AI Agent 和测试流程集成。
- **易于部署**：通过 CMake 生成可安装 bundle，安装后可直接使用 `limx-cli` 和 `limx-scratch`。

## 2. 适用对象

- 需要脚本化访问 LimX signaling WebSocket API 的机器人应用开发者。
- 需要 JSON 优先、支持 dry-run 的机器人技能入口的 AI Agent 工具构建者。
- 希望用 Scratch 风格图形化编程编排机器人行为的教学、演示和运营人员。
- 希望改进 CLI、Scratch bridge、文档、打包或测试的贡献者。

## 3. 架构概览

典型链路如下：

1. 用户通过 Scratch 积木、CLI、脚本或 AI Agent 发出机器人技能命令。
2. `limx-scratch` 将图形化积木请求转换成受限的 CLI 调用。
3. `limx-cli` 将高层技能命令转换为 WebSocket API `request_*` 消息。
4. WebSocket API 把请求交给机器人控制系统。

## 4. 前置条件

- Linux x86_64 或 aarch64。
- Python `>= 3.8`。
- CMake `>= 3.16`。
- 可访问 LimX 机器人 WebSocket API，默认地址为 `ws://10.192.1.2:5000`。
- 构建 Scratch 静态站点时，构建机需要 Node.js / npm。
- CMake 部署包会内置指定版本的 Node.js runtime，目标机器运行 `limx-scratch` 时不需要额外安装系统 Node.js。

Ubuntu / Debian 可使用：

```bash
sudo apt update
sudo apt install -y build-essential cmake python3 python3-pip curl
```

使用 nvm 安装 Node.js `22.22.0`：

```bash
# nvm 示例
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
. "$HOME/.nvm/nvm.sh"
nvm install 22.22.0
nvm use 22.22.0
node --version
npm --version
```

Python 依赖：

```bash
python3 -m pip install websocket-client
```

开发测试可额外安装：

```bash
python3 -m pip install pytest
```

## 5. 快速开始

```bash
cd limx-cli
python3 -m pip install websocket-client pytest
python3 -m pytest tests/ -q

# 开发时可不安装直接运行。
python3 -m limx-cli.cli --dry-run state mode

# 构建并安装可复制运行时包。
cmake -S . -B build
cmake --build build
cmake --install build --prefix install
export PATH="$PWD/install/bin:$PATH"

limx-cli --help
limx-cli --host 10.192.1.2 --port 5000 state mode
limx-scratch --listen-host 0.0.0.0 --listen-port 6080
```

执行高风险运动、动作、舞蹈、音频或屏显变更前，请优先使用 `--dry-run`。

## 6. CMake 编译和安装

通过 CMake 编译安装：

```bash
cd limx-cli
cmake -S . -B build
cmake --build build
```

本地测试安装：

```bash
cmake --install build --prefix install
```

安装后：

- `limx-cli` 位于 `install/bin/limx-cli`。
- `limx-scratch` 位于 `install/bin/limx-scratch`。
- 运行时资源位于 `install/bin/limx-cli.bin/`。

使用本地安装目录：

```bash
export PATH="$PWD/install/bin:$PATH"

limx-cli --help
limx-scratch --help
```

系统安装使用 `/usr/local`：

```bash
sudo cmake --install build --prefix /usr/local
```

系统安装后：

- `limx-cli` 位于 `/usr/local/bin/limx-cli`。
- `limx-scratch` 位于 `/usr/local/bin/limx-scratch`。
- 运行时资源位于 `/usr/local/bin/limx-cli.bin/`。

## 7. 使用说明

### 5.1 配置机器人连接

默认连接 `10.192.1.2:5000`。可以用命令行参数覆盖：

```bash
limx-cli --host 10.192.1.2 --port 5000 state mode
```

也可以用环境变量设置默认值：

```bash
export LIMX_ROBOT_HOST=10.192.1.2
export LIMX_ROBOT_PORT=5000
```

### 5.2 CLI

常用命令：

```bash
# 状态查询
limx-cli state mode
limx-cli state joint
limx-cli state imu

# 动作和舞蹈
limx-cli action list
limx-cli action run --name wave_greet_bye --timeout 120
limx-cli dance list
limx-cli dance run --rc-mapping solo_shake --timeout 660

# 运动控制
limx-cli motion standup
limx-cli motion walk --x 0.1 --y 0 --yaw 0 --duration 2
limx-cli motion sit

# 表情和音量
limx-cli emoji list
limx-cli emoji set smile
limx-cli audio set-volume 60
```

`limx-cli` 默认输出 JSON，适合 Agent 或自动化脚本直接解析：

```bash
limx-cli state mode
limx-cli action list
limx-cli --dry-run motion walk --x 0.1 --duration 3
```

`--dry-run` 会展示计划发送的请求，但不会真实控制机器人。

### 5.3 Agent Skill 使用

仓库提供了 `SKILL.md`，用于让 OpenClaw、ZeroClaw、Cursor、Claude Code 等支持 Agent Skill 的工具理解如何安全调用 `limx-cli`。

使用方式：

1. 先按第 4 节安装 `limx-cli`，确认当前 shell 可以直接执行：

```bash
limx-cli --help
```

2. 将 `limx-cli/SKILL.md` 添加到对应工具的 skill 目录，或在工具配置中引用这个文件。

常见放置方式：

| 工具 | 使用方式 |
| --- | --- |
| OpenClaw / ZeroClaw | 将 `SKILL.md` 放入项目或工作区的 skills 目录，并让 Agent 加载该 skill |
| Cursor | 将 `SKILL.md` 放入 Cursor 可发现的 skill 目录，或随项目一起打开后让 Agent 读取 |
| Claude Code | 可复制到 `~/.claude/skills/limx-cli/SKILL.md` |

3. 设置机器人连接环境变量：

```bash
export LIMX_ROBOT_HOST=10.192.1.2
export LIMX_ROBOT_PORT=5000
```

4. 在 Agent 中提出自然语言任务，例如：

```text
查看机器人当前状态
列出可用动作
dry-run 规划一次向前走 0.1m/s 持续 3 秒
```

`SKILL.md` 会指导 Agent 优先使用 JSON 输出、先 dry-run 高风险动作，并通过已有 CLI 子命令调用机器人能力。

### 5.4 Scratch 图形化编程

![Oli Robot Scratch 图形化编程演示](docs/oli-robot-programming.gif)

启动 Scratch 本地服务：

```bash
limx-scratch
```

如果要让同一局域网内的手机、平板或 WebView 访问：

```bash
limx-scratch --listen-host 0.0.0.0 --listen-port 6080
```

然后在浏览器打开 `limx-scratch` 输出的 Scratch 页面地址。

Scratch 页面会出现 `LimX Robot` 分类，常用积木包括：

- 查询机器人状态。
- 进入站立、行走、阻尼、零力矩等模式。
- 执行动作和舞蹈。
- 按 `x/y/yaw` 行走指定时长。
- 设置表情和音量。
- 刷新动作和舞蹈列表。
- 停止机器人。

课堂或演示模式可以使用 dry-run：

```bash
limx-scratch --dry-run
```

## 8. 环境变量

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `LIMX_ROBOT_HOST` | `10.192.1.2` | WebSocket API 主机 |
| `LIMX_ROBOT_PORT` | `5000` | WebSocket API 端口 |
| `LIMX_SCRATCH_LISTEN_HOST` | `0.0.0.0` | Scratch 本地服务监听地址 |
| `LIMX_SCRATCH_LISTEN_PORT` | `6080` | Scratch 本地服务监听端口 |
| `LIMX_SCRATCH_MENU_TIMEOUT` | `5` | 动作/舞蹈菜单预加载超时 |
| `LIMX_SCRATCH_PYTHON` | `python3` | Python 可执行文件 |

## 9. 测试

运行单元测试：

```bash
cd limx-cli
python3 -m pytest tests/ -q
```

如果没有安装 pytest：

```bash
python3 -m unittest discover -s tests -v
```

机器人冒烟测试按风险从低到高执行：

```bash
limx-cli state mode
limx-cli state joint
limx-cli action list
limx-cli dance list
limx-cli --dry-run motion walk --x 0.05 --duration 1
```

## 10. 开源说明

LimX CLI 旨在提供一个更易用、更可组合的机器人技能入口：AI Agent 可以调用，开发者可以脚本化，普通用户可以拖积木。

许可证说明：

- 除第三方组件外，LimX CLI 自研部分采用 Apache License 2.0。
- `scratch-app` 基于 Scratch GUI，保留其原始 GPL-3.0 许可证声明和版权信息。
- 如果发布内容包含 `scratch-app` 或由其构建生成的 Scratch 页面，需要同时遵守 GPL-3.0 的分发要求。
