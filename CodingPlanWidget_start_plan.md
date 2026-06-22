# Coding Plan Widget 开发启动方案

版本：v0.1-start  
目标平台：Windows 10/11  
当前目标：先做电脑屏幕桌面版，暂不做 ESP32 硬件版  
后续扩展：同一份 `usage.json` 可继续喂给 ESP32 / OLED 桌面硬件玩具

---

## 1. 项目目标

做一个 Windows 桌面悬浮小组件，用来显示当前 AI Coding Plan 额度：

- Codex：5-hour window 剩余额度、weekly quota 剩余额度、reset 时间。
- Kimi Code：5-hour window 剩余额度、weekly quota 剩余额度、reset 时间。
- 桌面显示：半透明小窗、可拖动、可置顶、可托盘隐藏、低额度提醒。
- 后续硬件复用：桌面版的数据层必须输出标准 `usage.json`，以后通过串口发给 ESP32 小屏幕。

本项目第一阶段不追求复杂 UI，不做账号切换，不做代理服务，不替代 CC Switch。只做“额度可视化”。

---

## 2. 总体判断

现在先做桌面版是正确路线。原因：

1. 这个项目真正的难点不是显示屏，而是稳定拿到 Codex / Kimi 的额度。
2. 桌面版可以快速验证数据源、刷新机制、代理、登录态、安全脱敏。
3. 后面做硬件时，只需要复用桌面版产生的 `usage.json`，再增加一个 serial sender 即可。
4. 你已经在用 CC Switch，并且 CC Switch 开源，说明 Codex 额度显示存在可参考实现。
5. Kimi 这边已有 `kimi-code-usage`，可以直接通过 `kimi-usage --json` 作为数据源。

---

## 3. 开发原则

### 3.1 数据层优先，UI 第二

不要先做漂亮界面。先保证命令行可以输出真实额度：

```powershell
python main.py doctor
python main.py status
python main.py refresh
```

只有当 `status` 能稳定输出 Codex / Kimi 数据后，再做悬浮窗。

### 3.2 参考开源，但不复制大工程

CC Switch 是大型 Tauri/Rust/TypeScript 应用，功能远超本项目。我们只参考它的“额度查询”和“UI 展示思路”，不要 fork 全部功能。

需要参考：

- Codex quota / balance 查询逻辑。
- Token Plan provider 的 usage progression 思路。
- provider card 里 quota 显示方式。
- tray / lightweight mode 的交互设计。
- 安全脱敏、配置存储、错误提示方式。

暂时不做：

- provider 切换。
- reverse proxy。
- 多模型管理。
- MCP / Skills / Sessions。
- SQLite 大型配置库。
- 云同步。

### 3.3 安全边界

账号凭据永远只保存在电脑端：

- 不打印 API Key。
- 不打印 Codex auth token。
- 不把 token/cookie 写入日志。
- 不把 token/cookie 写入 `usage.json`。
- 日志里只显示“存在 / 不存在”“成功 / 失败”。

### 3.4 Provider 可替换

Codex 的接口可能变化，所以 CodexProvider 必须做成可替换模块：

```text
CodexProvider
├─ CcswitchInspiredCodexProvider
├─ CodexCliStatuslineProvider
├─ CodexWebUsageProvider
└─ MockCodexProvider
```

Kimi 也同理：

```text
KimiProvider
├─ KimiUsageCliProvider
├─ KimiApiProvider
└─ MockKimiProvider
```

---

## 4. 参考项目与要分析的部分

## 4.1 第一优先级：CC Switch

仓库：`https://github.com/farion1231/cc-switch`

CC Switch 是跨平台桌面应用，支持 Claude Code、Codex、Gemini CLI、OpenCode 等，使用 Tauri 2 + Rust + React/TypeScript 构建。它的 v3.13.0 版本说明中明确加入了 quota / balance 可视化，覆盖官方 Claude / Codex / Gemini、Codex OAuth、以及 Kimi / Zhipu GLM / MiniMax 这类 Token Plan provider。

我们重点参考：

### A. Quota & Balance Visibility

分析目标：

- 它如何定义 provider 的 quota / balance 数据结构。
- 它如何把官方 provider 与 Token Plan provider 区分开。
- 它如何显示 remaining / reset / progression。
- 它在失败时如何展示错误。

建议代码搜索关键词：

```text
quota
balance
usage
Token Plan
Codex
Kimi
codex_oauth
remaining
reset
```

### B. Provider Card UI

分析目标：

- quota 信息显示在 provider card 的哪个层级。
- 低额度 warning/danger 怎么标注。
- 是否有 loading / stale / error 状态。

建议搜索路径：

```text
src/components/providers
src/components/usage
src/hooks
src/types
```

### C. Tauri 架构

CC Switch 的架构值得参考，但第一版不直接照搬：

```text
Frontend: React + TypeScript + Vite + TailwindCSS
Backend: Tauri + Rust
Data: SQLite + JSON settings
Pattern: Commands -> Services -> DAO -> Database
```

我们第一版先用 Python 快速验证，后续正式版再考虑 Tauri。

### D. Usage dashboard / session logs

CC Switch 还支持从 Claude / Codex / Gemini session logs 读取 usage，这对我们不是第一优先级。但如果 Codex quota 接口不稳定，可以作为补充参考：用 session logs 辅助显示“今日消耗趋势”。

---

## 4.2 第二优先级：kimi-code-usage

仓库：`https://github.com/Golden0Voyager/kimi-code-usage`

它已经提供：

```bash
pip install kimi-code-usage
kimi-usage
kimi-usage --json
kimi-usage --plain
```

我们重点参考：

### A. CLI JSON 输出

第一版直接调用：

```powershell
kimi-usage --json
```

然后解析 stdout。这样比自己逆 Kimi API 更稳。

### B. 环境变量读取方式

它要求 Kimi Coding Plan API Key 放在：

```text
KIMI_API_KEY
或 KIMI_CODING_API_KEY
或 .env
```

我们的 `doctor` 只检查是否存在，不打印值。

### C. VS Code Extension 状态栏设计

它的 VS Code 扩展状态栏设计可以参考：

```text
Wee:96% 5Ho:99%
```

我们桌面小窗可以更直观：

```text
KIMI
5H    99%
WEEK  96%
```

### D. 阈值设计

参考它的默认思路：

- weekly low threshold：30%
- five-hour low threshold：15%
- refresh interval：5 分钟

---

## 4.3 第三优先级：OpenAI Codex CLI 现状

Codex CLI 已经有 statusline 相关能力，可以配置显示 `five-hour-limit` 和 `weekly-limit`。但是当前公开 CLI 对完整 usage/reset 的输出并不够稳定，所以不能把它作为唯一数据源。

我们对 Codex 的策略：

1. 优先参考 CC Switch 已经实现的 Codex quota/balance 逻辑。
2. 如果短期无法接入完整 Codex quota，则先用 Codex CLI statusline 或 mock provider 保证 UI 和架构跑通。
3. 不把 Codex auth 文件内容打印出来。
4. CodexProvider 返回 `unsupported` 时，UI 仍然正常显示 Kimi 数据。

---

## 4.4 可选参考：CodexBar / AgentLimits

这两个是 macOS 工具，不适合直接复用到 Windows，但可以用于理解 quota 展示和 reset 倒计时：

- CodexBar：显示多个 AI coding provider 的 usage windows / credits / reset countdown。
- AgentLimits：显示 Codex / Claude Code 的 5-hour 和 weekly windows。

只有当 CC Switch 的 Codex 实现不容易拆出来时，才分析这两个项目。

---

## 5. 技术路线选择

## 5.1 MVP 选择：Python + PySide6

第一版推荐 Python + PySide6，而不是一上来 Tauri。

原因：

- Windows 上开发快。
- Python 调命令行工具方便，比如 `kimi-usage --json`。
- 后续串口发 ESP32 也方便。
- 对你当前需求来说，先验证数据比打包精美 App 更重要。

缺点：

- 打包体积大。
- UI 精致度不如 Tauri。
- 后续如果要正式发布，建议重构成 Tauri。

## 5.2 正式版选择：Tauri

当 Python MVP 跑通后，再考虑 Tauri：

- Rust 后端负责数据采集、安全、托盘、开机启动。
- React 前端负责透明悬浮窗 UI。
- 与 CC Switch 技术栈一致，后续更容易参考/迁移。

但 Tauri 放到第二阶段，不是第一阶段。

---

## 6. 项目结构

建议初始目录：

```text
CodingPlanWidget/
├─ README.md
├─ START_PLAN.md
├─ requirements.txt
├─ config.example.yaml
├─ main.py
├─ providers/
│  ├─ __init__.py
│  ├─ base.py
│  ├─ kimi_provider.py
│  ├─ codex_provider.py
│  └─ mock_provider.py
├─ core/
│  ├─ __init__.py
│  ├─ collector.py
│  ├─ normalizer.py
│  ├─ cache.py
│  ├─ security.py
│  └─ paths.py
├─ ui/
│  ├─ __init__.py
│  ├─ widget.py
│  ├─ tray.py
│  └─ theme.py
├─ tests/
│  ├─ test_normalizer.py
│  ├─ test_cache.py
│  └─ test_security.py
└─ data/
   └─ usage.example.json
```

---

## 7. 统一数据结构

无论 Codex / Kimi 怎么获取，最终都统一成以下结构。

```json
{
  "schemaVersion": 1,
  "updatedAt": "2026-06-18T16:42:00+09:00",
  "staleAfterSeconds": 300,
  "providers": {
    "codex": {
      "name": "Codex",
      "status": "ok",
      "plan": "unknown",
      "fiveHour": {
        "remainingPercent": 72,
        "usedPercent": 28,
        "resetAt": "2026-06-18T18:42:00+09:00",
        "resetText": "18:42"
      },
      "weekly": {
        "remainingPercent": 58,
        "usedPercent": 42,
        "resetAt": "2026-06-22T10:00:00+09:00",
        "resetText": "06-22 10:00"
      },
      "message": ""
    },
    "kimi": {
      "name": "Kimi",
      "status": "ok",
      "plan": "Coding Plan",
      "fiveHour": {
        "remainingPercent": 91,
        "usedPercent": 9,
        "resetAt": "2026-06-18T19:10:00+09:00",
        "resetText": "19:10"
      },
      "weekly": {
        "remainingPercent": 76,
        "usedPercent": 24,
        "resetAt": "2026-06-23T10:00:00+09:00",
        "resetText": "06-23 10:00"
      },
      "message": ""
    }
  }
}
```

Provider 状态枚举：

```text
ok            成功
partial       部分字段缺失，但可显示
error         请求失败
unsupported   当前机器/当前 provider 暂不支持
not_configured 未配置 API key 或登录态
stale         数据过期
```

---

## 8. 命令设计

第一版支持这些命令：

```powershell
python main.py doctor
python main.py status
python main.py refresh
python main.py widget
```

后续硬件版增加：

```powershell
python main.py serial --port COM3
```

### 8.1 doctor

检查项目：

- Python 版本。
- PySide6 是否安装。
- `kimi-usage` 是否可执行。
- `KIMI_API_KEY` 或 `KIMI_CODING_API_KEY` 是否存在。
- `codex` CLI 是否可执行。
- Codex auth 文件是否存在。
- `%APPDATA%/CodingPlanWidget` 是否可写。
- 代理配置是否存在。

输出示例：

```text
[OK] Python 3.11
[OK] PySide6 installed
[OK] kimi-usage found
[OK] KIMI_API_KEY exists, value hidden
[OK] codex found
[OK] Codex auth file exists, content hidden
[OK] output dir writable
```

### 8.2 status

读取真实 provider，输出当前状态：

```text
CODING PLAN
Codex  5H 72%  WEEK 58%  status=ok
Kimi   5H 91%  WEEK 76%  status=ok
Updated 16:42
```

### 8.3 refresh

执行一次采集，写入：

```text
%APPDATA%/CodingPlanWidget/usage.json
```

### 8.4 widget

启动桌面悬浮窗。

---

## 9. UI 设计

## 9.1 第一版小窗

尺寸：约 260 × 180，可调整。

```text
┌──────────────────────┐
│  CODING ENERGY  ^_^  │
├──────────────────────┤
│ Codex                │
│ 5H   ███████░  72%   │
│ Week █████░░░  58%   │
├──────────────────────┤
│ Kimi                 │
│ 5H   ████████  91%   │
│ Week ██████░░  76%   │
├──────────────────────┤
│ Updated 16:42        │
└──────────────────────┘
```

## 9.2 交互

- 鼠标拖动移动窗口。
- 右键菜单：刷新 / 置顶 / 隐藏 / 退出。
- 双击展开详情。
- 托盘图标常驻。
- 低额度时 Windows 通知提醒。

## 9.3 状态规则

按所有窗口中最低剩余额度计算总表情：

```text
>= 50%       (^_^)  能量充足
30% ~ 49%   (-_-)  注意节省
15% ~ 29%   (>_<)  偏低
< 15%       (x_x)  危险
error/stale (?_?)  数据异常
```

UI 颜色规则：

```text
>= 50%       normal
30% ~ 49%   warning
15% ~ 29%   danger
< 15%       critical
```

---

## 10. 开发阶段规划

## Phase 0：资料分析与最小验证

目标：确认参考项目里哪些东西能直接借鉴。

任务：

1. Clone CC Switch。
2. 搜索 `quota`、`balance`、`usage`、`Codex`、`Kimi`。
3. 记录 Codex quota 的调用链：UI -> command -> service -> http/auth。
4. Clone kimi-code-usage。
5. 运行 `kimi-usage --json`，保存一份真实输出样例。
6. 运行 `codex`，确认本机登录态、statusline、auth 文件路径。

产出：

```text
docs/research_notes.md
docs/kimi_json_sample.json
docs/codex_findings.md
```

验收：

- 明确 Kimi provider 真实字段。
- 明确 Codex provider 第一版采用哪条路线。

---

## Phase 1：命令行数据层 MVP

目标：不做 UI，先让数据能采集。

任务：

1. 搭建 Python 项目结构。
2. 实现 `BaseProvider`。
3. 实现 `MockProvider`。
4. 实现 `KimiUsageCliProvider`。
5. 实现 `CodexProvider` 的 mock / unsupported / 最小可用版。
6. 实现 `normalizer`。
7. 实现 `cache.py` 写入 usage.json。
8. 实现 `doctor/status/refresh` 命令。

验收：

```powershell
python main.py doctor
python main.py status
python main.py refresh
```

成功生成：

```text
%APPDATA%/CodingPlanWidget/usage.json
```

---

## Phase 2：桌面悬浮窗 MVP

目标：能在屏幕上显示 usage.json。

任务：

1. PySide6 创建无边框半透明窗口。
2. 实现拖动。
3. 实现置顶。
4. 读取 usage.json。
5. 每 60 秒刷新一次 UI。
6. 显示 Codex / Kimi 两张卡片。
7. 显示错误和 stale 状态。

验收：

```powershell
python main.py widget
```

屏幕上出现小窗，能显示 mock / Kimi / Codex 数据。

---

## Phase 3：自动刷新与托盘

目标：从玩具 demo 变成可长期使用的桌面工具。

任务：

1. 后台定时采集，每 3~5 分钟刷新一次。
2. 采集失败时保留旧数据，但标记 stale。
3. 托盘图标。
4. 右键菜单。
5. 开机自启配置。
6. 低额度通知。

验收：

- 程序可后台运行。
- 网络失败不崩溃。
- Kimi/Codex 任何一个失败，另一个仍显示。

---

## Phase 4：Codex 真实数据完善

目标：让 Codex 也稳定显示 5H / WEEK。

任务：

1. 从 CC Switch 中确认 Codex quota 的具体实现。
2. 抽象为本项目的 `CodexProvider`。
3. 添加请求超时、重试、代理配置。
4. 添加 token 脱敏。
5. 添加“接口失败时 fallback 到 statusline / unsupported”的逻辑。

验收：

- 真实显示 Codex 5H / WEEK。
- 不泄露 auth。
- 失败时 UI 不崩溃。

---

## Phase 5：硬件预留，不立即做

目标：为 ESP32 桌面硬件玩具预留接口。

任务：

1. 新增 serial sender。
2. 把 usage.json 压缩成一行 JSON：

```json
{"c5":72,"cw":58,"k5":91,"kw":76,"ts":"16:42","state":"ok"}
```

3. 通过 COM 口发送。

此阶段暂不开发，等桌面版稳定后再做。

---

## 11. 风险与规避

| 风险 | 说明 | 规避 |
|---|---|---|
| Codex 接口变化 | Codex quota 可能不是稳定公开 API | Provider 可替换；失败时显示 unsupported |
| Token 泄露 | Codex auth / Kimi key 很敏感 | 全部脱敏；不写入 usage.json |
| CC Switch 太大 | 直接 fork 会被复杂功能拖垮 | 只参考 quota/balance 相关代码 |
| Kimi JSON 字段变化 | `kimi-usage --json` 输出可能更新 | normalizer 做字段兼容 |
| 公司网络代理 | 请求可能需要 7897 | config 支持 proxyUrl |
| UI 先行导致返工 | 数据没跑通就做 UI 会浪费时间 | Phase 1 只做 CLI 数据层 |
| 刷新过频 | 可能触发风控或浪费资源 | 默认 5 分钟刷新，手动刷新才立即请求 |

---

## 12. 配置文件设计

`config.yaml` 示例：

```yaml
refreshIntervalSeconds: 300
staleAfterSeconds: 600
outputDir: "%APPDATA%/CodingPlanWidget"
proxyUrl: "http://127.0.0.1:7897"

providers:
  codex:
    enabled: true
    mode: "auto"
    timeoutSeconds: 20
  kimi:
    enabled: true
    mode: "kimi-usage-cli"
    timeoutSeconds: 20

ui:
  alwaysOnTop: true
  opacity: 0.88
  width: 260
  height: 180
  startMinimizedToTray: false
  notifyDanger: true
```

---

## 13. 第一轮开发提示词

下面这段可以直接丢给 Codex / Kimi 作为第一轮开发任务。

```text
你是一个资深 Windows 桌面工具开发工程师。请在 D:\CodingPlanWidget 下开发一个 Windows 桌面悬浮小组件，用于显示 Codex 和 Kimi Code 的 Coding Plan 额度。

当前只做第一阶段：命令行数据层 MVP，不做 UI。

目标：
1. Python 项目。
2. 支持命令：
   - python main.py doctor
   - python main.py status
   - python main.py refresh
3. 实现统一 usage.json 数据结构。
4. Kimi 使用 kimi-usage --json 作为第一数据源。
5. Codex 先实现 provider 接口和 mock/unsupported，不要阻塞 Kimi。
6. 所有 token/API key/auth 文件内容必须脱敏，不得打印。
7. 生成清晰 README 和 config.example.yaml。

项目结构：
CodingPlanWidget/
├─ main.py
├─ requirements.txt
├─ config.example.yaml
├─ providers/
│  ├─ base.py
│  ├─ kimi_provider.py
│  ├─ codex_provider.py
│  └─ mock_provider.py
├─ core/
│  ├─ collector.py
│  ├─ normalizer.py
│  ├─ cache.py
│  ├─ security.py
│  └─ paths.py
└─ data/
   └─ usage.example.json

doctor 检查：
1. Python 版本。
2. kimi-usage 是否存在。
3. KIMI_API_KEY 或 KIMI_CODING_API_KEY 是否存在，只显示存在/不存在。
4. codex CLI 是否存在。
5. Codex auth 文件是否存在，只显示存在/不存在。
6. 输出目录是否可写。

usage.json 结构必须包含：
- schemaVersion
- updatedAt
- staleAfterSeconds
- providers.codex
- providers.kimi
- fiveHour.remainingPercent
- weekly.remainingPercent
- status
- message

先生成完整代码，然后告诉我如何运行和下一步怎么接 PySide6 UI。
```

---

## 14. 第一轮验收标准

第一轮完成后，必须能做到：

```powershell
cd D:\CodingPlanWidget
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python main.py doctor
python main.py status
python main.py refresh
```

输出示例：

```text
CODING PLAN
Codex  status=unsupported  message="Codex provider not implemented yet"
Kimi   5H=99%  WEEK=96%  status=ok
Updated 2026-06-18 16:42
```

并生成：

```text
%APPDATA%\CodingPlanWidget\usage.json
```

---

## 15. 参考资料

- CC Switch GitHub：`https://github.com/farion1231/cc-switch`
- CC Switch v3.13.0 Release Notes：`https://github.com/farion1231/cc-switch/blob/main/docs/release-notes/v3.13.0-en.md`
- Kimi Code Usage GitHub：`https://github.com/Golden0Voyager/kimi-code-usage`
- OpenAI Codex usage issue / statusline discussion：`https://github.com/openai/codex/issues/15281`
- CodexBar GitHub：`https://github.com/steipete/codexbar`
- AgentLimits GitHub：`https://github.com/Nihondo/AgentLimits`

---

## 16. 当前最小可行路线总结

最小路线不是直接做硬件，也不是直接做漂亮 UI，而是：

```text
研究 CC Switch / kimi-code-usage
        ↓
做 Python 命令行数据层
        ↓
输出统一 usage.json
        ↓
做 PySide6 桌面悬浮窗
        ↓
完善 Codex 真实 provider
        ↓
稳定后再接 ESP32 硬件
```

当前第一步就是：先用上面的“第一轮开发提示词”让 Codex/Kimi 开始搭项目骨架和 Kimi provider。
