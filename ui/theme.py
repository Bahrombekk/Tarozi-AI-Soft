"""Theme colour palettes and accessor helpers.

All colour constants and the dark/light palette dict live here.
CSS generation stays in styles.py.
"""

# Layout
item_height: int = 60
font: str = "Poppins"
font_size: str = "16px"
border_radius: str = "8px"

# Default (light) base colours
hover_color: str = "#ddd"
select_color: str = "#bbb"
bg_color: str = "#f2f3f3"
border_color: str = "#E5E6E8"
text_color: str = "#000A19"
border: str = f"1px solid {border_color}"

# Scroll
scroll_color: str = "#62989F"
scroll_hover_color: str = "#82B8BF"

# Palette keys
DARK: str = "DARK"
LIGHT: str = "LIGHT"
TEXT_COLOR: str = "TEXT_COLOR"
TEXT_BG_COLOR: str = "TEXT_BG_COLOR"
TEXT_COLOR2: str = "TEXT_COLOR2"
BORDER_COLOR: str = "BORDER_COLOR"
HOVER_BORDER: str = "HOVER_BORDER"
HOVER_COLOR: str = "HOVER_COLOR"
HOVER_TAB: str = "HOVER_TAB"
HOVER_TABLE: str = "HOVER_TABLE"
SELECTED_TAB: str = "SELECTED_TAB"
FOCUS_COLOR: str = "FOCUS_COLOR"
SELECT_COLOR: str = "SELECT_COLOR"
BORDER: str = "BORDER"
BG_COLOR: str = "BG_COLOR"
BG_COLOR2: str = "BG_COLOR2"
BG_COLOR3: str = "BG_COLOR3"
BG_ICON_COLOR: str = "BG_ICON_COLOR"

# Palettes
palettes: dict = {
    DARK: {
        TEXT_COLOR: "#F5F5E9",
        TEXT_COLOR2: "#F5F5E9",
        TEXT_BG_COLOR: "#333",
        BG_COLOR: "#000A19",
        BG_COLOR2: "#252B29",
        BG_COLOR3: "#454B49",
        BORDER: "1px solid #454648",
        BORDER_COLOR: "#454648",
        HOVER_BORDER: "#00F07C",
        BG_ICON_COLOR: "#25222D",
        HOVER_TAB: "#444",
        HOVER_TABLE: "#444",
        SELECTED_TAB: "#333",
        SELECT_COLOR: "#555",
    },
    LIGHT: {
        TEXT_COLOR: "#000A19",
        TEXT_COLOR2: "#000A19",
        TEXT_BG_COLOR: "#eee",
        BG_COLOR: "#f2f3f3",
        BG_COLOR2: "#ffffff",
        BG_COLOR3: "#ddd",
        BORDER: "1px solid #C5C6C8",
        BORDER_COLOR: "#C5C6C8",
        HOVER_BORDER: "#00F07C",
        BG_ICON_COLOR: "#E5F2FD",
        HOVER_TAB: "#ddd",
        HOVER_TABLE: "#ddd",
        SELECTED_TAB: "#fff",
        SELECT_COLOR: "#ccc",
    },
}


# ---------- Accessor helpers ----------

def get_border_color(style_name: str) -> str:
    return palettes[style_name][BORDER_COLOR]


def get_hover_color(style_name: str) -> str:
    return palettes[style_name][HOVER_TABLE]


def get_select_color(style_name: str) -> str:
    return palettes[style_name][SELECT_COLOR]


def get_text_color(style_name: str) -> str:
    return palettes[style_name][TEXT_COLOR]


def get_text_bg_color(style_name: str) -> str:
    return palettes[style_name][TEXT_BG_COLOR]


def get_bg_color(style_name: str) -> str:
    return palettes[style_name][BG_COLOR2]
