# Deployment Guide

This project is a FastAPI web app with WebSocket support, so it should be deployed to a container platform, not a static host.

## Recommended platform

Use Render, Railway, Fly.io, or any container host that supports a long-running Python process.

## What has already been added

- `Dockerfile` for container builds
- `.dockerignore` to keep the image lean
- `render.yaml` for Render-friendly deployment
- `main.py` now reads `PORT` from the environment

## Required environment variables

At minimum, configure:

- `COMFLY_API_KEY` if you use the hosted AI API
- `MODELSCOPE_API_KEY` if you use ModelScope features
- `PORT` is supplied by the platform, but defaults to `3000` locally

Optional but commonly used:

- `COMFLY_BASE_URL`
- `COMFYUI_INSTANCES`
- `CHAT_MODEL`
- `IMAGE_MODEL`
- `SYSTEM_PROMPT`
- `PUBLIC_BASE_URL`
- `PUBLIC_MEDIA_BASE_URL`
- `PUBLIC_MEDIA_TOKEN`

## Render steps

1. Push this folder to GitHub.
2. In Render, create a new `Web Service`.
3. Connect the GitHub repository.
4. Choose `Docker` as the runtime.
5. Leave the start command empty and let the `Dockerfile` handle it.
6. Add any required environment variables in the Render dashboard.
7. Deploy and wait for the service to finish building.

## Important notes

- This app stores data locally under `data/`, `assets/`, and `output/`.
- On free or ephemeral containers, that data may be lost on restart unless you add persistent storage.
- If you need durable user files, connect a persistent disk or external object storage.
- Some features depend on external services and API keys, so they may not work until those are configured.

## Local run

```bash
pip install -r requirements.txt
python main.py
```

Then open `http://127.0.0.1:3000`.
