# Troubleshooting

## Codex usage service is unreachable: SSL UNEXPECTED_EOF_WHILE_READING

If the Codex card shows `offline` / `SSL/network error` while Kimi and DeepSeek work, the problem is isolated to the Codex usage endpoint or the local network path to it.

### Possible causes

1. Proxy not in effect for the Codex endpoint.
2. Company network TLS/SSL interception breaks the TLS handshake.
3. The Codex usage endpoint has changed or is temporarily unavailable.
4. The EXE runtime environment has different proxy/certificate settings than the source environment.
5. Firewall or security software blocks the connection.

### How to investigate

1. Compare source vs EXE:
   ```powershell
   python main.py refresh
   python main.py status
   ```
   If source works but EXE fails, compare proxy/environment/certificate settings between the two runtimes.

2. Check `.env` and `config.yaml`:
   - `config.yaml` controls `provider.timeout_seconds`.
   - `.env` is loaded from the same folder as `main.py` or `CodingPlanWidget.exe`.

3. Check proxy settings:
   - `HTTP_PROXY` / `HTTPS_PROXY` environment variables.
   - System proxy settings.
   - Corporate TLS inspection tools.

4. Retry with the tray or in-window refresh button. Some Codex endpoint failures are transient.

5. If Kimi and DeepSeek refresh successfully, the issue is limited to the Codex usage source (OAuth/local login or custom command). Verify:
   - `codex login` state in `~/.codex/auth.json`.
   - Whether a custom command is configured in `config.yaml` under `codex.custom_command`.

### What the UI shows

- Short status: `offline`.
- Short message: `SSL/network error`, `Network timeout`, or `Network error`.
- If a previous successful value exists, the widget keeps showing the last known `5H` / `WEEK` percentages with status `offline` and the message `Last value shown; refresh failed.`.
- Retained value rows are marked `stale`. A sanitized technical detail may be stored in the cache `debug` field, but it is not shown in the compact UI.

### Do not

- Do not paste `auth.json`, Bearer tokens, or cookies into chat or logs.
- Do not ship a real `.env` inside the release package.
