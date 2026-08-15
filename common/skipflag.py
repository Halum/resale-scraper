"""Global platform skip flag -- global_config.json at repo root, kills a
platform everywhere at once (e.g. Vinted-wide Cloudflare trouble)."""
import json, pathlib

GLOBAL_CFG_PATH = pathlib.Path(__file__).parent.parent / "global_config.json"


def platform_enabled(cfg, platform):
    global_cfg = json.loads(GLOBAL_CFG_PATH.read_text()) if GLOBAL_CFG_PATH.exists() else {}
    return global_cfg.get(platform, {}).get("enabled", True)
