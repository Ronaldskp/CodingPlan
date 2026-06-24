# CodingPlanWidget

CodingPlanWidget 是一个 Windows 桌面悬浮工具，用于显示 Codex、Kimi Coding Plan
的 5H、weekly 剩余额度，以及 DeepSeek API 余额和今日估算消费。V1.5 新增
Codex/Kimi 额度重置时间显示，V1.4.1 保持 Python + PySide6 以及 provider/core/ui
分层。

## V1.5 Reset Time Display

V1.5 新增 Codex/Kimi 的 5H 额度重置时间解析与显示：

- CLI `status` / `refresh` 输出中，Codex 与 Kimi 的 5H / Week 行末尾显示 `reset <time>`。
- UI 展开卡片中，每行额度右侧显示对应的重置时间；缺失或无法解析时显示 `--`。
- 折叠摘要可选显示第二行重置时间，格式 `R C18:44 K18:44    Fresh`。
- 新增 `ui` 配置项：`show_reset_times`、`reset_display_mode`、`compact_summary_show_reset`。

详细信息见 `docs/ui_notes.md`。

## 日常启动（推荐）

旧版桌面快捷方式可能仍指向 `start_widget_silent.vbs`。V1.4.1 的 EXE 版推荐直接运行：

```text
E:\Ronald\CodingPlanWidget\release\CodingPlanWidget\CodingPlanWidget.exe
```

创建或更新桌面 EXE 快捷方式：

```powershell
cd E:\Ronald\CodingPlanWidget
powershell -ExecutionPolicy Bypass -File .\create_exe_desktop_shortcut.ps1
```

也可以双击：

```text
create_exe_desktop_shortcut.bat
```

脚本会覆盖同名的 `CodingPlanWidget.lnk`，使其指向 release EXE，而不再指向旧 VBS。
源码启动脚本 `start_widget.bat` 和 `start_widget_silent.vbs` 仍保留用于开发调试。

## EXE 快捷方式图标

EXE 桌面快捷方式使用：

```text
release\CodingPlanWidget\assets\coding_plan.ico
```

## EXE 版本（V1.4+）

打包后的 Windows 桌面版本位于：

```text
release\CodingPlanWidget\
```

双击 `CodingPlanWidget.exe` 即可启动悬浮窗，无命令行黑窗口。

### 打包

```powershell
build_exe.bat
```

打包产物：

```text
release\CodingPlanWidget\
├─ CodingPlanWidget.exe
├─ config.yaml
├─ .env.example
├─ README_RELEASE.md
├─ assets\coding_plan.ico
└─ data\
```

### 发布前配置

1. 在 `release\CodingPlanWidget\` 中复制 `.env.example` 为 `.env`。
2. 填写 `KIMI_API_KEY` 和/或 `DEEPSEEK_API_KEY`。
3. 双击 `CodingPlanWidget.exe`。

EXE 版读取的是：

```text
release\CodingPlanWidget\.env
```

不是源码目录中的 `.env`。release 包默认只提供 `.env.example`，`.env` 必须由用户
自行复制创建，并且不得提交或上传。

## 安装与依赖

Python 3.10 或更高版本：

```powershell
python -m venv codingplan
.\codingplan\Scripts\Activate.ps1
pip install -r requirements.txt
pip install kimi-code-usage
```

也可双击 `setup_env.bat`。普通安装使用：

```powershell
pip install -r requirements.txt
```

完全复现当前验证环境使用：

```powershell
pip install -r requirements.lock.txt
```

`requirements.lock.txt` 来自当前虚拟环境的 `pip freeze`，不包含本地绝对路径依赖。

## Kimi 配置

程序支持系统环境变量或项目根目录 `.env`：

```env
KIMI_API_KEY=your_key_here
```

也支持 `KIMI_CODING_API_KEY`。`.env` 已被 `.gitignore` 排除。程序只检查凭据是否
存在，不打印、记录或缓存真实值。

## DeepSeek API Balance

DeepSeek provider 用于显示 API 账户余额和今日估算消费。

在 `.env` 中填写：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

`.env` 已被 `.gitignore` 排除，不要把 `.env` 提交或发给别人。

当前余额来自 DeepSeek 官方余额接口：

```text
GET https://api.deepseek.com/user/balance
```

今日消费是本地估算：

```text
今日消费 ~ 今日初始余额 - 当前余额
```

估算值保存在 `data/deepseek_daily.json` 中。如果当天充值、退款或赠送余额变化，
今日消费可能不准确，UI 会用提示说明。删除 `data/deepseek_daily.json` 可以重置
今日估算起点。

## 命令

```powershell
python main.py doctor
python main.py refresh
python main.py status
python main.py widget
python -m pytest
```

- `doctor`：检查环境，只显示敏感配置的 `set / not set`。
- `refresh`：独立采集 provider 并更新安全缓存。
- `status`：只读本地缓存。
- `widget`：启动悬浮窗、托盘和后台定时刷新。

## 托盘与窗口

- 关闭窗口默认隐藏到系统托盘，程序继续运行。
- 托盘菜单提供 Show、Hide、Refresh、Open Data Folder、Open Project Folder、
  Toggle Always on Top 和 Exit。
- 真正退出需要右键托盘图标后选择 `Exit`。
- 若系统托盘不可用，窗口仍可正常启动和关闭。
- Always on Top 和窗口位置保存在 `data/ui_state.json`。

## 折叠与手动刷新

- 点击标题栏右侧的 `˄` 按钮，或点击标题栏区域（不拖动），可将悬浮窗折叠为一行摘要。
- 折叠后显示示例：
  ```text
  C 98/84  K 70/52  DS 58.23
  R C18:44 K18:44    Fresh
  ```
  第二行仅在 `compact_summary_show_reset: true` 且有有效重置时间时显示。
- 折叠摘要末尾显示 `Fresh`、`Stale` 或 `Expired`；刷新过程中显示 `Refreshing...`。
- Provider 刷新失败但有旧值时，展开卡片保留旧值并在额度行标记 `stale`。
- 再次点击同一区域恢复展开，窗口高度与位置自动恢复。
- 标题栏右侧的 `↻` 按钮可手动触发后台刷新，刷新时按钮变为 `...` 且不会重复启动多个刷新任务。
- 右键菜单和托盘菜单的 Refresh 与界面按钮共用同一套刷新逻辑。
- 折叠状态保存在 `data/ui_state.json` 的 `collapsed` 字段，重启后恢复。

## 缓存新鲜度

窗口底部和 `status` 命令会显示：

```text
Updated 17:56 · Fresh
Updated 17:40 · Stale 16m
Updated 16:50 · Expired 66m
```

- 0～5 分钟：Fresh
- 大于 5 分钟且不超过 15 分钟：Stale
- 大于 15 分钟：Expired
- 时间缺失或无法解析：Unknown

Expired 只改变更新时间提示颜色，不会把 provider 状态改成 error。

## Provider timeout

`config.yaml` 的统一超时配置：

```yaml
provider:
  timeout_seconds: 15
```

它同时约束 Kimi/Codex 子进程以及 Codex 网络请求。超时只影响对应 provider，
不会导致整个程序崩溃。退出时若后台刷新尚未完成，窗口立即隐藏，程序会在受 timeout
约束的刷新结束后退出。

## Reset time display config

`config.yaml` 控制重置时间的显示行为：

```yaml
ui:
  show_reset_times: true
  reset_display_mode: "time"
  compact_summary_show_reset: true
```

- `show_reset_times`：是否在 CLI 与 UI 中显示 Codex/Kimi 的重置时间。
- `reset_display_mode`：目前仅支持 `"time"`（显示具体时间点）；未来可扩展为 `"countdown"`。
- `compact_summary_show_reset`：是否在折叠摘要第二行显示 5H 重置时间。

## 安全说明

- 不要提交 `.env`，也不要把 API Key、token、cookie 或 auth.json 内容写入项目文件。
- `usage.json` 写入前会递归删除敏感字段并脱敏消息。
- doctor/status 不显示真实凭据；Codex auth.json 内容始终隐藏。
- 原始 provider 响应不写日志；Kimi schema 诊断只记录字段名和类型。

## 架构

```text
Codex OAuth / kimi-usage
          -> providers
          -> core normalizer + security + cache freshness
          -> data/usage.json
          -> PySide6 UI / tray / CLI status
```

Provider 细节见 `docs/codex_provider_notes.md`、`docs/kimi_provider_notes.md` 和
`docs/deepseek_provider_notes.md`。
