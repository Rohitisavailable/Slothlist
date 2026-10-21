# Slothlist 🦥

**Let the pile wait a little.** Slothlist turns a messy task dump into one gentle first step, a few small moves, and permission to let the rest wait.

Slothlist sends plans to the [Backboard API](https://docs.backboard.io/api-reference/threads/send-message). The API key is read only by the local Python server and is never sent to the browser. Backboard creates a hosted thread for each plan. Optional Backboard memory is off by default; turn it on in the UI to let Backboard save and retrieve planning preferences across plans.

The default model route is OpenRouter's Qwen2.5 7B Instruct, an open-weight model. This project uses both Backboard's API and open-weight AI. It is not an offline or local-inference app: task text is transmitted to Backboard and routed to the configured model provider.

## Run it with Backboard

1. Create an API key in the Backboard dashboard's **Settings → API Keys** section at [app.backboard.io](https://app.backboard.io). See [Backboard authentication docs](https://docs.backboard.io/authentication).
2. In PowerShell, set the key in the current terminal session: `$env:BACKBOARD_API_KEY="paste-your-key-here"`.
3. From this folder, run `python server.py` and open `http://127.0.0.1:8765`.

Python 3.9+ is required. No Python packages or frontend build step are needed. Do not put the API key in `app.js`, HTML, a committed file, or a chat message. The key is kept in the server process environment; restart the server after changing it.

## Model settings

By default the server sends `llm_provider=openrouter` and `model_name=qwen/qwen-2.5-7b-instruct:free` to Backboard. The OpenRouter listing currently marks that model route as free and rate-limited; pricing and availability can change, and Backboard account terms may also apply. Check both services before relying on the route.

You can override the route before starting the server. For example, in PowerShell:

```powershell
$env:BACKBOARD_LLM_PROVIDER = "openrouter"
$env:BACKBOARD_MODEL_NAME = "qwen/qwen3-4b:free"
python server.py
```

Backboard's message API accepts `llm_provider` and `model_name`, and supports structured JSON output. Check the model's license, price, and provider route before selecting another model.

## How memory works

- Each plan gets a hosted Backboard thread. Slothlist stores the returned assistant ID in this browser's local storage so optional memory can be reused.
- The plan text is sent to Backboard and retained in its hosted thread, even when preference memory is off.
- The optional **Remember planning preferences** checkbox sends `memory: "Auto"`; Backboard can save and recall memories across plans. It is off by default.
- Removing the assistant ID from local storage stops Slothlist from reusing that assistant in this browser. It does not delete old Backboard threads or memories; manage those in your Backboard account.
- The app does not save task text to local files or browser storage. Do not enter sensitive details you do not want transmitted.

## Why open AI here?

The model weights behind the default Qwen route are open-weight, so Slothlist can use a model with inspectable weights rather than being locked to a single model family. Backboard provides the API, hosted threads, and optional memory, while the local server keeps the Backboard key out of the browser. The trade-off is cloud processing: this setup needs internet access, and task text leaves the device.

## How much effort does it save?

Slothlist aims to remove the repeated act of sorting and prioritizing: paste once, get a first step, then decide what fits. No time-saved number has been measured yet; time a few real planning sessions before and after use before making a savings claim.

## Stack

- Python standard-library HTTP server, bound to loopback only
- Backboard message API, threads, and optional assistant memory
- OpenRouter route to Qwen2.5 7B Instruct (default)
- Plain HTML, CSS, and JavaScript

## License

MIT. See [LICENSE](LICENSE).
