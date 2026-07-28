# Local Run

This is a portable Windows package. You can run it locally without GitHub or cloud deployment.

## How to run

1. Double-click `run.bat`.
2. Wait for the browser to open, or visit `http://127.0.0.1:3000/` manually.
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
- `API/.env` for optional API keys

## Important

- Some AI features need API keys in `API/.env`.
- Local ComfyUI features require a separate ComfyUI instance.
- If they only want to view or edit existing canvases offline, they can do that with the bundled files.
