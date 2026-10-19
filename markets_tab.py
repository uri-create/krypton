# markets_tab.py
# The Markets page:
#   - Sectors: the 9 largest US-listed companies in each sector (3x3), coloured by today's move,
#     with "View all" opening the full list of every company in that sector (sector_page)
#   - Commodities, indices and currencies Krypton watches, coloured by this month's move
#   - Today's biggest movers among large companies
#   - Price history for any company or market
# Company data comes from universe.py (every US-listed company); the rest from markets.py.

import html

import pandas as pd
import streamlit as st
import yfinance as yf

from markets import OTHER_GROUPS, SECTORS, label, ticker
from panels import how_to_read, line_chart, stat_cards, subtitle
from universe import by_sector, money


def _tile_colour(move, full=10):
    """Smooth colour for a move: deeper green the more it rose, deeper red the more it fell
    (full colour at +/- `full` %)."""
    if move is None or pd.isna(move) or abs(move) < full * 0.03:
        return "rgba(255, 255, 255, 0.05)"
    strength = min(abs(move), full) / full
    rgb = "61, 220, 132" if move > 0 else "255, 42, 61"
    return f"rgba({rgb}, {0.10 + 0.55 * strength:.2f})"


def _legend(low, high):
    return (f"<div class='heat-legend'><span>{low}</span><div class='heat-scale'></div><span>{high}</span></div>")


def _company_tile(row):
    move = "n/a" if pd.isna(row.change_pct) else f"{row.change_pct:+.2f}%"
    return (f"<div class='tile' style='background:{_tile_colour(row.change_pct, full=4)}' "
            f"title='{html.escape(row.name)} ({html.escape(row.ticker)}) · {html.escape(str(row.industry))}'>"
            f"<span class='tile-ticker'>{html.escape(row.ticker)}</span>"
            f"<span class='tile-name'>{html.escape(row.name)}</span>"
            f"<span class='tile-cap'>{money(row.market_cap)}</span>"
            f"<span class='tile-move'>{move}</span></div>")


def _sector_grid(universe):
    subtitle("Sectors: the largest companies")
    how_to_read("Every company listed in the US, sorted by sector. Each sector shows its <b>9 largest companies</b> "
                "by market value (biggest first). <b>Green</b> = up today, <b>red</b> = down today. "
                "Press <b>View all</b> to see every company in that sector.")
    st.markdown(_legend("−4% today", "+4% today"), unsafe_allow_html=True)
    sectors = list(by_sector(universe).items())
    for start in range(0, len(sectors), 2):
        for column, (sector, table) in zip(st.columns(2, gap="medium"), sectors[start:start + 2]):
            with column:
                rising = (table["change_pct"] > 0).mean() * 100
                tiles = "".join(_company_tile(row) for row in table.head(9).itertuples())
                st.markdown(
                    f"<div class='heat-sector'><div class='heat-head'><span>{html.escape(sector)}</span>"
                    f"<span class='muted'>{len(table):,} companies · {money(table['market_cap'].sum())} · "
                    f"{rising:.0f}% up today</span></div><div class='grid3'>{tiles}</div></div>",
                    unsafe_allow_html=True)
                if st.button(f"View all {len(table):,} {sector} companies", key=f"view_{sector}",
                             use_container_width=True):
                    st.session_state["sector_view"] = sector
                    st.rerun()  # the whole app, so the full list page opens


def _other_markets(changes):
    subtitle("Commodities, indices and currencies: this month")
    how_to_read("The oil, metals, crops, stock indices and currencies Krypton watches. <b>Green</b> = up over the "
                "last month, <b>red</b> = down.")
    cards = []
    for group in OTHER_GROUPS:
        rows = [(n, changes[n]) for n in SECTORS[group] if changes.get(n, {}).get("1 month (%)") is not None]
        rows.sort(key=lambda r: -r[1]["1 month (%)"])
        tiles = "".join(
            f"<div class='tile' style='background:{_tile_colour(c['1 month (%)'])}' "
            f"title='{html.escape(label(n))}: {c['Price']:,.2f}'>"
            f"<span class='tile-ticker'>{html.escape(ticker(n))}</span>"
            f"<span class='tile-name'>{html.escape(label(n).rsplit(' (', 1)[0])}</span>"
            f"<span class='tile-move'>{c['1 month (%)']:+.1f}%</span></div>" for n, c in rows)
        cards.append(f"<div class='heat-sector'><div class='heat-head'><span>{html.escape(group)}</span></div>"
                     f"<div class='heat-tiles'>{tiles}</div></div>")
    st.markdown(_legend("−10%", "+10%") + f"<div class='heat-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)


def _movers(universe):
    subtitle("Today's biggest movers")
    how_to_read("The largest price changes today among companies worth more than $10 billion.")
    big = universe[(universe["market_cap"] >= 1e10) & universe["change_pct"].notna()
                   & (universe["live"] if "live" in universe else True)]
    if big.empty:
        st.caption("No price changes yet today.")
        return
    ranked = big.sort_values("change_pct")
    up, down = st.columns(2)

    def cards(rows, tone):
        return [{"label": f"{r.name} ({r.ticker})", "value": f"{r.change_pct:+.2f}%", "tone": tone,
                 "explain": f"{r.sector} · worth {money(r.market_cap)} · price ${r.price:,.2f}"}
                for r in rows.itertuples()]
    with up:
        st.markdown("**Biggest gains**")
        stat_cards(cards(ranked.tail(4).iloc[::-1], "good"), per_row=2)
    with down:
        st.markdown("**Biggest losses**")
        stat_cards(cards(ranked.head(4), "bad"), per_row=2)


@st.cache_data(ttl=3600, show_spinner=False)
def _history(symbol):
    data = yf.download(symbol.replace(".", "-"), period="1y", progress=False, auto_adjust=True)["Close"]
    return data.squeeze("columns") if isinstance(data, pd.DataFrame) else data


def _explorer(universe, prices):
    subtitle("Price history")
    how_to_read("Search any US-listed company, or one of the commodities, indices and currencies Krypton watches.")
    companies = [f"{r.name} ({r.ticker})" for r in universe.itertuples()] if universe is not None else []
    others = [label(n) for g in OTHER_GROUPS for n in SECTORS[g] if n in prices.columns]
    options = companies + others
    if not options:
        return
    choice = st.selectbox("Company or market", options, index=0, label_visibility="collapsed")
    if choice in others:
        name = next(n for g in OTHER_GROUPS for n in SECTORS[g] if label(n) == choice)
        series = prices[name]
    else:
        try:
            series = _history(choice.rsplit("(", 1)[1].rstrip(")"))
        except Exception:
            st.caption("Couldn't load this price history right now.")
            return
    line_chart(series, f"{choice}: daily price, last 12 months", "Price", colour="#ffb000", height=340,
               explain="The price at the end of each trading day over the last year.")


def markets_tab(state):
    st.markdown("### Markets")
    universe = state.get("universe")
    if universe is not None and not universe.empty:
        st.markdown(f"<div class='lead'>{len(universe):,} US-listed companies worth "
                    f"{money(universe['market_cap'].sum())} in total, plus the commodities, indices and currencies "
                    "Krypton watches.</div>", unsafe_allow_html=True)
        _sector_grid(universe)
        _movers(universe)
    else:
        st.warning("The full company list couldn't be loaded right now. Please try again in a few minutes.")
    _other_markets(state["changes"])
    _explorer(universe, state["prices"])


# ===========================================================================
# THE FULL LIST PAGE ("View all")
# ===========================================================================
def sector_page(state):
    universe = state.get("universe")
    if st.button("← Back to Markets"):
        st.session_state.pop("sector_view", None)
        st.session_state["return_tab"] = "Markets"  # reopen the Markets tab, not the first one
        st.rerun()
    if universe is None or universe.empty:
        st.warning("The company list isn't available right now.")
        return
    sectors = by_sector(universe)
    names = list(sectors)
    current = st.session_state.get("sector_view")
    if current not in sectors:
        current = names[0]
    picked = st.selectbox("Sector", names, index=names.index(current))
    if picked != current:
        st.session_state["sector_view"] = picked
        st.rerun()
    table = sectors[picked]

    st.markdown(f"### {picked}")
    biggest = table.iloc[0]
    stat_cards([
        {"label": "Companies", "value": f"{len(table):,}", "explain": "US-listed companies in this sector."},
        {"label": "Total market value", "value": money(table["market_cap"].sum()),
         "explain": "All of them added together."},
        {"label": "Up today", "value": f"{(table['change_pct'] > 0).mean() * 100:.0f}%",
         "explain": "Share of the sector's companies whose price is higher today."},
        {"label": "Largest company", "value": biggest["ticker"],
         "explain": f"{biggest['name']}, worth {money(biggest['market_cap'])}."},
    ], per_row=4)

    search = st.text_input("Search by name, ticker or industry", placeholder="e.g. bank, NVDA, semiconductors")
    shown = table
    if search.strip():
        q = search.strip().lower()
        shown = table[table["name"].str.lower().str.contains(q, regex=False)
                      | table["ticker"].str.lower().str.contains(q, regex=False)
                      | table["industry"].str.lower().str.contains(q, regex=False)]
    view = pd.DataFrame({
        "Rank": shown.index + 1, "Company": shown["name"], "Ticker": shown["ticker"],
        "Market cap ($B)": shown["market_cap"] / 1e9, "Price ($)": shown["price"], "Today (%)": shown["change_pct"],
        "Industry": shown["industry"], "Country": shown["country"],
        "Price as of": shown["live"].map({True: "Live", False: "Last close"}) if "live" in shown else "Last close"})
    st.caption(f"Showing {len(view):,} of {len(table):,} companies, largest first. Click a column title to sort.")
    st.dataframe(
        view, hide_index=True, width="stretch", height=640,
        column_config={
            "Rank": st.column_config.NumberColumn(width="small"),
            "Market cap ($B)": st.column_config.NumberColumn(format="%.1f"),
            "Price ($)": st.column_config.NumberColumn(format="%.2f"),
            "Today (%)": st.column_config.NumberColumn(format="%+.2f"),
        })
    st.caption("Prices: live from Yahoo Finance for the 1,000 largest companies (refreshed every 15 minutes, "
               "may be up to 15 minutes delayed); the last closing price for smaller ones. Company list and sizes: "
               "Nasdaq stock screener. Sectors: GICS (S&P index members) or Nasdaq's classification.")
