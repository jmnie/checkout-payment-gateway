"""Run both gateways against the unmodified official bank simulator."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    for port in (8080, 2525, 8090, 8091):
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                raise SystemExit(f"Port {port} is in use. Stop its owner before running E2E.")
    java_home = os.environ.get("JAVA_HOME")
    java = str(Path(java_home) / "bin/java") if java_home else "java"
    commands = [
        ("bank", [str(ROOT / "node_modules/.bin/mb"), "--configfile",
                  str(ROOT / "imposters/bank_simulator.ejs"), "--allowInjection",
                  "--localOnly", "--loglevel", "error"], ROOT, 2525, "/imposters"),
        ("java", [java, "-jar", str(ROOT / "java/build/libs/payment-gateway.jar")], ROOT, 8090, "/health"),
        ("python", [sys.executable, "-m", "uvicorn", "payment_gateway_api.app:app",
                    "--host", "127.0.0.1", "--port", "8091", "--no-access-log"], ROOT / "python", 8091, "/health"),
    ]
    processes = []
    with tempfile.TemporaryDirectory(prefix="checkout-e2e-") as temp:
        log_dir = Path(temp)
        try:
            for name, command, cwd, port, path in commands:
                if name == "bank":
                    command += ["--logfile", str(log_dir / "bank-internal.log")]
                log = (log_dir / f"{name}.log").open("w")
                env = os.environ | {"BANK_URL": "http://127.0.0.1:8080", "PORT": "8090", "BANK_TIMEOUT_SECONDS": "2"}
                process = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
                processes.append((name, process, log))
                deadline = time.monotonic() + 60
                while True:
                    if process.poll() is not None:
                        raise RuntimeError(f"{name} exited with {process.returncode}")
                    try:
                        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=1) as response:
                            if response.status == 200:
                                break
                    except (urllib.error.URLError, TimeoutError):
                        pass
                    if time.monotonic() > deadline:
                        raise RuntimeError(f"{name} did not become ready")
                    time.sleep(0.1)
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/test_e2e.py", "-q"], cwd=ROOT,
                env=os.environ | {
                    "GATEWAY_URLS": "http://127.0.0.1:8090,http://127.0.0.1:8091",
                    "BANK_URL": "http://127.0.0.1:8080", "BANK_ADMIN_URL": "http://127.0.0.1:2525",
                    "GATEWAY_LOG_DIR": str(log_dir),
                },
            )
            if result.returncode:
                raise RuntimeError("E2E tests failed")
        except (RuntimeError, OSError):
            for name, process, log in processes:
                log.flush()
                print(f"\n{name} log:\n{(log_dir / f'{name}.log').read_text()[-12000:]}")
            raise
        finally:
            for name, process, log in reversed(processes):
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                log.close()


if __name__ == "__main__":
    main()
