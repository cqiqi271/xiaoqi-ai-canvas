import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path


DEFAULT_PORT = 3011
PORT_SCAN_END = 3099
STARTUP_TIMEOUT_SECONDS = 60
REPO_URL = "https://github.com/cqiqi271/xiaoqi-ai-canvas"


def base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


ROOT = base_dir()


def read_text(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except Exception:
        return default


def load_config() -> dict:
    try:
        value = json.loads(read_text(ROOT / "project-config.json", "{}"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def expected_identity() -> tuple[str, str]:
    config = load_config()
    name = str(config.get("project_name") or "小七AI画布").strip()
    repo = str(config.get("repo_url") or REPO_URL).strip().rstrip("/")
    return name, repo


def get_app_info(port: int) -> dict | None:
    try:
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/app-info",
            headers={"Cache-Control": "no-cache"},
        )
        with urllib.request.urlopen(request, timeout=0.8) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def is_this_project(info: dict | None, name: str, repo: str) -> bool:
    if not info:
        return False
    actual_repo = str(info.get("repo_url") or "").strip().rstrip("/")
    actual_name = str(info.get("project_name") or "").strip()
    if actual_repo:
        return actual_repo == repo
    return actual_name == name


def can_bind(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            sock.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False


def choose_port(name: str, repo: str) -> tuple[int | None, bool]:
    for port in range(DEFAULT_PORT, PORT_SCAN_END + 1):
        info = get_app_info(port)
        if is_this_project(info, name, repo):
            return port, True
        if can_bind(port):
            return port, False
    return None, False


def write_error(message: str) -> None:
    try:
        (ROOT / "launcher-error.log").write_text(message + "\n", encoding="utf-8")
    except Exception:
        pass


def show_error(message: str) -> None:
    write_error(message)
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, message, "小七AI画布启动失败", 0x10)
    except Exception:
        print(message)


def start_server(port: int) -> subprocess.Popen:
    python_exe = ROOT / "python" / "python.exe"
    main_file = ROOT / "main.py"
    if not python_exe.exists():
        raise RuntimeError(
            "没有找到内置 Python。\n"
            "请先完整解压压缩包，不要直接在压缩包预览窗口里运行。"
        )
    if not main_file.exists():
        raise RuntimeError("没有找到 main.py。请确认压缩包已经完整解压。")

    log_path = ROOT / "server-launcher.log"
    log_file = log_path.open("a", encoding="utf-8")
    env = os.environ.copy()
    env["APP_PORT"] = str(port)
    env["PYTHONIOENCODING"] = "utf-8"

    creation_flags = 0
    startupinfo = None
    if os.name == "nt":
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0

    try:
        process = subprocess.Popen(
            [str(python_exe), str(main_file)],
            cwd=str(ROOT),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
            startupinfo=startupinfo,
        )
    except Exception:
        log_file.close()
        raise
    log_file.close()
    return process


def wait_until_ready(process: subprocess.Popen, port: int, name: str, repo: str) -> bool:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        if is_this_project(get_app_info(port), name, repo):
            return True
        time.sleep(0.5)
    return False


def main() -> int:
    name, repo = expected_identity()
    port, already_running = choose_port(name, repo)
    if port is None:
        show_error(
            f"没有找到可用端口（{DEFAULT_PORT}-{PORT_SCAN_END}）。\n"
            "请关闭不使用的本地项目后再启动。"
        )
        return 2

    if already_running:
        webbrowser.open(f"http://127.0.0.1:{port}/")
        return 0

    process = None
    try:
        process = start_server(port)
        if not wait_until_ready(process, port, name, repo):
            log_hint = ROOT / "server-launcher.log"
            detail = "服务没有在规定时间内启动。"
            if process.poll() is not None:
                detail = f"服务启动后退出，退出码：{process.returncode}。"
            show_error(
                f"{detail}\n\n"
                f"请查看：{log_hint}\n"
                "也可以双击 run.bat 查看详细启动信息。"
            )
            if process.poll() is None:
                process.terminate()
            return 1
        webbrowser.open(f"http://127.0.0.1:{port}/")
        return 0
    except Exception as exc:
        if process is not None and process.poll() is None:
            process.terminate()
        show_error(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
