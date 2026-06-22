# DeepSeek Provider Notes

## 数据来源

DeepSeek provider 直接调用官方余额接口：

```text
GET https://api.deepseek.com/user/balance
Authorization: Bearer <DEEPSEEK_API_KEY>
```

API Key 来自项目根目录 `.env` 中的 `DEEPSEEK_API_KEY`。程序只检查 key 是否存在，
不打印、记录或缓存 key 的真实值。

## 请求方式

- 使用 Python 标准库 `urllib.request`，不新增 requests/httpx 依赖。
- 请求头：`Authorization: Bearer <key>`、`Accept: application/json`。
- 超时使用 `config.yaml` 中的 `provider.timeout_seconds`，默认 15 秒。
- HTTP 401/403 返回 `error`，网络异常返回 `offline`，解析失败返回 `error`，都不会抛到上层。
- 未配置 `DEEPSEEK_API_KEY` 时返回 `unsupported`，不影响 Codex/Kimi。

## 返回字段

已验证的响应结构示例：

```json
{
  "is_available": true,
  "balance_infos": [
    {
      "currency": "CNY",
      "total_balance": "23.42",
      "granted_balance": "0.00",
      "topped_up_balance": "23.42"
    }
  ]
}
```

字段说明：

- `is_available`：DeepSeek 账户是否可用。
- `balance_infos`：余额列表，可能有多个币种。
- `currency`：币种。
- `total_balance`：当前可用总余额。
- `granted_balance`：赠送余额。
- `topped_up_balance`：充值余额。

余额字段为字符串或数字，解析时安全转 float。

## V1.3 解析规则

- `balance_infos` 缺失或为空时返回 `error`。
- 优先选择 `currency == preferred_currency`（默认 CNY）。
- 没有目标币种时选择第一个 entry。
- `total_balance` 缺失时返回 `error`。
- `granted_balance` / `topped_up_balance` 缺失时补 0.0。
- 解析失败不抛异常，返回带脱敏消息的 `error`。

## 今日消费估算规则

DeepSeek 余额接口只返回当前余额，因此今日消费采用本地估算：

```text
todaySpend = max(0, startBalance - latestBalance)
```

- 每天第一次成功获取余额时，创建 `data/deepseek_daily.json`。
- 同一天的后续刷新保持 `startBalance` 不变，更新 `latestBalance`。
- 如果充值导致余额上涨，`todaySpend` 显示 0，并在 message 中提示估算可能不准。
- 删除 `data/deepseek_daily.json` 可重置今日估算起点。

## CLI 输出格式

使用 ASCII 避免终端乱码：

```text
DeepSeek
  Balance  CNY 23.42
  Today    ~ CNY 0.18
  Status   ok
```

未配置 key 时：

```text
DeepSeek
  Status unsupported
  Message DeepSeek API key is not configured.
```

## UI 显示

DeepSeek 卡片显示：

```text
DEEPSEEK
BAL    CNY 23.42
TODAY  ~CNY 0.18
```

如果未配置 key，卡片显示 `unsupported` 和提示信息；请求失败显示 `error` 和脱敏消息。

## 安全注意事项

- 不要把 `.env` 提交到仓库；`.gitignore` 已排除 `.env`。
- `DEEPSEEK_API_KEY` 不写入 `usage.json`、`deepseek_daily.json`、日志或文档。
- 所有错误消息在返回和缓存前都会经过 `core/security.py` 脱敏。
- 如把 `Authorization` header 内容误写入日志，会被 `redact_text` 替换为 `[REDACTED]`。

## 已知限制

- 今日消费是本地估算，非 DeepSeek 官方账单数据。
- 当天充值、退款、赠送余额变化后，今日消费会偏低或显示为 0。
- 多币种账户中，程序只按 `preferred_currency` 或第一个币种展示一种余额。
- UI 和 CLI 不显示 `granted_balance` / `topped_up_balance` 明细，仅用于内部记录。

## Attribution

- DeepSeek API: https://platform.deepseek.com/
