# Discord Embed Builder Bot

Bot for interactively configuring and sending embeds via Discord slash commands and a modal form.

## Setup
- Install deps: `python -m pip install -r requirements.txt`
- In the Developer Portal, invite with `applications.commands` (and `bot` if you want guild member presence). Message Content intent is **not** needed.
- Set your token in the shell: `set DISCORD_TOKEN=your-bot-token` (PowerShell) or `export DISCORD_TOKEN=your-bot-token` (macOS/Linux).
- Optional: set `EMBED_CONFIG_FILE` to choose the default JSON for `/embed import` (default `embed_config.json`).
- Run the bot: `python newbot.py` (first launch auto-syncs slash commands; keep it running).

## Slash commands (`/embed ...`)
- `/embed form` - open a modal to set title, description, color, thumbnail, image.
- `/embed add_field name value [inline]` - add a field (inline defaults to false).
- `/embed clear_fields` - remove all fields.
- `/embed footer text` - set footer text.
- `/embed author name [icon_url]` - set author text and optional icon.
- `/embed content <text>` - set message text to send with embeds.
- `/embed preview` - show your current message (content + embeds, ephemeral).
- `/embed send [channel]` - send to the chosen channel or the one you run it in (supports content + multiple embeds from imports).
- `/embed reset` - start a new blank embed.
- `/embed summary` - quick text overview.
- `/embed import [file_name]` - load from a local JSON file (default `embed_config.json` or `EMBED_CONFIG_FILE` env).
- `/embed import_file` - upload a JSON file directly to load it (supports multiple embeds + content).

Tips:
- The bot keeps a separate in-progress embed per user.
- Color accepts hex (`#5865F2`) or Discord color names (`blurple`, `red`, etc.).

## Optional: Local web UI to build an embed
- Install Flask: `python -m pip install flask`
- Run the web UI: `python webapp.py` then open http://127.0.0.1:5000
- Fill message content and one or more embeds, add fields, click Save. It writes `embed_config.json` next to the script.
- You can rename the JSON using the file name box; Save/Download/Upload respect that name.
- In Discord, either run `/embed import [file_name]` (reads the chosen JSON on disk) or `/embed import_file` and attach the downloaded JSON, then `/embed preview` or `/embed send`.

## Self-host quickstart
- Create and activate a venv (recommended).
- Install deps: `python -m pip install -r requirements.txt`
- Export `DISCORD_TOKEN` (and optional `EMBED_CONFIG_FILE`).
- Run `python newbot.py` in one shell, and optionally `python webapp.py` in another for the local builder UI.
- Invite the app with `applications.commands` scope (and `bot` if you want it listed as a member).
- Use the `/embed` commands in a channel or DM; import JSONs from the web UI or the provided `examples/basic_embed.json`.
