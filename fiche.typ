// Fiche d'investissement — design rapport annuel vert forêt / menthe
// Inspiré du template Canva "vert blanc moderne rapport annuel"
// typst compile --input "data=output/_payloads/AAPL.json" fiche.typ output/AAPL.pdf

#let payload-path = sys.inputs.at("data", default: "output/_payloads/AAPL.json")
#let data = json(payload-path)
#let meta = data.meta
#let market = data.market
#let piotroski = data.at("piotroski", default: (:))
#let historical = data.at("historical", default: ())

// ── Constantes & Palette ──────────────────────────────────────────────
#let G = 1.4cm
#let forest = rgb("#1b3a2e")
#let forest2 = rgb("#254d3c")
#let mint = rgb("#e8f5f0")
#let mint2 = rgb("#cde8df")
#let teal = rgb("#2aa897")
#let teal-lt = rgb("#a8d8d2")
#let green-ok = rgb("#27ae60")
#let red-bad = rgb("#c0392b")
#let amber = rgb("#d68910")
#let white = luma(255)
#let ink = rgb("#1a2e2b")
#let muted = rgb("#5a7a72")

// ── Page ─────────────────────────────────────────────────────────────
#set page(
  paper: "a4",
  margin: (x: 0cm, top: 0cm, bottom: 0cm),
  fill: white,
  footer: context [
    #block(fill: forest, width: 100%, inset: (x: G, y: 0.28cm))[
      #text(6.5pt, fill: teal-lt)[
        #meta.symbol — Généré le #datetime.today().display("[day]/[month]/[year]")
        — Moyennes Damodaran jan. 2025
        #h(1fr) p. #counter(page).display()
      ]
    ]
  ],
)
#set text(
  font: ("Calibri", "Arial", "New Computer Modern"),
  size: 9pt,
  fill: ink,
)
#set par(leading: 0.55em)

// ── Score Piotroski ────────────────────────────────────────────────────
#let p-score = piotroski.at("score", default: 0)
#let p-details = piotroski.at("details", default: (:))
#let score-col = if p-score >= 7 { teal } else if p-score >= 4 { amber } else { red-bad }
#let score-lbl = if p-score >= 7 { "Solide" } else if p-score >= 4 { "Neutre" } else { "Faible" }

// ── Recommandation ────────────────────────────────────────────────────
#let reco-str = meta.at("recommendation", default: none)
#let reco-col = if reco-str in ("strong_buy", "buy") { green-ok } else if reco-str == "hold" { amber } else if (
  reco-str in ("sell", "strong_sell")
) { red-bad } else { muted }
#let reco-lbl = if reco-str == "strong_buy" { "FORT ACHAT" } else if reco-str == "buy" { "ACHAT" } else if (
  reco-str == "hold"
) { "CONSERVER" } else if reco-str == "sell" { "VENDRE" } else if reco-str == "strong_sell" { "FORT VENTE" } else {
  none
}

// ── Helpers formatage ─────────────────────────────────────────────────
#let na = text(fill: muted, style: "italic")[—]

#let fmt-num(v, decimals: 2) = {
  if v == none { return na }
  let n = float(v)
  if calc.abs(n) >= 1e12 { str(calc.round(n / 1e12, digits: 2)) + " T" } else if calc.abs(n) >= 1e9 {
    str(calc.round(n / 1e9, digits: 2)) + " Md"
  } else if calc.abs(n) >= 1e6 { str(calc.round(n / 1e6, digits: 2)) + " M" } else {
    str(calc.round(n, digits: decimals))
  }
}

#let fmt-pct(v) = {
  if v == none { return na }
  str(calc.round(float(v) * 100, digits: 1)) + " %"
}

#let compare(val, avg, higher_is_better: true) = {
  if val == none or avg == none { return na }
  let v = float(val)
  let a = float(avg)
  if calc.abs(a) < 1e-9 { return na }
  let diff = ((v - a) / calc.abs(a)) * 100
  let better = if higher_is_better { v > a } else { v < a }
  text(fill: if better { teal } else { red-bad }, weight: "bold")[
    #(if better { "▲" } else { "▼" }) #str(calc.round(diff, digits: 1)) %
  ]
}

#let metric-row(label, blk, key, is_pct: false, higher_is_better: true) = {
  let val = blk.at(key).value
  let avg = blk.at(key).sector_avg
  (
    text(8pt)[#label],
    if is_pct { fmt-pct(val) } else { fmt-num(val) },
    if is_pct { fmt-pct(avg) } else { fmt-num(avg) },
    compare(val, avg, higher_is_better: higher_is_better),
  )
}

#let metric-tbl(rows) = table(
  columns: (1.6fr, 1fr, 1fr, 0.8fr),
  stroke: none,
  align: (left, right, right, right),
  inset: (x: 4pt, y: 3pt),
  fill: (_, y) => if y == 0 { mint2 } else if calc.even(y) { white } else { mint },
  table.header(
    text(6.5pt, fill: muted, weight: "bold")[INDICATEUR],
    text(6.5pt, fill: muted, weight: "bold")[VALEUR],
    text(6.5pt, fill: muted, weight: "bold")[SECTEUR],
    text(6.5pt, fill: muted, weight: "bold")[ÉCART],
  ),
  ..rows.flatten(),
)

// Barre de progression horizontale
#let pbar(label, val, max-val: 1.0, color: teal) = {
  let pct = if val == none { 0.0 } else { calc.min(calc.max(float(val) / max-val, 0.0), 1.0) }
  let neg = val != none and float(val) < 0
  let display = if val == none { "—" } else { str(calc.round(float(val) * 100, digits: 1)) + " %" }
  let bar-col = if neg { red-bad } else { color }

  block(width: 100%, above: 2mm, below: 0.5mm)[
    #grid(
      columns: (1fr, auto),
      text(7.5pt, fill: muted)[#label], text(8.5pt, weight: "bold", fill: bar-col)[#display],
    )
    #block(width: 100%, height: 4.5pt, radius: 2.25pt, fill: mint2, clip: true)[
      #place(left + horizon)[
        #block(width: pct * 100%, height: 4.5pt, fill: bar-col)[]
      ]
    ]
  ]
}

// Critère Piotroski (sur fond foncé)
#let pio(key, label) = {
  let v = p-details.at(key, default: none)
  let (icon, col) = if v == 1 { ("✓", green-ok) } else if v == 0 { ("✗", red-bad) } else { ("?", muted) }
  block(above: 2.5mm)[
    #stack(
      dir: ltr,
      spacing: 5pt,
      box(width: 14pt, height: 14pt, radius: 7pt, fill: col.lighten(75%))[
        #align(center + horizon)[#text(8pt, weight: "bold", fill: col)[#icon]]
      ],
      align(horizon)[#text(7.5pt, fill: white)[#label]],
    )
  ]
}

// Titre de section (zone blanche)
#let section-hdr(t) = {
  stack(dir: ltr, spacing: 6pt, block(width: 3pt, height: 13pt, fill: teal), align(horizon)[#text(
    8.5pt,
    weight: "bold",
    fill: forest,
  )[#upper(t)]])
  v(2mm)
}

// ══════════════════════════════════════════════════════════
// PAGE 1 — VUE D'ENSEMBLE
// ══════════════════════════════════════════════════════════

// ── En-tête (vert forêt) ─────────────────────────────────
#block(fill: forest, width: 100%, inset: (x: G, top: 1cm, bottom: 0.85cm))[
  #grid(
    columns: (1fr, auto),
    column-gutter: 8pt,
    align: (left + horizon, right + horizon),
    [
      #text(19pt, weight: "bold", fill: white)[#meta.name]
      #linebreak()
      #text(9pt, fill: teal-lt)[
        #meta.symbol
        #if meta.at("exchange", default: none) != none [ — #meta.exchange]
        #if meta.at("country", default: none) != none [ — #meta.country]
      ]
      #linebreak()
      #text(7.5pt, fill: rgb("#7ab5ad"))[
        #meta.at("sector", default: "")
        #if meta.at("industry", default: none) != none [ — #meta.industry]
      ]
    ],
    stack(
      dir: ltr,
      spacing: 7pt,
      if reco-lbl != none {
        block(fill: reco-col, inset: (x: 9pt, y: 7pt), radius: 4pt)[
          #align(center)[
            #text(6pt, fill: white, weight: "bold")[CONSENSUS]
            #v(1.5mm)
            #text(9.5pt, weight: "bold", fill: white)[#reco-lbl]
            #if meta.at("analysts_count", default: none) != none [
              #v(0.5mm)
              #text(6pt, fill: white)[#meta.analysts_count analystes]
            ]
          ]
        ]
      } else { box() },
      block(fill: score-col, inset: (x: 11pt, y: 7pt), radius: 4pt)[
        #align(center)[
          #text(6pt, fill: white, weight: "bold")[SCORE F]
          #v(1.5mm)
          #text(20pt, weight: "bold", fill: white)[#p-score/9]
          #v(0.5mm)
          #text(7.5pt, fill: white)[#score-lbl]
        ]
      ],
    ),
  )
]

// ── Bande KPI marché (menthe) ─────────────────────────────
#block(fill: mint, width: 100%, inset: (x: G, y: 0.55cm))[
  #grid(
    columns: (1.3fr, 1.2fr, 1fr, 1fr, 1fr, 1fr, 0.8fr),
    column-gutter: 6pt,
    [
      #text(6pt, fill: muted, weight: "bold")[COURS (#meta.at("currency", default: "USD"))]
      #v(1mm)
      #text(13pt, weight: "bold", fill: forest)[#fmt-num(market.price)]
    ],
    [
      #text(6pt, fill: muted, weight: "bold")[OBJECTIF ANALYSTES]
      #v(1mm)
      #text(12pt, weight: "bold", fill: teal)[#fmt-num(meta.at("target_price", default: none))]
    ],
    [
      #text(6pt, fill: muted, weight: "bold")[CAPITALISATION]
      #v(1mm)
      #text(11pt, weight: "bold")[#fmt-num(market.market_cap)]
    ],
    [
      #text(6pt, fill: muted, weight: "bold")[VAL. D'ENTREPRISE]
      #v(1mm)
      #text(10pt)[#fmt-num(market.enterprise_value)]
    ],
    [
      #text(6pt, fill: muted, weight: "bold")[+ HAUT 52 SEM.]
      #v(1mm)
      #text(10pt)[#fmt-num(market.at("52w_high"))]
    ],
    [
      #text(6pt, fill: muted, weight: "bold")[+ BAS 52 SEM.]
      #v(1mm)
      #text(10pt)[#fmt-num(market.at("52w_low"))]
    ],
    [
      #text(6pt, fill: muted, weight: "bold")[BÊTA]
      #v(1mm)
      #text(10pt)[#fmt-num(market.beta)]
    ],
  )
]

// ── Section Piotroski | Métriques ─────────────────────────
#grid(
  columns: (0.38fr, 0.62fr),
  fill: (x, _) => if x == 0 { forest } else { white },
  // Piotroski — colonne gauche foncée
  pad(left: G, right: 0.6cm, top: 0.7cm, bottom: 0.7cm)[
    #text(7.5pt, fill: teal-lt, weight: "bold")[ANALYSE DE QUALITÉ — PIOTROSKI F-SCORE]
    #v(2mm)
    #text(26pt, weight: "bold", fill: score-col)[#p-score]
    #text(14pt, fill: white)[/9]
    #v(0.5mm)
    #text(9pt, fill: white)[(#score-lbl)]
    #v(4mm)
    #grid(
      columns: (1fr, 1fr),
      row-gutter: 0pt,
      column-gutter: 6pt,
      pio("f1_roa_positive", "ROA > 0"), pio("f2_cfo_positive", "CFO > 0"),
      pio("f3_delta_roa", "ROA en hausse"), pio("f4_accruals", "Qualité bénéf."),
      pio("f5_delta_leverage", "Levier ↓"), pio("f6_delta_liquidity", "Liquidité ↑"),
      pio("f7_no_dilution", "Pas dilution"), pio("f8_delta_gross_margin", "Marge brute ↑"),
      pio("f9_delta_asset_turnover", "Rotation actifs ↑"),
    )
  ],
  // Métriques clés — colonne droite claire
  pad(left: 0.7cm, right: G, top: 0.7cm, bottom: 0.7cm)[
    #text(7.5pt, fill: muted, weight: "bold")[
      MÉTRIQUES CLÉS — #meta.at("sector", default: "")
    ]
    #v(3mm)
    #grid(
      columns: (1fr, 1fr),
      column-gutter: 12pt,
      [
        #pbar("ROE", data.profitability.roe.value, max-val: 0.35)
        #pbar("ROA", data.profitability.roa.value, max-val: 0.20)
        #pbar("Marge brute", data.profitability.gross_margin.value)
        #pbar("Marge opérat.", data.profitability.operating_margin.value, max-val: 0.35)
        #pbar("Marge nette", data.profitability.net_margin.value, max-val: 0.30)
      ],
      [
        #pbar("Croissance CA", data.growth.revenue_growth.value, max-val: 0.30)
        #pbar("Croissance BPA", data.growth.earnings_growth.value, max-val: 0.30)
        #pbar("Rendement div.", data.dividend.dividend_yield.value, max-val: 0.08)
        #v(3mm)
        #grid(
          columns: (auto, 1fr),
          row-gutter: 2.5pt,
          column-gutter: 6pt,
          text(7.5pt, fill: muted)[PER],
          compare(data.valuation.per.value, data.valuation.per.sector_avg, higher_is_better: false),

          text(7.5pt, fill: muted)[P / Book],
          compare(data.valuation.price_to_book.value, data.valuation.price_to_book.sector_avg, higher_is_better: false),

          text(7.5pt, fill: muted)[EV / EBITDA],
          compare(data.valuation.ev_ebitda.value, data.valuation.ev_ebitda.sector_avg, higher_is_better: false),

          text(7.5pt, fill: muted)[Dette / FP],
          compare(data.health.debt_to_equity.value, data.health.debt_to_equity.sector_avg, higher_is_better: false),
        )
      ],
    )
  ],
)

// ── Tables détaillées ─────────────────────────────────────
#v(3mm)
#pad(x: G)[
  #grid(
    columns: (1fr, 1fr),
    column-gutter: 5mm,
    [
      #section-hdr("Valorisation")
      #metric-tbl((
        metric-row("PER (trailing)", data.valuation, "per", higher_is_better: false),
        metric-row("PER prévisionnel", data.valuation, "forward_per", higher_is_better: false),
        metric-row("PEG", data.valuation, "peg", higher_is_better: false),
        metric-row("Price / Book", data.valuation, "price_to_book", higher_is_better: false),
        metric-row("Price / Sales", data.valuation, "price_to_sales", higher_is_better: false),
        metric-row("EV / EBITDA", data.valuation, "ev_ebitda", higher_is_better: false),
        metric-row("EV / Revenue", data.valuation, "ev_revenue", higher_is_better: false),
      ))
    ],
    [
      #section-hdr("Rentabilité")
      #metric-tbl((
        metric-row("ROE", data.profitability, "roe", is_pct: true),
        metric-row("ROA", data.profitability, "roa", is_pct: true),
        metric-row("Marge brute", data.profitability, "gross_margin", is_pct: true),
        metric-row("Marge opérationnelle", data.profitability, "operating_margin", is_pct: true),
        metric-row("Marge nette", data.profitability, "net_margin", is_pct: true),
      ))
    ],
  )
  #v(3mm)
  #grid(
    columns: (1fr, 1fr, 1fr),
    column-gutter: 5mm,
    [
      #section-hdr("Santé financière")
      #metric-tbl((
        metric-row("Dette / Fonds propres", data.health, "debt_to_equity", higher_is_better: false),
        metric-row("Current Ratio", data.health, "current_ratio"),
        metric-row("Quick Ratio", data.health, "quick_ratio"),
      ))
    ],
    [
      #section-hdr("Croissance")
      #metric-tbl((
        metric-row("Croissance CA", data.growth, "revenue_growth", is_pct: true),
        metric-row("Croissance BPA", data.growth, "earnings_growth", is_pct: true),
      ))
    ],
    [
      #section-hdr("Dividende")
      #metric-tbl((
        metric-row("Rendement", data.dividend, "dividend_yield", is_pct: true),
        metric-row("Taux distribut.", data.dividend, "payout_ratio", is_pct: true),
      ))
    ],
  )
]

// ══════════════════════════════════════════════════════════
// PAGE 2 — HISTORIQUE FINANCIER
// ══════════════════════════════════════════════════════════
#if historical.len() >= 2 {
  pagebreak()

  let hist = if historical.len() > 6 { historical.slice(historical.len() - 6) } else { historical }

  // En-tête page 2
  block(fill: forest, width: 100%, inset: (x: G, y: 0.8cm))[
    #grid(
      columns: (1fr, auto),
      align: (left + horizon, right + horizon),
      [
        #text(13pt, weight: "bold", fill: white)[#meta.name — Historique financier]
        #linebreak()
        #text(8pt, fill: teal-lt)[
          #meta.symbol — Exercices #hist.at(0).year – #hist.at(hist.len() - 1).year
        ]
      ],
      block(fill: teal, inset: (x: 10pt, y: 6pt), radius: 3pt)[
        #text(8pt, fill: white, weight: "bold")[#meta.at("sector", default: "")]
      ],
    )
  ]
  v(4mm)

  // Helpers historique
  let yoy(i, key) = {
    if i == 0 { return na }
    let c = hist.at(i).at(key, default: none)
    let p = hist.at(i - 1).at(key, default: none)
    if c == none or p == none or float(p) == 0 { return na }
    let g = (float(c) - float(p)) / calc.abs(float(p)) * 100
    text(fill: if g >= 0 { teal } else { red-bad }, weight: "bold", size: 7.5pt)[
      #(if g >= 0 { "+" } else { "" })#str(calc.round(g, digits: 1)) %
    ]
  }

  let hist-tbl-header = table.header(
    text(7pt, fill: teal-lt, weight: "bold")[],
    ..hist.map(h => text(7pt, fill: teal-lt, weight: "bold")[#h.year]),
  )

  let hist-fill = (_, y) => if y == 0 { forest } else if calc.even(y) { white } else { mint }
  let hist-cols = (1.7fr,) + hist.map(_ => 1fr)
  let hist-align = (col, _) => if col == 0 { left } else { right }

  pad(x: G)[
    // ── Compte de résultat ──────────────────────────────────
    #section-hdr("Compte de résultat & cash flow")
    #table(
      columns: hist-cols, stroke: none,
      align: hist-align, inset: (x: 4pt, y: 3.5pt), fill: hist-fill,
      hist-tbl-header,
      text(8pt, weight: "bold")[CA],
      ..hist.map(h => text(8pt)[#fmt-num(h.at("revenue", default: none))]),
      text(7.5pt, fill: muted)[  Croissance YoY],
      ..hist.enumerate().map(((i, _)) => yoy(i, "revenue")),
      text(8pt)[Marge brute],
      ..hist.map(h => text(8pt)[#fmt-num(h.at("gross_profit", default: none))]),
      text(8pt)[Rés. opérationnel],
      ..hist.map(h => text(8pt)[#fmt-num(h.at("operating_income", default: none))]),
      text(8pt)[Résultat net],
      ..hist.map(h => {
        let v = h.at("net_income", default: none)
        if v != none and float(v) < 0 { text(8pt, fill: red-bad, weight: "bold")[#fmt-num(v)] } else {
          text(8pt)[#fmt-num(v)]
        }
      }),
      text(8pt)[Cash flow opérationnel],
      ..hist.map(h => text(8pt)[#fmt-num(h.at("operating_cashflow", default: none))]),
      text(8pt)[EBITDA],
      ..hist.map(h => text(8pt)[#fmt-num(h.at("ebitda", default: none))]),
    )

    v(5mm)

    // ── Bilan & Ratios côte à côte ───────────────────────────
    #grid(
      columns: (1fr, 1fr),
      column-gutter: 5mm,
      [
        #section-hdr("Bilan")
        #table(
          columns: (1.5fr,) + hist.map(_ => 1fr),
          stroke: none, align: hist-align,
          inset: (x: 4pt, y: 3.5pt), fill: hist-fill,
          table.header(
            text(7pt, fill: teal-lt, weight: "bold")[],
            ..hist.map(h => text(7pt, fill: teal-lt, weight: "bold")[#h.year]),
          ),
          text(8pt, weight: "bold")[Total actifs],
          ..hist.map(h => text(8pt)[#fmt-num(h.at("total_assets", default: none))]),
          text(8pt)[Dette long terme],
          ..hist.map(h => text(8pt)[#fmt-num(h.at("long_term_debt", default: none))]),
          text(8pt)[Actifs courants],
          ..hist.map(h => text(8pt)[#fmt-num(h.at("current_assets", default: none))]),
          text(8pt)[Passifs courants],
          ..hist.map(h => text(8pt)[#fmt-num(h.at("current_liabilities", default: none))]),
        )
      ],
      [
        #section-hdr("Ratios calculés")
        #table(
          columns: (1.5fr,) + hist.map(_ => 1fr),
          stroke: none, align: hist-align,
          inset: (x: 4pt, y: 3.5pt), fill: hist-fill,
          table.header(
            text(7pt, fill: teal-lt, weight: "bold")[],
            ..hist.map(h => text(7pt, fill: teal-lt, weight: "bold")[#h.year]),
          ),
          text(8pt)[Marge brute %],
          ..hist.map(h => {
            let r = h.at("revenue", default: none)
            let g = h.at("gross_profit", default: none)
            if r != none and g != none and float(r) != 0 { text(8pt)[#fmt-pct(float(g) / float(r))] } else { na }
          }),
          text(8pt)[Marge nette %],
          ..hist.map(h => {
            let r = h.at("revenue", default: none)
            let n = h.at("net_income", default: none)
            if r != none and n != none and float(r) != 0 {
              let v = float(n) / float(r)
              text(8pt, fill: if v < 0 { red-bad } else { ink })[#fmt-pct(v)]
            } else { na }
          }),
          text(8pt)[ROA],
          ..hist.map(h => {
            let ta = h.at("total_assets", default: none)
            let ni = h.at("net_income", default: none)
            if ta != none and ni != none and float(ta) != 0 {
              let v = float(ni) / float(ta)
              text(8pt, fill: if v < 0 { red-bad } else { ink })[#fmt-pct(v)]
            } else { na }
          }),
          text(8pt)[Current Ratio],
          ..hist.map(h => {
            let ca = h.at("current_assets", default: none)
            let cl = h.at("current_liabilities", default: none)
            if ca != none and cl != none and float(cl) != 0 { text(8pt)[#fmt-num(float(ca) / float(cl))] } else { na }
          }),
        )
      ],
    )
  ]
}
