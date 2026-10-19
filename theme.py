# theme.py
# Krypton's colour themes. The site's styles are written once in the default Blood colours; a theme
# simply swaps those accent colours for its own. "Up" (green) and "down" (red) market colours never
# change, so a price move always means the same thing whatever theme you pick.

THEMES = {
    "Blood": {"accent": "#ff2a3d", "rgb": "255, 42, 61", "deep": "#8b0a1a", "deep2": "#a10d22",
              "light": "#ff8a95", "lighter": "#ffb3ba", "glow1": "150, 0, 20", "glow2": "90, 0, 12",
              "glow3": "70, 0, 10", "aurora": "120, 0, 40"},
    "Inferno": {"accent": "#ff6a1a", "rgb": "255, 106, 26", "deep": "#8a2d00", "deep2": "#b34000",
                "light": "#ffaa70", "lighter": "#ffd0b0", "glow1": "150, 50, 0", "glow2": "100, 20, 0",
                "glow3": "80, 15, 0", "aurora": "140, 30, 0"},
    "Eclipse": {"accent": "#a855f7", "rgb": "168, 85, 247", "deep": "#4c1d95", "deep2": "#6d28d9",
                "light": "#c9a2ff", "lighter": "#e2ccff", "glow1": "70, 20, 140", "glow2": "40, 10, 90",
                "glow3": "35, 5, 70", "aurora": "90, 20, 160"},
    "Abyss": {"accent": "#00c2ff", "rgb": "0, 194, 255", "deep": "#00506e", "deep2": "#006d94",
              "light": "#7fdcff", "lighter": "#bfeeff", "glow1": "0, 70, 120", "glow2": "0, 40, 80",
              "glow3": "0, 30, 60", "aurora": "0, 80, 140"},
}
DEFAULT = "Blood"


def apply(css, name):
    """The site's styles in the chosen theme's colours."""
    if name not in THEMES or name == DEFAULT:
        return css
    base, theme = THEMES[DEFAULT], THEMES[name]
    for key in ("accent", "rgb", "deep", "deep2", "light", "lighter", "glow1", "glow2", "glow3", "aurora"):
        css = css.replace(base[key], theme[key])
    return css.replace("#ff4d5e", theme["accent"]).replace("#ff6b78", theme["light"]).replace("#ff9aa3",
                                                                                            theme["lighter"])
