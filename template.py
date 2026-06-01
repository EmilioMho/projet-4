"""
Calcul du score F de Piotroski et construction du payload Typst.
"""

from __future__ import annotations

from typing import Any

from damodaran import get_sector_avg

# ── Piotroski F-Score ─────────────────────────────────────────────────────────


def _roa(net_income: float | None, total_assets: float | None) -> float | None:
    if net_income is None or total_assets is None or total_assets == 0:
        return None
    return net_income / total_assets


def compute_piotroski(historical: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Calcule les 9 critères du score F de Piotroski à partir des 2 derniers exercices.
    Retourne { score, max, details } où chaque critère vaut 1 (réussi), 0 (échoué)
    ou None (données insuffisantes, non compté).
    """
    hist = sorted(historical, key=lambda x: x.get("year", 0), reverse=True)
    curr = hist[0] if hist else {}
    prev = hist[1] if len(hist) > 1 else {}

    ta_c = curr.get("total_assets")
    ta_p = prev.get("total_assets")
    ni_c = curr.get("net_income")
    ni_p = prev.get("net_income")
    cfo_c = curr.get("operating_cashflow")
    rev_c = curr.get("revenue")
    rev_p = prev.get("revenue")
    gp_c = curr.get("gross_profit")
    gp_p = prev.get("gross_profit")
    ltd_c = curr.get("long_term_debt") or curr.get("total_debt") or 0
    ltd_p = prev.get("long_term_debt") or prev.get("total_debt") or 0
    ca_c = curr.get("current_assets")
    cl_c = curr.get("current_liabilities")
    ca_p = prev.get("current_assets")
    cl_p = prev.get("current_liabilities")
    sh_c = curr.get("shares_outstanding")
    sh_p = prev.get("shares_outstanding")

    roa_c = _roa(ni_c, ta_c)
    roa_p = _roa(ni_p, ta_p)
    cr_c = (ca_c / cl_c) if (ca_c and cl_c) else None
    cr_p = (ca_p / cl_p) if (ca_p and cl_p) else None
    lev_c = (ltd_c / ta_c) if ta_c else None
    lev_p = (ltd_p / ta_p) if ta_p else None
    gm_c = (gp_c / rev_c) if (gp_c and rev_c) else None
    gm_p = (gp_p / rev_p) if (gp_p and rev_p) else None
    at_c = (rev_c / ta_c) if (rev_c and ta_c) else None
    at_p = (rev_p / ta_p) if (rev_p and ta_p) else None

    details: dict[str, int | None] = {
        # Rentabilité
        "f1_roa_positive": int(roa_c > 0) if roa_c is not None else None,
        "f2_cfo_positive": int(cfo_c > 0) if cfo_c is not None else None,
        "f3_delta_roa": int(roa_c > roa_p)
        if (roa_c is not None and roa_p is not None)
        else None,
        "f4_accruals": int((cfo_c / ta_c) > roa_c)
        if (cfo_c is not None and ta_c is not None and roa_c is not None)
        else None,
        # Levier / liquidité / dilution
        "f5_delta_leverage": int(lev_c < lev_p)
        if (lev_c is not None and lev_p is not None)
        else None,
        "f6_delta_liquidity": int(cr_c > cr_p)
        if (cr_c is not None and cr_p is not None)
        else None,
        "f7_no_dilution": int(sh_c <= sh_p)
        if (sh_c is not None and sh_p is not None)
        else None,
        # Efficacité opérationnelle
        "f8_delta_gross_margin": int(gm_c > gm_p)
        if (gm_c is not None and gm_p is not None)
        else None,
        "f9_delta_asset_turnover": int(at_c > at_p)
        if (at_c is not None and at_p is not None)
        else None,
    }

    score = sum(v for v in details.values() if v is not None)
    return {"score": score, "max": 9, "details": details}


# ── Payload Typst ─────────────────────────────────────────────────────────────


def build_fiche_payload(
    ticker_data: dict[str, Any],
    sector_avg: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Construit le dict sérialisé en JSON et lu par Typst.
    Si sector_avg est None, les moyennes Damodaran sont récupérées automatiquement.
    """
    if sector_avg is None:
        sector_avg = get_sector_avg(ticker_data.get("sector"))

    historical: list[dict] = ticker_data.get("historical", [])

    return {
        "meta": {
            "symbol": ticker_data.get("symbol"),
            "name": ticker_data.get("name"),
            "sector": ticker_data.get("sector"),
            "industry": ticker_data.get("industry"),
            "country": ticker_data.get("country"),
            "currency": ticker_data.get("currency") or "USD",
            "exchange": ticker_data.get("exchange"),
            "recommendation": ticker_data.get("recommendation"),
            "target_price": ticker_data.get("target_price"),
            "analysts_count": ticker_data.get("analysts_count"),
        },
        "market": {
            "price": ticker_data.get("price"),
            "market_cap": ticker_data.get("market_cap"),
            "enterprise_value": ticker_data.get("enterprise_value"),
            "52w_high": ticker_data.get("52w_high"),
            "52w_low": ticker_data.get("52w_low"),
            "beta": ticker_data.get("beta"),
        },
        "valuation": _pair_block(
            ticker_data,
            sector_avg,
            [
                "per",
                "forward_per",
                "peg",
                "price_to_book",
                "price_to_sales",
                "ev_ebitda",
                "ev_revenue",
            ],
        ),
        "profitability": _pair_block(
            ticker_data,
            sector_avg,
            [
                "roe",
                "roa",
                "gross_margin",
                "operating_margin",
                "net_margin",
            ],
        ),
        "health": _pair_block(
            ticker_data,
            sector_avg,
            [
                "debt_to_equity",
                "current_ratio",
                "quick_ratio",
            ],
        ),
        "growth": _pair_block(
            ticker_data,
            sector_avg,
            [
                "revenue_growth",
                "earnings_growth",
            ],
        ),
        "dividend": _pair_block(
            ticker_data,
            sector_avg,
            [
                "dividend_yield",
                "payout_ratio",
            ],
        ),
        "extras": {
            "revenue_ttm": ticker_data.get("revenue_ttm"),
            "eps_ttm": ticker_data.get("eps_ttm"),
            "eps_forward": ticker_data.get("eps_forward"),
            "total_debt": ticker_data.get("total_debt"),
            "total_cash": ticker_data.get("total_cash"),
            "dividend_rate": ticker_data.get("dividend_rate"),
            "operating_cashflow": ticker_data.get("operating_cashflow"),
            "total_assets": ticker_data.get("total_assets"),
        },
        "piotroski": compute_piotroski(historical),
        "historical": historical,
    }


def _pair_block(data: dict, sector_avg: dict, keys: list[str]) -> dict:
    return {k: {"value": data.get(k), "sector_avg": sector_avg.get(k)} for k in keys}
