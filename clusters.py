# clusters.py
# 🧬 Market TEAMS: which markets move together?
#
# For every pair of markets Krypton follows, we compare their daily ups and downs over the last year.
# Markets that keep moving the same way are put in the same TEAM (e.g. oil companies + the oil price).
#
# How it works (simply): we measure how alike each pair's daily moves were (their "correlation":
# +1 = always move the same way, 0 = unrelated). Then the two most alike groups are joined, again
# and again, until the next join would put together markets that are only loosely related.
#
# For people, every link is shown as an easy number instead: "they moved the same direction on
# 78% of days" (two unrelated markets land around 50%).
#
# Pure calculation, no web-page code (see clusters_tab.py for the page).

import numpy as np
import pandas as pd

from markets import SECTOR_OF

TOGETHER = 0.5      # join groups only while their markets' average correlation is at least this
MIN_DAYS = 120      # a market needs this many days of prices to be included

# Friendly team names, from the sector most of the team comes from
TEAM_NAMES = {"Energy": "Oil & energy", "Shipping": "Shipping", "Airlines & logistics": "Travel & freight",
              "Autos": "Car makers", "Defence & aerospace": "Defence", "Insurance & rebuilding": "Insurers",
              "Agriculture & food": "Farm & food", "Metals & mining": "Metals & mining",
              "Semiconductors & tech": "Chips & tech", "Countries & indexes": "World stock markets",
              "Fear & safe havens": "Safe havens", "Utilities": "Power & utilities"}


def daily_moves(prices):
    returns = prices.pct_change(fill_method=None)
    return returns.loc[:, returns.count() >= MIN_DAYS]


def same_direction(moves, a, b):
    """Share of days (when both traded and both moved) that two markets went the same way, in %."""
    both = moves[[a, b]].dropna()
    both = both[(both[a] != 0) & (both[b] != 0)]
    if len(both) < 30:
        return None
    return float((np.sign(both[a]) == np.sign(both[b])).mean() * 100)


def group(corr, threshold=TOGETHER):
    """Keep joining the two most alike groups while they're alike enough. Biggest groups first."""
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
    return sorted([[names[i] for i in g] for g in groups], key=len, reverse=True)


def team_name(sector):
    plain = sector.split(" ", 1)[-1]
    return f"{TEAM_NAMES.get(plain, plain)} team"


def describe(members, corr, moves, changes):
    """Facts about one team, in plain numbers."""
    sub = corr.loc[members, members]
    anchor = sub.mean().idxmax()  # the most typical member: most alike to all the others
    pairs = [same_direction(moves, a, b) for i, a in enumerate(members) for b in members[i + 1:]]
    pairs = [p for p in pairs if p is not None]
    sectors = pd.Series([SECTOR_OF.get(m, "Other") for m in members]).value_counts()
    month = [changes[m]["1 month (%)"] for m in members if changes.get(m, {}).get("1 month (%)") is not None]
    main = sectors.index[0]
    return {"members": sorted(members, key=lambda m: -sub[m].mean()), "anchor": anchor,
            "together": float(np.mean(pairs)) if pairs else None, "main_sector": main,
            "name": team_name(main), "icon": main.split(" ", 1)[0], "mixed": len(sectors) > 1,
            "sectors": sectors.to_dict(), "month": float(np.mean(month)) if month else None}


def build(prices, changes):
    """Everything the Teams page needs."""
    moves = daily_moves(prices)
    corr = moves.corr(min_periods=MIN_DAYS)
    groups = group(corr)
    described = [describe(g, corr, moves, changes) for g in groups if len(g) > 1]
    teams = [t for t in described if len(t["members"]) >= 3]
    pairs = [t for t in described if len(t["members"]) == 2]
    # Two teams from the same sector get told apart by their leading member
    seen = {}
    for t in teams:
        seen[t["name"]] = seen.get(t["name"], 0) + 1
    for t in teams:
        if seen[t["name"]] > 1:
            t["name"] = f"{t['name']} · {t['anchor']}"
    loners = [g[0] for g in groups if len(g) == 1]
    team_of = {m: t for t in teams + pairs for m in t["members"]}
    return {"moves": moves, "corr": corr, "teams": teams, "pairs": pairs, "loners": loners, "team_of": team_of}


def buddies(data, market, limit=5):
    """The markets that move most like this one, with the share of days they moved the same way."""
    corr, moves = data["corr"], data["moves"]
    if market not in corr:
        return []
    closest = corr[market].drop(market).dropna().sort_values(ascending=False).head(limit)
    return [(other, same_direction(moves, market, other)) for other in closest.index]
