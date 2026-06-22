# Codex Provider Notes

## 数据来源

默认 `auto` 模式检测本机已有的 Codex ChatGPT OAuth 登录状态，并向 Codex usage endpoint 请求额度。该 endpoint 不是公开、稳定的 API 合约，因此 provider 保持可替换，并保留 `custom_command` fallback。

## 字段识别

响应中的 `rate_limit.primary_window` 与 `rate_limit.secondary_window` 是主要窗口来源：

- `limit_window_seconds <= 86400` 识别为 `fiveHour`；已验证的 5H 值为 18000 秒
- 更长窗口识别为 `weekly`；已验证的 weekly 值为 604800 秒
- 若窗口秒数缺失，按 primary -> fiveHour、secondary -> weekly 顺序 fallback
- `used_percent` 映射为 `usedPercent`
- `remainingPercent` 由 `100 - usedPercent` 计算
- `reset_at` 由 normalizer 转换为本地时区 ISO 时间；无法转换时保留安全字符串

## OAuth 安全边界

- 只检测和使用 `~/.codex/auth.json`，绝不打印或复制文件内容
- access token 与 account id 只在当前请求内存中使用
- token、cookie、Bearer header 不写入 README、docs、日志或 `usage.json`
- doctor 只显示登录文件是否存在，并明确标记内容隐藏
- 401/403 返回“Codex session expired”可读错误，提示重新登录

## 容错

- 登录文件缺失或不是 ChatGPT OAuth：`unsupported`
- 登录状态损坏、字段缺失、响应结构无效：`error`
- 网络不可达或超时：`offline`
- HTTP 认证失效：`error`
- 任一失败都只影响 Codex provider，不影响 Kimi、缓存结构或 UI
- `custom_command` 可用于兼容未来 endpoint/response 变化

## V1.2 timeout

Codex usage 网络请求与 `custom_command` 共用 `config.yaml` 中的
`provider.timeout_seconds`，默认 15 秒。网络超时或不可达返回 `offline`；认证与响应
错误返回脱敏后的 `error`，均不会影响 Kimi 或 UI 主进程。

## custom_command

自定义命令必须输出 JSON。程序支持通用 `fiveHour`、`weekly`、`primary`、`secondary` 及 rate-limit 窗口字段，并对输出消息和缓存做统一脱敏。不要把 token 直接写入命令字符串。

## Attribution

- CC Switch: https://github.com/farion1231/cc-switch
- 上游声明许可证：MIT
