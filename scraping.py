"""
Scraping financier multi-sources.
Source primaire : yfinance (info + états financiers annuels).
"""

from __future__ import annotations

import io
import logging
from typing import Any

import pandas as pd
import requests
import yfinance as yf

log = logging.getLogger(__name__)


def _safe(d: dict, key: str, default=None):
    """Récupère une valeur sans planter si elle vaut None, NaN ou est absente."""
    v = d.get(key, default)
    if v is None:
        return default
    try:
        if pd.isna(v):
            return default
    except (TypeError, ValueError):
        pass
    return v


def _safe_val(df: pd.DataFrame, *row_candidates: str, col: Any) -> float | None:
    """Lit une cellule d'un DataFrame yfinance en essayant plusieurs noms de ligne."""
    if df is None or df.empty:
        return None
    for row in row_candidates:
        if row in df.index:
            try:
                v = df.loc[row, col]
                if pd.notna(v):
                    return float(v)
            except Exception:
                pass
    return None


def fetch_yfinance(symbol: str) -> dict[str, Any]:
    """Récupère les indicateurs ponctuels via yfinance.info."""
    t = yf.Ticker(symbol)
    info = t.info or {}

    return {
        # Identité
        "symbol": symbol,
        "name": _safe(info, "longName") or _safe(info, "shortName"),
        "sector_yf": _safe(info, "sector"),
        "industry": _safe(info, "industry"),
        "country": _safe(info, "country"),
        "currency": _safe(info, "currency"),
        "exchange": _safe(info, "exchange"),
        # Cours et capitalisation
        "price": _safe(info, "currentPrice") or _safe(info, "regularMarketPrice"),
        "market_cap": _safe(info, "marketCap"),
        "enterprise_value": _safe(info, "enterpriseValue"),
        "52w_high": _safe(info, "fiftyTwoWeekHigh"),
        "52w_low": _safe(info, "fiftyTwoWeekLow"),
        "beta": _safe(info, "beta"),
        # Valorisation
        "per": _safe(info, "trailingPE"),
        "forward_per": _safe(info, "forwardPE"),
        "peg": _safe(info, "trailingPegRatio") or _safe(info, "pegRatio"),
        "price_to_book": _safe(info, "priceToBook"),
        "price_to_sales": _safe(info, "priceToSalesTrailing12Months"),
        "ev_ebitda": _safe(info, "enterpriseToEbitda"),
        "ev_revenue": _safe(info, "enterpriseToRevenue"),
        # Rentabilité (TTM)
        "roe": _safe(info, "returnOnEquity"),
        "roa": _safe(info, "returnOnAssets"),
        "gross_margin": _safe(info, "grossMargins"),
        "operating_margin": _safe(info, "operatingMargins"),
        "net_margin": _safe(info, "profitMargins"),
        # Santé financière
        "debt_to_equity": _safe(info, "debtToEquity"),
        "current_ratio": _safe(info, "currentRatio"),
        "quick_ratio": _safe(info, "quickRatio"),
        "total_debt": _safe(info, "totalDebt"),
        "total_cash": _safe(info, "totalCash"),
        # Croissance
        "revenue_growth": _safe(info, "revenueGrowth"),
        "earnings_growth": _safe(info, "earningsGrowth"),
        "revenue_ttm": _safe(info, "totalRevenue"),
        "eps_ttm": _safe(info, "trailingEps"),
        "eps_forward": _safe(info, "forwardEps"),
        # Dividende
        "dividend_yield": _safe(info, "dividendYield"),
        "payout_ratio": _safe(info, "payoutRatio"),
        "dividend_rate": _safe(info, "dividendRate"),
        # Champs supplémentaires pour Piotroski (TTM)
        "operating_cashflow": _safe(info, "operatingCashflow"),
        "total_assets": _safe(info, "totalAssets"),
        "shares_outstanding": _safe(info, "sharesOutstanding"),
        # Consensus analystes
        "recommendation": _safe(info, "recommendationKey"),
        "target_price": _safe(info, "targetMeanPrice"),
        "analysts_count": _safe(info, "numberOfAnalystOpinions"),
    }


def fetch_historical(symbol: str) -> list[dict[str, Any]]:
    """
    Extrait jusqu'à 4 exercices annuels depuis yfinance (compte de résultat,
    bilan, flux de trésorerie). Retourne une liste triée du plus ancien au plus récent.
    """
    t = yf.Ticker(symbol)
    by_year: dict[int, dict[str, Any]] = {}

    def _add(year: int, key: str, value: float | None) -> None:
        if value is None:
            return
        by_year.setdefault(year, {"year": year})[key] = value

    # ── Compte de résultat ──────────────────────────────────
    try:
        fin = t.financials  # rows = métriques, cols = dates
        if fin is not None and not fin.empty:
            for col in fin.columns:
                y = col.year
                _add(y, "revenue", _safe_val(fin, "Total Revenue", "Revenue", col=col))
                _add(y, "gross_profit", _safe_val(fin, "Gross Profit", col=col))
                _add(y, "operating_income", _safe_val(fin, "Operating Income", "EBIT", col=col))
                _add(
                    y,
                    "net_income",
                    _safe_val(
                        fin,
                        "Net Income",
                        "Net Income Common Stockholders",
                        "Net Income Applicable To Common Shares",
                        col=col,
                    ),
                )
                _add(y, "ebitda", _safe_val(fin, "EBITDA", col=col))
                _add(y, "basic_eps", _safe_val(fin, "Basic EPS", "Diluted EPS", col=col))
    except Exception as e:
        log.warning("%s – financials indisponibles : %s", symbol, e)

    # ── Bilan ────────────────────────────────────────────────
    try:
        bs = t.balance_sheet
        if bs is not None and not bs.empty:
            for col in bs.columns:
                y = col.year
                _add(y, "total_assets", _safe_val(bs, "Total Assets", col=col))
                _add(
                    y,
                    "long_term_debt",
                    _safe_val(
                        bs,
                        "Long Term Debt",
                        "Long Term Debt And Capital Lease Obligation",
                        col=col,
                    ),
                )
                _add(y, "current_assets", _safe_val(bs, "Current Assets", col=col))
                _add(
                    y,
                    "current_liabilities",
                    _safe_val(bs, "Current Liabilities", col=col),
                )
                _add(
                    y,
                    "shares_outstanding",
                    _safe_val(
                        bs,
                        "Ordinary Shares Number",
                        "Share Issued",
                        "Common Stock",
                        col=col,
                    ),
                )
                _add(
                    y,
                    "total_debt",
                    _safe_val(
                        bs,
                        "Total Debt",
                        "Long Term Debt And Capital Lease Obligation",
                        col=col,
                    ),
                )
    except Exception as e:
        log.warning("%s – balance_sheet indisponible : %s", symbol, e)

    # ── Flux de trésorerie ───────────────────────────────────
    try:
        cf = t.cashflow
        if cf is not None and not cf.empty:
            for col in cf.columns:
                y = col.year
                _add(
                    y,
                    "operating_cashflow",
                    _safe_val(
                        cf,
                        "Operating Cash Flow",
                        "Cash From Operating Activities",
                        "Total Cash From Operating Activities",
                        col=col,
                    ),
                )
                _add(y, "free_cashflow", _safe_val(cf, "Free Cash Flow", col=col))
                _add(y, "capex", _safe_val(cf, "Capital Expenditure", "Capital Expenditures", col=col))
    except Exception as e:
        log.warning("%s – cashflow indisponible : %s", symbol, e)

    return sorted(by_year.values(), key=lambda x: x["year"])


def fetch_stooq_price(symbol: str) -> float | None:
    """Fallback prix : Stooq fournit un CSV gratuit sans clé API."""
    stooq_symbol = _to_stooq_symbol(symbol)
    url = f"https://stooq.com/q/d/l/?s={stooq_symbol}&i=d"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        if df.empty or "Close" not in df.columns:
            return None
        return float(df["Close"].iloc[-1])
    except Exception as e:
        log.warning("Stooq fallback échoué pour %s : %s", symbol, e)
        return None


def _to_stooq_symbol(symbol: str) -> str:
    mapping = {".PA": ".FR", ".DE": ".DE", ".AS": ".NL", ".MI": ".IT", ".L": ".UK"}
    for yf_suf, stooq_suf in mapping.items():
        if symbol.endswith(yf_suf):
            return symbol.replace(yf_suf, stooq_suf).lower()
    return f"{symbol.lower()}.us"


def fetch_ticker(symbol: str) -> dict[str, Any]:
    """Point d'entrée : agrège toutes les sources pour un ticker."""
    log.info("Scraping %s…", symbol)
    data = fetch_yfinance(symbol)

    if data.get("price") is None:
        data["price"] = fetch_stooq_price(symbol)
        if data["price"] is not None:
            log.info("  prix récupéré via Stooq")

    data["historical"] = fetch_historical(symbol)
    return data
