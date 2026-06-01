"""
Orchestrateur principal : tickers.json → scraping → data.json → fiches PDF.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from scraping import fetch_ticker
from template import build_fiche_payload

logging.basicConfig(level=logging.INFO, format="%(levelname)s · %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).parent
TICKERS_FILE = ROOT / "tickers.json"
DATA_FILE = ROOT / "data.json"
TEMPLATE_FILE = ROOT / "fiche.typ"
OUTPUT_DIR = ROOT / "output"
PAYLOAD_DIR = ROOT / "output" / "_payloads"


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)

    tickers_cfg = json.loads(TICKERS_FILE.read_text(encoding="utf-8"))
    tickers = tickers_cfg["tickers"]
    log.info("→ %d tickers à traiter", len(tickers))

    all_data: list[dict] = []
    for t in tickers:
        try:
            data = fetch_ticker(t["symbol"])
            # Le secteur défini dans tickers.json prévaut sur yfinance (plus fiable)
            data["sector"] = t["sector"]
            data["name"] = data.get("name") or t["name"]
            all_data.append(data)
        except Exception as e:
            log.error("✗ Échec sur %s : %s", t["symbol"], e)

    DATA_FILE.write_text(
        json.dumps(all_data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    log.info("✓ data.json écrit (%d entrées)", len(all_data))

    for d in all_data:
        symbol = d["symbol"]
        payload = build_fiche_payload(d)  # moyennes Damodaran intégrées automatiquement

        payload_path = PAYLOAD_DIR / f"{symbol}.json"
        payload_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

        rel_payload = payload_path.relative_to(TEMPLATE_FILE.parent).as_posix()
        pdf_path = OUTPUT_DIR / f"{symbol}.pdf"
        try:
            subprocess.run(
                ["typst", "compile", "--input", f"data={rel_payload}",
                 str(TEMPLATE_FILE), str(pdf_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            log.info("✓ %s → %s", symbol, pdf_path.name)
        except subprocess.CalledProcessError as e:
            log.error("✗ Compilation Typst échouée pour %s :\n%s", symbol, e.stderr)
        except FileNotFoundError:
            log.error("✗ La commande `typst` est introuvable.")
            break


if __name__ == "__main__":
    main()
