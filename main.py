import subprocess
import os
import re
import logging
from logging.handlers import RotatingFileHandler

LOG_PATH = "/tmp/amneziawg.log"
_handler = RotatingFileHandler(LOG_PATH, maxBytes=512 * 1024, backupCount=2)
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[_handler])

CONF_DIR = "/etc/amnezia/amneziawg"
AWG = "awg"
AWG_QUICK = "awg-quick"
CMD_TIMEOUT = 15

_CONF_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+\.conf$")


def _valid_conf_name(conf: str) -> bool:
    return bool(conf) and _CONF_NAME_RE.match(conf) is not None and ".." not in conf


def _run(cmd: list) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=CMD_TIMEOUT)


class Plugin:

    async def get_status(self) -> dict:
        """Return VPN status: connected flag and list of active interfaces."""
        try:
            result = _run([AWG, "show", "interfaces"])
            if result.returncode != 0:
                logging.error(f"awg show interfaces failed: {result.stderr.strip()}")
                return {"connected": False, "interface": None, "interfaces": []}
            ifaces = result.stdout.split()
            connected = len(ifaces) > 0
            return {
                "connected": connected,
                "interface": ifaces[0] if connected else None,
                "interfaces": ifaces,
            }
        except subprocess.TimeoutExpired:
            logging.error("get_status: awg show timed out")
            return {"connected": False, "interface": None, "interfaces": []}
        except FileNotFoundError:
            logging.error("get_status: 'awg' binary not found")
            return {"connected": False, "interface": None, "interfaces": []}
        except Exception as e:
            logging.error(f"get_status error: {e}")
            return {"connected": False, "interface": None, "interfaces": []}

    async def get_configs(self) -> list:
        """Return sorted list of available .conf files in CONF_DIR."""
        try:
            if not os.path.isdir(CONF_DIR):
                return []
            files = [f for f in os.listdir(CONF_DIR) if f.endswith(".conf") and _valid_conf_name(f)]
            return sorted(files)
        except Exception as e:
            logging.error(f"get_configs error: {e}")
            return []

    async def connect(self, conf: str) -> dict:
        """Bring up VPN using awg-quick."""
        if not _valid_conf_name(conf):
            return {"ok": False, "error": "Invalid config name"}
        try:
            conf_path = os.path.join(CONF_DIR, conf)
            if not os.path.isfile(conf_path):
                return {"ok": False, "error": f"Config not found: {conf}"}
            result = _run([AWG_QUICK, "up", conf_path])
            if result.returncode != 0:
                logging.error(f"connect stderr: {result.stderr}")
                return {"ok": False, "error": result.stderr.strip() or "awg-quick up failed"}
            return {"ok": True}
        except subprocess.TimeoutExpired:
            logging.error("connect: awg-quick up timed out")
            return {"ok": False, "error": "Timeout"}
        except FileNotFoundError:
            return {"ok": False, "error": "awg-quick not installed"}
        except Exception as e:
            logging.error(f"connect error: {e}")
            return {"ok": False, "error": str(e)}

    async def disconnect(self, conf: str) -> dict:
        """Bring down VPN using awg-quick."""
        if not _valid_conf_name(conf):
            return {"ok": False, "error": "Invalid config name"}
        try:
            conf_path = os.path.join(CONF_DIR, conf)
            result = _run([AWG_QUICK, "down", conf_path])
            if result.returncode != 0:
                logging.error(f"disconnect stderr: {result.stderr}")
                return {"ok": False, "error": result.stderr.strip() or "awg-quick down failed"}
            return {"ok": True}
        except subprocess.TimeoutExpired:
            logging.error("disconnect: awg-quick down timed out")
            return {"ok": False, "error": "Timeout"}
        except FileNotFoundError:
            return {"ok": False, "error": "awg-quick not installed"}
        except Exception as e:
            logging.error(f"disconnect error: {e}")
            return {"ok": False, "error": str(e)}

    async def _main(self):
        pass

    async def _unload(self):
        pass
