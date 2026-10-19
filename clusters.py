# clusters.py
# 🧬 Market CLUSTERS: which markets move together?
#
# For every pair of markets Krypton follows, we measure how alike their daily ups and downs were over
# the last year (the "correlation": +1 = always move the same way, 0 = unrelated, -1 = opposite ways).
# Then markets are grouped step by step: the two most alike groups are joined, again and again, until
# the next join would put together markets that are only loosely related. What's left are CLUSTERS:
# families of markets that tend to rise and fall together.
#
#   - Market-wide clusters: across all sectors (e.g. oil companies + oil prices + Canadian oil sands)
#   - Sub-clusters: the same idea inside each sector (e.g. inside Energy: oil vs. natural gas)
#
# Pure calculation, no web-page code (see clusters_tab.py for the page).

import numpy as np
import pandas as pd

from markets import SECTOR_OF

TOGETHER = 0.5      # join groups only while their markets' average correlation is at least this
MIN_DAYS = 120      # a market needs this many days of prices to be included


def correlations(prices):
    """How alike each pair of markets' daily moves were (pairs compared on days both traded)."""
    returns = prices.pct_change(fill_method=None)
    returns = returns.loc[:, returns.count() >= MIN_DAYS]
    return returns.corr(min_periods=MIN_DAYS)


def group(corr, threshold=TOGETHER):
    """Average-linkage clustering: keep joining the two most alike groups while they're alike enough.
    Returns a list of groups (lists of market names), biggest first."""
    names = list(corr.columns)
    matrix = corr.fillna(0).to_numpy()
    groups = [[i] for i in range(len(names))]
    while len(groups) > 1:
        best, pair = -2.0, None
        for a in range(len(groups)):
            for b in range(a + 1, len(groups)):
                score = matrix[np.ix_(groups[a], groups[b])].mean()
                if score > best:
                    best, pair = score, (a, b)
        if best < threshold:
            break
        a, b = pair
        groups[a] = groups[a] + groups[b]
        del groups[b]
    result = [[names[i] for i in g] for g in groups]
    return sorted(result, key=len, reverse=True)


def describe(members, corr, changes):
    """Facts about one cluster: its 'anchor' (the most typical member), how tightly it moves together,
    which sectors it spans, and how it moved this month."""
    sub = corr.loc[members, members]
    if len(members) > 1:
        off_diagonal = sub.where(~np.eye(len(members), dtype=bool))
        cohesion = float(np.nanmean(off_diagonal.to_numpy()))
        anchor = off_diagonal.mean().idxmax()
    else:
        cohesion, anchor = 1.0, members[0]
    sectors = pd.Series([SECTOR_OF.get(m, "Other") for m in members]).value_counts()
    moves = [changes[m]["1 month (%)"] for m in members if changes.get(m, {}).get("1 month (%)") is not None]
    return {"members": sorted(members, key=lambda m: -sub[m].mean() if len(members) > 1 else 0),
            "anchor": anchor, "cohesion": cohesion, "sectors": sectors.to_dict(),
            "month": float(np.mean(moves)) if moves else None}


def build(prices, changes):
    """Everything the Clusters page needs."""
    from markets import SECTORS
    corr = correlations(prices)
    market_wide = [describe(g, corr, changes) for g in group(corr)]
    sectors = {}
    for sector, markets in SECTORS.items():
        names = [m for m in markets if m in corr.columns]
        if len(names) < 2:
            continue
        inner = corr.loc[names, names]
        off = inner.where(~np.eye(len(names), dtype=bool))
        subs = [describe(g, corr, changes) for g in group(inner)]
        order = [m for s in subs for m in s["members"]]  # cluster order, so related markets sit side by side
        sectors[sector] = {"cohesion": float(np.nanmean(off.to_numpy())), "subclusters": subs,
                           "matrix": corr.loc[order, order]}
    return {"corr": corr, "market_wide": market_wide, "sectors": sectors}
