import subprocess


ALLOWED_APPS = {
    "chrome": "chrome.exe",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
}

_LAUNCHED_PROCESSES = {}


def _normalize_app_name(app_name):
    if not isinstance(app_name, str):
        raise ValueError("app_name must be a string.")

    app_name = app_name.lower().strip()

    if not app_name:
        raise ValueError("app_name cannot be empty.")

    if (
        "\\" in app_name
        or "/" in app_name
        or ":" in app_name
        or app_name.endswith(".exe")
        or app_name.isdigit()
    ):
        raise ValueError(
            "app_name must be an allowlisted application name."
        )

    return app_name


def _live_processes(app_name):
    processes = []

    for process in _LAUNCHED_PROCESSES.get(app_name, []):

        try:
            if process.poll() is None:
                processes.append(process)
        except Exception:
            continue

    _LAUNCHED_PROCESSES[app_name] = processes

    return processes


def list_apps():
    return [
        {
            "name": name,
            "image": image,
        }
        for name, image in sorted(ALLOWED_APPS.items())
    ]


def open_app(app_name: str):
    try:
        app_name = _normalize_app_name(app_name)
    except ValueError as error:
        return {
            "success": False,
            "message": str(error)
        }

    if app_name not in ALLOWED_APPS:
        return {
            "success": False,
            "message": f"I don't have permission to open '{app_name}'."
        }

    try:
        process = subprocess.Popen(ALLOWED_APPS[app_name])
        _LAUNCHED_PROCESSES.setdefault(
            app_name,
            []
        ).append(process)

        return {
            "success": True,
            "message": f"Opened {app_name}."
        }

    except Exception as error:
        return {
            "success": False,
            "message": str(error)
        }


def close_app(app_name: str):
    try:
        app_name = _normalize_app_name(app_name)
    except ValueError as error:
        return {
            "success": False,
            "message": str(error)
        }

    if app_name not in ALLOWED_APPS:
        return {
            "success": False,
            "message": f"I don't have permission to close '{app_name}'."
        }

    processes = _live_processes(app_name)

    if not processes:
        return {
            "success": False,
            "message": (
                f"I can't safely identify a {app_name} "
                "instance launched by Zoey."
            )
        }

    if len(processes) > 1:
        return {
            "success": False,
            "message": (
                f"Multiple {app_name} instances are active; "
                "I won't close one without a safe target."
            )
        }

    process = processes[0]

    try:
        process.terminate()
        process.wait(timeout=5)
        _LAUNCHED_PROCESSES[app_name] = []

        return {
            "success": True,
            "message": f"Closed {app_name}."
        }

    except Exception as error:
        return {
            "success": False,
            "message": str(error)
        }
