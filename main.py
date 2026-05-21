import subprocess
import os
import re
import shutil
import logging
from logging.handlers import RotatingFileHandler

LOG_PATH = "/tmp/amneziawg.log"
_handler = RotatingFileHandler(LOG_PATH, maxBytes=512 * 1024, backupCount=2)
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[_handler])

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(PLUGIN_DIR, "bin")
AWG = os.path.join(BIN_DIR, "awg")
AWG_QUICK = os.path.join(BIN_DIR, "awg-quick")

# Configs live in user home so SteamOS atomic updates don't wipe them.
CONF_DIR = "/home/deck/.config/amneziawg"
# Quick lookups (awg show) should be ~instant.
STATUS_TIMEOUT = 10
# awg-quick up/down via userspace amneziawg-go can take a while on first
# handshake — the daemon has to fork, open TUN, exchange keys, and only
# then setconf/ip add/resolvconf can run.
QUICK_TIMEOUT = 60

_CONF_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+\.conf$")


def _env() -> dict:
    """Env for bundled tools: PATH includes our bin/ so awg-quick finds `awg`
    and `amneziawg-go`. The userspace impl is forced because the kernel
    module isn't installed on SteamOS — awg-quick falls back to it on
    `ip link add ... type amneziawg` failure.

    Decky-loader injects its own LD_LIBRARY_PATH/LD_PRELOAD that point to
    its bundled libs (newer than system). When we exec /bin/bash for
    awg-quick, those libs get pulled in and break readline lookups
    (`undefined symbol: rl_trim_arg_from_keyseq`). Strip them so system
    binaries link against system libs."""
    env = {
        k: v for k, v in os.environ.items()
        if k not in ("LD_LIBRARY_PATH", "LD_PRELOAD", "PYTHONPATH", "PYTHONHOME")
    }
    env.update({
        "PATH": f"{BIN_DIR}:/usr/sbin:/usr/bin:/sbin:/bin",
        "WG_QUICK_USERSPACE_IMPLEMENTATION": "amneziawg-go",
        "LC_ALL": "C",
    })
    return env


def _valid_conf_name(conf: str) -> bool:
    return bool(conf) and _CONF_NAME_RE.match(conf) is not None and ".." not in conf


def _run(cmd: list, timeout: int = STATUS_TIMEOUT) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, env=_env()
    )


def _is_iface_up(iface: str) -> bool:
    """Quick check: is the given amneziawg interface present?"""
    try:
        r = _run([AWG, "show", "interfaces"])
        return iface in r.stdout.split()
    except Exception:
        return False


def _ensure_conf_dir():
    try:
        os.makedirs(CONF_DIR, exist_ok=True)
        try:
            shutil.chown(CONF_DIR, user="deck", group="deck")
            os.chmod(CONF_DIR, 0o700)
        except (LookupError, PermissionError) as e:
            logging.warning(f"chown {CONF_DIR}: {e}")
        # Lock down .conf perms — awg-quick warns when configs are
        # world-readable (they contain private keys).
        for f in os.listdir(CONF_DIR):
            if f.endswith(".conf"):
                try:
                    os.chmod(os.path.join(CONF_DIR, f), 0o600)
                except OSError:
                    pass
    except Exception as e:
        logging.error(f"_ensure_conf_dir: {e}")


class Plugin:

    async def get_status(self) -> dict:
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
            logging.error("get_status: timed out")
            return {"connected": False, "interface": None, "interfaces": []}
        except FileNotFoundError:
            logging.error(f"get_status: bundled binary missing at {AWG}")
            return {"connected": False, "interface": None, "interfaces": []}
        except Exception as e:
            logging.error(f"get_status error: {e}")
            return {"connected": False, "interface": None, "interfaces": []}

    async def get_configs(self) -> list:
        try:
            _ensure_conf_dir()
            if not os.path.isdir(CONF_DIR):
                return []
            files = [
                f for f in os.listdir(CONF_DIR)
                if f.endswith(".conf") and _valid_conf_name(f)
            ]
            return sorted(files)
        except Exception as e:
            logging.error(f"get_configs error: {e}")
            return []

    async def get_conf_dir(self) -> str:
        return CONF_DIR

    async def connect(self, conf: str) -> dict:
        if not _valid_conf_name(conf):
            return {"ok": False, "error": "Invalid config name"}
        iface = conf[:-5]  # strip .conf
        try:
            conf_path = os.path.join(CONF_DIR, conf)
            if not os.path.isfile(conf_path):
                return {"ok": False, "error": f"Config not found: {conf}"}
            result = _run([AWG_QUICK, "up", conf_path], timeout=QUICK_TIMEOUT)
            if result.returncode != 0:
                logging.error(f"connect stderr: {result.stderr}")
                return {"ok": False, "error": result.stderr.strip() or "awg-quick up failed"}
            return {"ok": True}
        except subprocess.TimeoutExpired:
            # awg-quick was killed, but amneziawg-go forked off — the
            # interface may already be up. Treat that as success rather
            # than scaring the user with a Timeout error.
            if _is_iface_up(iface):
                logging.warning(f"connect: awg-quick timed out but {iface} is up")
                return {"ok": True}
            return {"ok": False, "error": "Timeout"}
        except FileNotFoundError:
            return {"ok": False, "error": "Bundled awg-quick missing"}
        except Exception as e:
            logging.error(f"connect error: {e}")
            return {"ok": False, "error": str(e)}

    async def disconnect(self, conf: str) -> dict:
        if not _valid_conf_name(conf):
            return {"ok": False, "error": "Invalid config name"}
        iface = conf[:-5]
        try:
            conf_path = os.path.join(CONF_DIR, conf)
            result = _run([AWG_QUICK, "down", conf_path], timeout=QUICK_TIMEOUT)
            if result.returncode != 0:
                logging.error(f"disconnect stderr: {result.stderr}")
                return {"ok": False, "error": result.stderr.strip() or "awg-quick down failed"}
            return {"ok": True}
        except subprocess.TimeoutExpired:
            # Mirror image of connect's timeout handling: if the iface
            # is already gone, the down completed despite the kill.
            if not _is_iface_up(iface):
                logging.warning(f"disconnect: awg-quick timed out but {iface} is gone")
                return {"ok": True}
            return {"ok": False, "error": "Timeout"}
        except FileNotFoundError:
            return {"ok": False, "error": "Bundled awg-quick missing"}
        except Exception as e:
            logging.error(f"disconnect error: {e}")
            return {"ok": False, "error": str(e)}

    async def _main(self):
        _ensure_conf_dir()

    async def _unload(self):
        pass
