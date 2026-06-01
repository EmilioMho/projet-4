"""
Envoi du rapport hebdomadaire via Gmail.

Credentials (par ordre de priorité) :
  1. mail_config.json  (fichier local, non versionné)
  2. Variables d'environnement : GMAIL_USER, GMAIL_APP_PASSWORD, MAIL_RECIPIENTS
     MAIL_RECIPIENTS est une liste séparée par des virgules.

Pour Gmail, utiliser un "App Password" (compte Google → Sécurité → Mots de passe
des applications) — les mots de passe classiques sont refusés depuis 2022.
"""

from __future__ import annotations

import json
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "output"
PAYLOAD_DIR = ROOT / "output" / "_payloads"
CONFIG_FILE = ROOT / "mail_config.json"

_PIOTROSKI_LABELS = {
    "f1_roa_positive": "ROA &gt; 0",
    "f2_cfo_positive": "Cash flow opérationnel &gt; 0",
    "f3_delta_roa": "ROA en hausse",
    "f4_accruals": "Qualité des bénéfices (CFO &gt; ROA)",
    "f5_delta_leverage": "Levier en baisse",
    "f6_delta_liquidity": "Liquidité en hausse",
    "f7_no_dilution": "Pas de dilution",
    "f8_delta_gross_margin": "Marge brute en hausse",
    "f9_delta_asset_turnover": "Rotation des actifs en hausse",
}


def load_config() -> dict:
    if CONFIG_FILE.exists():
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    else:
        cfg = {
            "gmail_user": os.environ.get("GMAIL_USER", ""),
            "gmail_password": os.environ.get("GMAIL_APP_PASSWORD", ""),
            "recipients": [
                r.strip()
                for r in os.environ.get("MAIL_RECIPIENTS", "").split(",")
                if r.strip()
            ],
        }
    return cfg


def load_payloads() -> list[dict]:
    payloads = []
    for f in sorted(PAYLOAD_DIR.glob("*.json")):
        try:
            payloads.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return sorted(
        payloads, key=lambda x: x.get("piotroski", {}).get("score", -1), reverse=True
    )


def _score_color(score: int | None) -> str:
    if score is None:
        return "#888888"
    if score >= 7:
        return "#2e7d32"
    if score >= 4:
        return "#e65100"
    return "#c62828"


def _fmt(v, pct: bool = False) -> str:
    if v is None:
        return "—"
    if pct:
        return f"{float(v) * 100:.1f} %"
    return f"{float(v):.2f}"


def build_html(payloads: list[dict]) -> str:
    rows = ""
    for p in payloads:
        meta = p.get("meta", {})
        pio = p.get("piotroski", {})
        score = pio.get("score")
        color = _score_color(score)
        price = _fmt(p.get("market", {}).get("price"))
        per = _fmt(p.get("valuation", {}).get("per", {}).get("value"))
        roe = _fmt(p.get("profitability", {}).get("roe", {}).get("value"), pct=True)
        net_m = _fmt(
            p.get("profitability", {}).get("net_margin", {}).get("value"), pct=True
        )
        rev_g = _fmt(
            p.get("growth", {}).get("revenue_growth", {}).get("value"), pct=True
        )

        details = pio.get("details", {})
        detail_cells = "".join(
            f'<td style="text-align:center; color:{"#2e7d32" if v == 1 else ("#c62828" if v == 0 else "#888")};">'
            f"{'✓' if v == 1 else ('✗' if v == 0 else '?')}</td>"
            for v in details.values()
        )

        rows += f"""
        <tr>
          <td style="font-weight:bold; white-space:nowrap;">{meta.get("symbol", "")}</td>
          <td>{meta.get("name", "")}</td>
          <td style="font-size:11px; color:#555;">{meta.get("sector", "")}</td>
          <td style="text-align:center; font-weight:bold; color:{color}; font-size:15px;">{score}/9</td>
          <td style="text-align:right;">{price}</td>
          <td style="text-align:right;">{per}</td>
          <td style="text-align:right;">{roe}</td>
          <td style="text-align:right;">{net_m}</td>
          <td style="text-align:right;">{rev_g}</td>
          {detail_cells}
        </tr>"""

    f1_to_f9 = "".join(
        f'<th style="font-size:9px; max-width:50px; white-space:normal;">{lbl}</th>'
        for lbl in _PIOTROSKI_LABELS.values()
    )

    pdf_count = len(list(OUTPUT_DIR.glob("*.pdf")))

    return f"""<!DOCTYPE html>
<html lang="fr"><body style="font-family: Arial, sans-serif; color: #222;">
<h2 style="color:#1a237e; border-bottom:2px solid #1a237e; padding-bottom:6px;">
  Rapport boursier hebdomadaire
</h2>
<p style="color:#555; font-size:13px;">
  {len(payloads)} société(s) analysée(s) · {pdf_count} fiche(s) PDF en pièces jointes
</p>
<table border="1" cellpadding="5" cellspacing="0"
       style="border-collapse:collapse; font-size:12px; width:100%;">
  <thead style="background:#1a237e; color:white;">
    <tr>
      <th>Ticker</th><th>Société</th><th>Secteur</th>
      <th>Score F</th><th>Cours</th><th>PER</th>
      <th>ROE</th><th>Mg. nette</th><th>Croiss. CA</th>
      {f1_to_f9}
    </tr>
  </thead>
  <tbody>
    {rows}
  </tbody>
</table>
<p style="margin-top:16px; font-size:11px; color:#999;">
  Score F de Piotroski&nbsp;: 0–3 faible (rouge) · 4–6 neutre (orange) · 7–9 solide (vert).
  Moyennes sectorielles&nbsp;: Damodaran janvier 2025.
</p>

<h3 style="margin-top:28px; margin-bottom:8px; font-size:13px; color:#1a237e; border-bottom:1px solid #c5cae9; padding-bottom:4px;">
  Rappel des indicateurs
</h3>
<table cellpadding="4" cellspacing="0" style="font-size:11px; color:#444; border-collapse:collapse; width:100%;">
  <tr style="background:#e8eaf6;">
    <td colspan="2" style="padding:4px 6px; font-weight:bold; color:#1a237e;">Indicateurs de valorisation</td>
  </tr>
  <tr><td style="width:160px; font-weight:bold; white-space:nowrap;">PER (trailing)</td><td>Cours rapporté aux bénéfices passés ; une valeur inférieure à la moyenne sectorielle indique un titre potentiellement sous-valorisé.</td></tr>
  <tr style="background:#f5f5f5;"><td style="font-weight:bold;">PER prévisionnel</td><td>Cours rapporté aux bénéfices attendus ; plus fiable que le trailing pour anticiper la valorisation future.</td></tr>
  <tr><td style="font-weight:bold;">PEG</td><td>PER divisé par le taux de croissance attendu ; un PEG inférieur à 1 suggère que la croissance n'est pas encore intégrée dans le cours.</td></tr>
  <tr style="background:#f5f5f5;"><td style="font-weight:bold;">Price / Book</td><td>Rapport cours / valeur comptable ; une valeur inférieure à 1 signale un titre coté en dessous de la valeur de ses actifs nets.</td></tr>
  <tr><td style="font-weight:bold;">EV / EBITDA</td><td>Multiple de valorisation indépendant de la structure financière ; un niveau élevé par rapport au secteur traduit une prime de valorisation.</td></tr>

  <tr style="background:#e8eaf6;">
    <td colspan="2" style="padding:4px 6px; font-weight:bold; color:#1a237e;">Indicateurs de rentabilité</td>
  </tr>
  <tr><td style="font-weight:bold;">ROE</td><td>Rentabilité des capitaux propres ; mesure l'efficacité avec laquelle l'entreprise crée de la valeur pour ses actionnaires.</td></tr>
  <tr style="background:#f5f5f5;"><td style="font-weight:bold;">Marge nette</td><td>Part du chiffre d'affaires convertie en bénéfice net ; reflète la rentabilité globale après charges et impôts.</td></tr>
  <tr><td style="font-weight:bold;">Croissance du CA</td><td>Progression annuelle des revenus ; indicateur de la dynamique commerciale et du potentiel de croissance.</td></tr>

  <tr style="background:#e8eaf6;">
    <td colspan="2" style="padding:4px 6px; font-weight:bold; color:#1a237e;">Critères Piotroski (score F)</td>
  </tr>
  <tr><td style="font-weight:bold;">ROA &gt; 0</td><td>Un ROA positif confirme que l'entreprise génère un bénéfice à partir de ses actifs.</td></tr>
  <tr style="background:#f5f5f5;"><td style="font-weight:bold;">CFO &gt; 0</td><td>Un flux de trésorerie opérationnel positif atteste d'une génération de cash effective, indépendante des écritures comptables.</td></tr>
  <tr><td style="font-weight:bold;">ROA en hausse</td><td>L'amélioration du ROA d'une année sur l'autre signale une utilisation plus efficiente des actifs.</td></tr>
  <tr style="background:#f5f5f5;"><td style="font-weight:bold;">Qualité des bénéfices</td><td>Un cash flow opérationnel supérieur au ROA indique que les bénéfices sont soutenus par du cash réel, et non par des ajustements comptables.</td></tr>
  <tr><td style="font-weight:bold;">Levier en baisse</td><td>La réduction du ratio dette / actifs renforce la résilience financière et réduit le risque de solvabilité.</td></tr>
  <tr style="background:#f5f5f5;"><td style="font-weight:bold;">Liquidité en hausse</td><td>L'amélioration du ratio de liquidité courante réduit l'exposition au risque de défaut à court terme.</td></tr>
  <tr><td style="font-weight:bold;">Pas de dilution</td><td>L'absence d'émission d'actions nouvelles préserve la valeur des actionnaires existants.</td></tr>
  <tr style="background:#f5f5f5;"><td style="font-weight:bold;">Marge brute en hausse</td><td>Une marge brute croissante reflète un meilleur pouvoir de fixation des prix ou une maîtrise accrue des coûts de production.</td></tr>
  <tr><td style="font-weight:bold;">Rotation des actifs en hausse</td><td>Une rotation accrue indique que l'entreprise génère davantage de chiffre d'affaires par unité d'actif — signe d'efficacité opérationnelle.</td></tr>
</table>

</body></html>"""


def send_report(config: dict | None = None) -> None:
    if config is None:
        config = load_config()

    sender = config.get("gmail_user", "")
    password = config.get("gmail_password", "")
    recipients: list[str] = config.get("recipients", [])

    if not sender or not password:
        raise ValueError(
            "Credentials Gmail manquants. Créez mail_config.json ou définissez "
            "GMAIL_USER et GMAIL_APP_PASSWORD."
        )
    if not recipients:
        raise ValueError("Aucun destinataire configuré (clé 'recipients').")

    payloads = load_payloads()
    pdfs = sorted(OUTPUT_DIR.glob("*.pdf"))

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = "Rapport boursier hebdomadaire"
    msg.attach(MIMEText(build_html(payloads), "html", "utf-8"))

    for pdf in pdfs:
        data = pdf.read_bytes()
        part = MIMEApplication(data, Name=pdf.name)
        part["Content-Disposition"] = f'attachment; filename="{pdf.name}"'
        msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, password)
        smtp.sendmail(sender, recipients, msg.as_string())

    print(f"✓ Mail envoyé à {', '.join(recipients)} ({len(pdfs)} PDFs joints)")


if __name__ == "__main__":
    send_report()
