# Local Run

This is a portable Windows package. You can run it locally without GitHub or cloud deployment.

## How to run

1. Double-click `run.bat`.
2. Wait for the browser to open. If it does not, visit the exact address printed in the server window; the port may be different if another local project is using the default port.
3. Leave the console window open while you use the app.

## How to share

1. Send `Infinite-Canvas-shareable.zip` to the other person.
2. They extract it anywhere on Windows.
3. They double-click `run.bat` and start using it.

## What is inside

- `python/` bundled interpreter
- `packages/` bundled wheels
- `main.py` app entrypoint
- `static/`, `data/`, `workflows/`, and `assets/`
- `API/.env` is created on first run for optional API keys and is not included in the clean share package.

## Important

- Some AI features need API keys in `API/.env`.
- Local ComfyUI features require a separate ComfyUI instance.
- If they only want to view or edit existing canvases offline, they can do that with the bundled files.

## Updating an existing installation

Use the overwrite update package and run its `update.bat`. Select the old installation folder when asked. The update keeps the recipient's `data`, `assets`, `output`, `API/.env`, and `history.json`, and only replaces program files.
