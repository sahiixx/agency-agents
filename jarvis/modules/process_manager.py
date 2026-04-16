"""Process listing and termination module."""

from __future__ import annotations

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None


class ProcessManager:
    """List and kill running processes."""

    def list_processes(self, limit: int = 10) -> list[str]:
        if psutil is None:
            return ["psutil is not available."]
        rows = []
        for proc in psutil.process_iter(attrs=["pid", "name"]):
            rows.append(f"{proc.info['pid']}: {proc.info['name']}")
            if len(rows) >= limit:
                break
        return rows

    def kill(self, pid: int) -> str:
        if psutil is None:
            return "psutil is not available."
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            return f"Sent terminate signal to process {pid}."
        except Exception as exc:
            return f"Could not kill process {pid}: {exc}"
