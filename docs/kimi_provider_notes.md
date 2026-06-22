# Kimi Provider Notes

## 数据来源

Kimi provider 调用已安装的：

```powershell
kimi-usage --json
```

进程继承程序启动时加载的环境变量，包括项目根目录 `.env` 中的 `KIMI_API_KEY` 或 `KIMI_CODING_API_KEY`。程序不读取、打印或缓存 key 的真实值。

## 已验证的 JSON 结构

根对象包含 `kimi` 数组。每个额度项包含：

- `label`
- `used`
- `limit`
- `remaining`
- `percent`
- `reset_at`
- `unit`

## V1.1 固化解析规则

- `label == "Weekly Usage"` 映射到 `weekly`
- `label == "5h Limit"` 映射到 `fiveHour`
- `usedPercent` 优先取 `percent`，缺失时取 `used`
- `remainingPercent` 取 `remaining`
- `resetAt` 取 `reset_at`
- 两个窗口必须都存在，且每个窗口必须具有可解析的 used/percent、remaining 和 reset_at
- 必需字段缺失时返回 `error`，不会抛出到 collector 或 UI
- 两个 Kimi key 均未设置时返回 `unsupported`，并给出配置提示
- `kimi-usage` 不存在时返回 `unsupported`
- 超时返回 `offline`
- CLI 非零退出码或无效 JSON 返回 `error`

由于真实接口以百分比为单位，V1.1 不再依赖 `limit` 做比例换算，避免上游字段语义变化时重复换算。

## 安全与诊断

原始 JSON 不写入日志。若 schema 不匹配，只允许把字段名和数据类型追加到 development log；任何错误消息在显示和缓存前都会经过脱敏。

## V1.2 timeout

`kimi-usage --json` 使用 `config.yaml` 中的 `provider.timeout_seconds`，默认 15 秒。
超时返回 `offline`，不抛出到 collector 或 UI，也不会阻止 Codex 状态继续显示。

## Attribution

- kimi-code-usage: https://github.com/Golden0Voyager/kimi-code-usage
- 上游声明许可证：MIT
