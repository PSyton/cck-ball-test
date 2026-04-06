#!/usr/bin/env python3
"""
Generate SVG keymap diagrams for CCK BALL from cck_ball.json + cck_ball.keymap.

Usage:
    python3 gen_svg.py [--out-dir DIR]

Output:
    layer_0_En.svg, layer_1_Sym.svg, layer_2_Ru.svg, layer_4_F_layers.svg,
    layer_5_Numbers.svg (one file per logical layer)
    keymap_all.svg (all layers stacked)

Notes:
    - Sym-en (layer 1) and Sym-ru (layer 3) are merged into a single visual
      "Sym" layer. in_en macros are treated as plain symbols — the OS-level
      input switching is an implementation detail invisible to the user.
    - Shortcut-L (layer 6) and Shortcut-R (layer 7) are excluded from the
      diagram — they are an implementation detail of Ru layer HRM shortcuts.
    - hmc_sc_l/r are rendered like hrm with hold=Ctrl, hiding the
      "also activates shortcut layer" implementation detail. Same for
      hma_sc_l/r (hold=Alt) and hmg_sc_l/r (hold=GUI).
    - The Ru layer (2) displays Cyrillic letters instead of QWERTY key codes.
"""

import json
import re
import argparse
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCALE = 64          # pixels per 1U
KEY_SIZE = 58       # key square size (px), margin = SCALE - KEY_SIZE
CORNER_R = 6        # rounded corner radius
FONT_MAIN = 13      # main label font size
FONT_HOLD = 10      # hold-action label font size
FONT_TITLE = 18     # layer title font size
PAD_X = 20          # left/right padding
PAD_TOP = 50        # top padding (space for title)
PAD_BOT = 20        # bottom padding

# ---------------------------------------------------------------------------
# Color scheme
# ---------------------------------------------------------------------------
#
# Each logical layer has two color variants:
#   LAYER_COLORS       — saturated: used for title pill + layer-tap/lt/mo keys
#   LAYER_NORMAL_COLORS — desaturated/light: used for ordinary keys on that layer
#
# Visual layer indices (after Sym-ru merge):
#   0 = En        — grey
#   1 = Sym       — blue
#   2 = Ru        — green
#   3 = F_layers  — orange
#   4 = Numbers   — violet
#
# Each tuple: (fill, stroke, text)
LAYER_COLORS = {
    0: ("#d8d8d8", "#888888", "#111111"),   # En — grey (saturated)
    1: ("#b8d4ff", "#4477cc", "#08224a"),   # Sym — blue
    2: ("#b8e8c4", "#389955", "#083018"),   # Ru — green
    3: ("#ffd49a", "#bb6611", "#3a1800"),   # F_layers — orange
    4: ("#d8beff", "#7744bb", "#200044"),   # Numbers — violet
}

LAYER_NORMAL_COLORS = {
    0: ("#f0f0f0", "#aaaaaa", "#222222"),   # En — light grey
    1: ("#e8f2ff", "#99bbee", "#1a3a6c"),   # Sym — very light blue
    2: ("#e4f7e8", "#88cc99", "#1a4a28"),   # Ru — very light green
    3: ("#fff3e0", "#ddaa66", "#4a2800"),   # F_layers — very light orange
    4: ("#f5eeff", "#bb99ee", "#3a1a66"),   # Numbers — very light violet
}

# Non-layer key types → (fill, stroke, text)
COLORS = {
    "trans": ("#f5f5f5", "#cccccc", "#aaaaaa"),   # transparent ▽
    "none":  ("#fafafa", "#dddddd", "#bbbbbb"),   # disabled ✕
}

# Color used for hold-modifier label text (Shift/Ctrl/Alt) on hrm keys
HRM_HOLD_COLOR = "#7a55cc"

# ---------------------------------------------------------------------------
# Keymap label tables
# ---------------------------------------------------------------------------

# Human-readable labels for ZMK key codes
KEY_LABELS = {
    # Letters
    "Q":"Q","W":"W","E":"E","R":"R","T":"T","Y":"Y","U":"U","I":"I","O":"O","P":"P",
    "A":"A","S":"S","D":"D","F":"F","G":"G","H":"H","J":"J","K":"K","L":"L",
    "Z":"Z","X":"X","C":"C","V":"V","B":"B","N":"N","M":"M",
    # Numbers
    "N1":"1","N2":"2","N3":"3","N4":"4","N5":"5","N6":"6","N7":"7","N8":"8","N9":"9","N0":"0",
    "NUMBER_1":"1","NUMBER_2":"2","NUMBER_3":"3","NUMBER_4":"4","NUMBER_5":"5",
    "NUMBER_6":"6","NUMBER_7":"7","NUMBER_8":"8","NUMBER_9":"9","NUMBER_0":"0",
    # Function keys
    "F1":"F1","F2":"F2","F3":"F3","F4":"F4","F5":"F5","F6":"F6",
    "F7":"F7","F8":"F8","F9":"F9","F10":"F10","F11":"F11","F12":"F12",
    # Punctuation / symbols
    "SPACE":"Space","ENTER":"Enter","BACKSPACE":"⌫","DELETE":"Del","TAB":"Tab",
    "ESCAPE":"Esc","ESC":"Esc",
    "MINUS":"-","EQUAL":"=","PLUS":"+",
    "LEFT_BRACKET":"[","RIGHT_BRACKET":"]","LBKT":"[","RBKT":"]",
    "BACKSLASH":"\\","SLASH":"/","GRAVE":"`",
    "SEMICOLON":";","APOS":"'","SINGLE_QUOTE":"'","DOUBLE_QUOTES":"\"",
    "COMMA":",","PERIOD":".","DOT":".",
    "EXCLAMATION":"!","AT_SIGN":"@","HASH":"#","DOLLAR":"$",
    "PERCENT":"%","CARET":"^","AMPERSAND":"&","ASTERISK":"*",
    "LEFT_PARENTHESIS":"(","RIGHT_PARENTHESIS":")",
    "UNDERSCORE":"_","PIPE":"|","TILDE":"~","TILDE2":"~",
    "LESS_THAN":"<","GREATER_THAN":">",
    "LEFT_BRACE":"{","RIGHT_BRACE":"}",
    "QUESTION":"?","COLON":":",
    # Navigation
    "LEFT":"←","RIGHT":"→","UP":"↑","DOWN":"↓",
    "HOME":"Home","END":"End","PAGE_UP":"PgUp","PAGE_DOWN":"PgDn","PG_UP":"PgUp","PG_DN":"PgDn",
    "INSERT":"Ins","INS":"Ins",
    "PRINTSCREEN":"PScr","PSCRN":"PScr",
    # Modifiers
    "LSHIFT":"LShift","RSHIFT":"RShift","LEFT_SHIFT":"LShift","RIGHT_SHIFT":"RShift",
    "LCTRL":"LCtrl","RCTRL":"RCtrl","LEFT_CONTROL":"LCtrl","RIGHT_CONTROL":"RCtrl",
    "LALT":"LAlt","RALT":"RAlt","LEFT_ALT":"LAlt","RIGHT_ALT":"RAlt",
    "LGUI":"LGui","RGUI":"RGui",
    # Media / misc
    "C_VOL_UP":"Vol+","C_VOL_DN":"Vol-",
    "KP_DOT":"Num.","KP_COMMA":"Num,",
    # Soft-off / boot
    "SOFT_OFF":"Off",
}

MOD_LABELS = {
    "LSHIFT":"Shift","RSHIFT":"Shift","LEFT_SHIFT":"Shift","RIGHT_SHIFT":"Shift",
    "LSHFT":"Shift","RSHFT":"Shift",
    "LCTRL":"Ctrl","RCTRL":"Ctrl","LEFT_CONTROL":"Ctrl","RIGHT_CONTROL":"Ctrl",
    "LALT":"Alt","RALT":"AltGr","LEFT_ALT":"Alt","RIGHT_ALT":"AltGr",
    "LGUI":"GUI","RGUI":"GUI","LEFT_GUI":"GUI","RIGHT_GUI":"GUI",
}

# Layer index → display name (used in lt / mo hold labels)
# These are the RAW keymap indices (before Sym-ru merge).
# lt/mo in the keymap always reference original indices.
LAYER_LABELS = {
    0: "En",
    1: "Sym",
    2: "Ru",
    3: "Sym",      # Sym-ru is the same logical layer as Sym-en
    4: "F",
    5: "Num",
}

# Raw layer index → visual display index (after Sym-ru merge)
# Used to look up the correct LAYER_COLORS entry for lt/mo keys.
LAYER_VISUAL_IDX = {
    0: 0,   # En
    1: 1,   # Sym-en → Sym
    2: 2,   # Ru
    3: 1,   # Sym-ru → Sym (same visual layer)
    4: 3,   # F_layers
    5: 4,   # Numbers
}

BT_LABELS = {
    "BT_SEL 0":"BT 1","BT_SEL 1":"BT 2","BT_SEL 2":"BT 3",
    "BT_SEL 3":"BT 4","BT_SEL 4":"BT 5",
    "BT_CLR":"BT Clr","BT_CLR_ALL":"BT ClrAll",
}

# Russian QWERTY mapping: ZMK key code → Cyrillic letter
# Used when rendering layer 2 (Ru) to show actual Russian letters
RU_KEYS = {
    "Q":"Й","W":"Ц","E":"У","R":"К","T":"Е","Y":"Н","U":"Г","I":"Ш","O":"Щ","P":"З",
    "A":"Ф","S":"Ы","D":"В","F":"А","G":"П","H":"Р","J":"О","K":"Л","L":"Д",
    "Z":"Я","X":"Ч","C":"С","V":"М","B":"И","N":"Т","M":"Ь",
    "SEMICOLON":"Ж","APOS":"Э","COMMA":"Б","DOT":"Ю","PERIOD":"Ю",
    "LBKT":"Х","LEFT_BRACKET":"Х",
    "RBKT":"Ъ","RIGHT_BRACKET":"Ъ",
    "GRAVE":"Ё",
}

# ---------------------------------------------------------------------------
# Keymap parser
# ---------------------------------------------------------------------------

def strip_comments(text: str) -> str:
    """Remove C-style // and /* */ comments."""
    text = re.sub(r'//[^\n]*', '', text)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    return text


def expand_defines(text: str) -> str:
    """Expand simple #define NAME VALUE substitutions (integer values only)."""
    defines = {}
    for m in re.finditer(r'^\s*#define\s+(\w+)\s+(\d+)', text, re.MULTILINE):
        defines[m.group(1)] = m.group(2)
    # Replace all occurrences of each defined name with its value.
    # Sort by length descending to avoid partial replacements.
    for name in sorted(defines, key=len, reverse=True):
        text = re.sub(r'\b' + re.escape(name) + r'\b', defines[name], text)
    return text


def parse_combos(path: str) -> list:
    """
    Parse the combos { ... } block and return a list of:
      {"positions": [int, ...], "layer_target": int|None, "binding": str}

    Only layer-activating combos (mo/lt/to) are tracked for visualization.
    """
    text = Path(path).read_text(encoding="utf-8")
    text = strip_comments(text)
    text = expand_defines(text)

    combos_match = re.search(r'combos\s*\{[^}]*compatible\s*=\s*"zmk,combos"\s*;(.*?)\}\s*;', text, re.DOTALL)
    if not combos_match:
        return []

    body = combos_match.group(1)

    combo_pattern = re.compile(
        r'\w[\w-]*\s*\{[^}]*?key-positions\s*=\s*<([^>]+)>[^}]*?bindings\s*=\s*<([^>]+)>',
        re.DOTALL
    )

    result = []
    for m in combo_pattern.finditer(body):
        positions = [int(p) for p in m.group(1).split()]
        binding = m.group(2).strip()
        # Extract layer target if binding is mo/lt/to
        layer_target = None
        lm = re.match(r'&(?:mo|lt|to)\s+(\d+)', binding)
        if lm:
            layer_target = int(lm.group(1))
        result.append({"positions": positions, "layer_target": layer_target, "binding": binding})

    return result


def parse_keymap(path: str) -> dict:
    """
    Returns dict:
      {
        layer_index: {
          "name": str,
          "keys": [ {"tap": str, "hold": str|None, "type": str}, ... ]
                   60 entries, matrix order (row-major, left-right)
        }
      }
    """
    text = Path(path).read_text(encoding="utf-8")
    text = strip_comments(text)
    text = expand_defines(text)

    # Find keymap { ... }
    km_match = re.search(r'keymap\s*\{[^}]*compatible\s*=\s*"zmk,keymap"\s*;(.*)\}\s*;', text, re.DOTALL)
    if not km_match:
        km_match = re.search(r'keymap\s*\{(.*?)\}\s*;?\s*\}', text, re.DOTALL)
    if not km_match:
        raise ValueError("Could not find keymap block")

    km_body = km_match.group(1)

    layer_pattern = re.compile(
        r'(\w[\w-]*)\s*\{[^{]*?bindings\s*=\s*<(.*?)>\s*;',
        re.DOTALL
    )

    layers = {}
    for idx, m in enumerate(layer_pattern.finditer(km_body)):
        name = m.group(1)
        raw = m.group(2).strip()
        keys = parse_bindings(raw, layer_idx=idx)
        layers[idx] = {"name": name, "keys": keys}

    return layers


def tokenize_bindings(raw: str) -> list:
    """Split binding string into individual &behavior ... tokens."""
    tokens = []
    i = 0
    raw = raw.strip()
    while i < len(raw):
        while i < len(raw) and raw[i] in ' \t\n\r':
            i += 1
        if i >= len(raw):
            break
        if raw[i] == '&':
            j = raw.find('&', i + 1)
            token = raw[i:j].strip() if j != -1 else raw[i:].strip()
            tokens.append(token)
            i = j if j != -1 else len(raw)
        else:
            i += 1
    return tokens


def parse_binding(token: str, layer_idx: int = -1) -> dict:
    """
    Parse a single &behavior [args...] token into:
      {
        "tap":        str,
        "hold":       str|None,
        "type":       "normal"|"hrm"|"layer"|"mouse"|"trans"|"none"|"bt",
        "layer_target": int|None   # raw layer index for lt/mo, for color lookup
      }

    layer_idx: current layer index, used to apply RU_KEYS translation for layer 2.
    """
    def key_result(tap, hold=None, ktype="normal", layer_target=None):
        return {"tap": tap, "hold": hold, "type": ktype, "layer_target": layer_target}

    token = token.strip()
    if not token.startswith('&'):
        return key_result("?")

    parts = token[1:].split()
    if not parts:
        return key_result("?")

    behavior = parts[0]
    args = parts[1:]

    def ru(code):
        """Translate key code to Cyrillic if we're in the Ru layer."""
        if layer_idx == 2 and code in RU_KEYS:
            return RU_KEYS[code]
        return KEY_LABELS.get(code, code.replace("_", " "))

    # --- transparent / none ---
    if behavior == "trans":
        return key_result("▽", ktype="trans")
    if behavior == "none":
        return key_result("✕", ktype="none")

    # --- plain keypress ---
    if behavior == "kp":
        code = args[0] if args else "?"
        combo = re.match(r'([LR][CSA])\((.+)\)', code)
        if combo:
            mod_short = {"LC":"Ctrl","RC":"Ctrl","LS":"Shift","RS":"Shift","LA":"Alt","RA":"Alt"}
            mod = mod_short.get(combo.group(1), combo.group(1))
            inner = combo.group(2)
            shifted_symbols = {
                "N1":"!","N2":'"',"N3":"#","N4":"$","N5":"%",
                "N6":"^","N7":"&","N8":"*","N9":"(","N0":")",
                "NUMBER_1":"!","NUMBER_2":'"',"NUMBER_3":"#","NUMBER_4":"$","NUMBER_5":"%",
                "NUMBER_6":"^","NUMBER_7":"&","NUMBER_8":"*","NUMBER_9":"(","NUMBER_0":")",
            }
            # In Sym-ru, Shift+N2="  Shift+N6=:  Shift+N7=?  — resolve to actual symbol
            if mod == "Shift" and inner in shifted_symbols:
                return key_result(shifted_symbols[inner])
            key = KEY_LABELS.get(inner, inner)
            return key_result(f"{mod}+{key}")
        return key_result(ru(code))

    # --- mouse buttons ---
    if behavior == "mkp":
        btn_map = {"LCLK":"L🖱","RCLK":"R🖱","MCLK":"M🖱",
                   "MB1":"L🖱","MB2":"R🖱","MB3":"M🖱"}
        label = btn_map.get(args[0] if args else "", args[0] if args else "🖱")
        return key_result(label, ktype="mouse")

    # --- mouse move / scroll ---
    if behavior in ("mmv", "msc"):
        dir_map = {
            "MOVE_UP":"M↑","MOVE_DOWN":"M↓","MOVE_LEFT":"M←","MOVE_RIGHT":"M→",
            "SCRL_UP":"Sc↑","SCRL_DOWN":"Sc↓","SCRL_LEFT":"Sc←","SCRL_RIGHT":"Sc→",
        }
        label = dir_map.get(args[0] if args else "", args[0] if args else "?")
        return key_result(label)

    # --- bluetooth ---
    if behavior.startswith("bt"):
        full = " ".join(parts[1:])
        label = BT_LABELS.get(full, full if full else behavior)
        return key_result(label, ktype="bt")

    # --- layer-tap (lt): tap = key, hold = layer name ---
    if behavior == "lt":
        layer_num = int(args[0]) if args else 0
        code = args[1] if len(args) > 1 else "?"
        tap_label = ru(code)
        hold_label = LAYER_LABELS.get(layer_num, f"L{layer_num}")
        return key_result(tap_label, hold=hold_label, ktype="layer", layer_target=layer_num)

    # --- momentary layer (mo) ---
    if behavior == "mo":
        layer_num = int(args[0]) if args else 0
        hold_label = LAYER_LABELS.get(layer_num, f"L{layer_num}")
        return key_result(f"[{hold_label}]", ktype="layer", layer_target=layer_num)

    # --- to layer ---
    if behavior in ("to", "tog"):
        layer_num = int(args[0]) if args else 0
        label = LAYER_LABELS.get(layer_num, f"L{layer_num}")
        return key_result(f"→{label}", ktype="layer", layer_target=layer_num)

    # --- home-row mod (hrm_l, hrm_r, mt) ---
    if behavior in ("hrm_l", "hrm_r", "mt"):
        mod = MOD_LABELS.get(args[0], args[0]) if args else "?"
        code = args[1] if len(args) > 1 else "?"
        return key_result(ru(code), hold=mod, ktype="hrm")

    # --- hmc_sc_l / hmc_sc_r: hold = Ctrl, activates shortcut layer (impl detail hidden) ---
    if behavior in ("hmc_sc_l", "hmc_sc_r"):
        code = args[0] if args else "?"
        return key_result(ru(code), hold="Ctrl", ktype="hrm")

    # --- hma_sc_l / hma_sc_r: hold = Alt, activates shortcut layer (impl detail hidden) ---
    if behavior in ("hma_sc_l", "hma_sc_r"):
        code = args[0] if args else "?"
        return key_result(ru(code), hold="Alt", ktype="hrm")

    # --- hmg_sc_l / hmg_sc_r: hold = GUI, activates shortcut layer (impl detail hidden) ---
    if behavior in ("hmg_sc_l", "hmg_sc_r"):
        code = args[0] if args else "?"
        return key_result(ru(code), hold="GUI", ktype="hrm")

    # --- in_en: plain symbol, OS-switch mechanism hidden ---
    if behavior == "in_en":
        code = args[0] if args else "?"
        return key_result(KEY_LABELS.get(code, code))

    # --- macros: all rendered as normal keys ---
    if behavior == "layer_en":
        return key_result("▸ En", ktype="layer", layer_target=0)
    if behavior == "layer_ru":
        return key_result("▸ Ru", ktype="layer", layer_target=2)
    if behavior == "to_en":
        return key_result("→ En", ktype="layer", layer_target=0)
    if behavior == "to_ru":
        return key_result("→ Ru", ktype="layer", layer_target=2)
    if behavior == "dash_long":
        return key_result("—")
    if behavior == "dash_short":
        return key_result("–")
    if behavior == "open_rquote_en":
        return key_result("«")
    if behavior == "close_rquote_en":
        return key_result("»")
    if behavior == "lm":
        layer_num = int(args[0]) if args else 0
        mod = MOD_LABELS.get(args[1], args[1]) if len(args) > 1 else "?"
        hold_label = LAYER_LABELS.get(layer_num, f"L{layer_num}")
        return key_result(mod, hold=hold_label, ktype="hrm")
    if behavior == "soft_off":
        return key_result("Off")

    # --- generic fallback ---
    label = behavior + (" " + " ".join(args) if args else "")
    return key_result(label[:10])


def parse_bindings(raw: str, layer_idx: int = -1) -> list:
    tokens = tokenize_bindings(raw)
    return [parse_binding(t, layer_idx=layer_idx) for t in tokens]


# ---------------------------------------------------------------------------
# Layer merging: Sym-en (1) + Sym-ru (3) → single "Sym" layer
# ---------------------------------------------------------------------------

def merge_sym_layers(layers: dict) -> dict:
    """
    Replace layer 1 (Sym-en) with a merged "Sym" layer that uses Sym-en as
    the canonical source (since both layers produce identical visible symbols).
    Drop layer 3 (Sym-ru) from the output entirely.
    Drop layers 6 (Shortcut-L) and 7 (Shortcut-R) — implementation detail of
    the Ru layer HRM mechanism, not user-visible layers.

    Also renumber output layers to fill the gap: 0, 1, 2, 3, 4
    (original indices 0=En, 1=Sym-en→Sym, 2=Ru, 4=F_layers, 5=Numbers)
    """
    SKIP = {3, 6, 7}  # Sym-ru, Shortcut-L, Shortcut-R
    merged = {}
    display_idx = 0
    for orig_idx in sorted(layers.keys()):
        if orig_idx in SKIP:
            continue
        layer = dict(layers[orig_idx])
        if orig_idx == 1:
            layer = dict(layer)
            layer["name"] = "Sym"
        merged[display_idx] = layer
        display_idx += 1
    return merged


# ---------------------------------------------------------------------------
# SVG generator
# ---------------------------------------------------------------------------

def escape_xml(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def resolve_color(key: dict, current_layer_idx: int = 0) -> tuple:
    """Return (fill, stroke, text_color) for a key."""
    ktype = key.get("type", "normal")
    if ktype == "layer":
        target = key.get("layer_target")
        vis_idx = LAYER_VISUAL_IDX.get(target, 0) if target is not None else 0
        return LAYER_COLORS.get(vis_idx, LAYER_COLORS[0])
    if ktype in COLORS:
        return COLORS[ktype]
    # normal, hrm, mouse, bt — all use the current layer's normal color
    return LAYER_NORMAL_COLORS.get(current_layer_idx, LAYER_NORMAL_COLORS[0])


def key_svg(x_px: float, y_px: float, key: dict, current_layer_idx: int = 0,
            combo_target: int | None = None) -> str:
    """Render a single key as SVG group."""
    fill, stroke, text_color = resolve_color(key, current_layer_idx)
    tap = escape_xml(key["tap"])
    hold = escape_xml(key["hold"]) if key.get("hold") else None
    is_hrm = key.get("type") == "hrm"

    kx = x_px - KEY_SIZE / 2
    ky = y_px - KEY_SIZE / 2

    lines = [
        f'  <rect x="{kx:.1f}" y="{ky:.1f}" width="{KEY_SIZE}" height="{KEY_SIZE}" '
        f'rx="{CORNER_R}" ry="{CORNER_R}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>',
    ]

    # Combo indicator: small filled triangle in bottom-right corner
    if combo_target is not None:
        vis_idx = LAYER_VISUAL_IDX.get(combo_target, 0)
        tri_fill, tri_stroke, tri_text = LAYER_COLORS.get(vis_idx, LAYER_COLORS[0])
        T = 10  # triangle size
        rx = kx + KEY_SIZE
        by = ky + KEY_SIZE
        # right-angle triangle in bottom-right corner
        lines.append(
            f'  <polygon points="{rx - T:.1f},{by:.1f} {rx:.1f},{by - T:.1f} {rx:.1f},{by:.1f}" '
            f'fill="{tri_fill}" stroke="{tri_stroke}" stroke-width="0.5"/>'
        )

    if hold:
        hold_color = HRM_HOLD_COLOR if is_hrm else text_color
        lines.append(
            f'  <text x="{x_px:.1f}" y="{ky + 13:.1f}" '
            f'text-anchor="middle" font-family="sans-serif" font-size="{FONT_HOLD}" '
            f'font-weight="bold" fill="{hold_color}">{hold}</text>'
        )
        lines.append(
            f'  <text x="{x_px:.1f}" y="{y_px + 5:.1f}" '
            f'text-anchor="middle" font-family="sans-serif" font-size="{FONT_MAIN}" '
            f'font-weight="bold" fill="{text_color}">{tap}</text>'
        )
    else:
        lines.append(
            f'  <text x="{x_px:.1f}" y="{y_px + 5:.1f}" '
            f'text-anchor="middle" font-family="sans-serif" font-size="{FONT_MAIN}" '
            f'font-weight="bold" fill="{text_color}">{tap}</text>'
        )

    return "\n".join(lines)


def legend_svg(x: float, y: float) -> str:
    """Render a small color legend at the given position."""
    # Regular key examples per layer
    key_items = [
        (LAYER_NORMAL_COLORS[0], "En"),
        (LAYER_NORMAL_COLORS[1], "Sym"),
        (LAYER_NORMAL_COLORS[2], "Ru"),
        (LAYER_NORMAL_COLORS[3], "F"),
        (LAYER_NORMAL_COLORS[4], "Num"),
    ]
    # Layer-switch key examples
    layer_items = [
        (LAYER_COLORS[1], "→ Sym"),
        (LAYER_COLORS[2], "→ Ru"),
        (LAYER_COLORS[3], "→ F"),
        (LAYER_COLORS[4], "→ Num"),
    ]
    # Other
    other_items = [
        (COLORS["trans"], "transparent"),
        (COLORS["none"],  "disabled"),
    ]

    BOX = 12
    GAP = 8
    TEXT_OFF = 16
    FONT = 10
    parts = []
    cx = x

    def add_item(color_tuple, label):
        nonlocal cx
        fill, stroke, _ = color_tuple
        parts.append(
            f'<rect x="{cx:.0f}" y="{y:.0f}" width="{BOX}" height="{BOX}" '
            f'rx="2" fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{cx + TEXT_OFF:.0f}" y="{y + BOX - 1:.0f}" '
            f'font-family="sans-serif" font-size="{FONT}" fill="#555">{label}</text>'
        )
        cx += TEXT_OFF + len(label) * 6.2 + GAP

    for color, label in key_items:
        add_item(color, label)

    cx += GAP  # extra separator

    for color, label in layer_items:
        add_item(color, label)

    cx += GAP

    # hrm: show box in layer-normal color with purple hold text sample
    parts.append(
        f'<rect x="{cx:.0f}" y="{y:.0f}" width="{BOX}" height="{BOX}" '
        f'rx="2" fill="{LAYER_NORMAL_COLORS[0][0]}" stroke="{LAYER_NORMAL_COLORS[0][1]}" stroke-width="1"/>'
    )
    parts.append(
        f'<text x="{cx + TEXT_OFF:.0f}" y="{y + BOX - 1:.0f}" '
        f'font-family="sans-serif" font-size="{FONT}" fill="#555">key + '
        f'<tspan fill="{HRM_HOLD_COLOR}" font-weight="bold">mod</tspan></text>'
    )
    cx += TEXT_OFF + 9 * 6.2 + GAP

    cx += GAP
    for color, label in other_items:
        add_item(color, label)

    return "\n".join(parts)


def layer_svg(layer: dict, layout: list, layer_idx: int, offset_y: float = 0,
              combos: list = None) -> tuple:
    """
    Returns (svg_content: str, total_height: float, width: float).
    offset_y: vertical offset for stacking multiple layers.
    combos: list of combo dicts from parse_combos(), used to mark combo keys.
    """
    name = layer["name"]
    keys = layer["keys"]

    xs = [k["x"] for k in layout]
    ys = [k["y"] for k in layout]
    max_x = max(xs) + 1.0
    max_y = max(ys) + 1.0

    width = max_x * SCALE + PAD_X * 2
    content_height = max_y * SCALE + PAD_TOP + PAD_BOT

    # Build pos → combo_target map
    combo_map = {}
    for c in (combos or []):
        if c["layer_target"] is not None:
            for pos in c["positions"]:
                combo_map[pos] = c["layer_target"]

    parts = []

    # Title with layer accent color pill — centered
    fill, stroke, tcol = LAYER_COLORS.get(layer_idx, LAYER_COLORS[0])
    pill_h = FONT_TITLE + 8
    pill_w = FONT_TITLE * (len(name) + 4) * 0.62
    pill_y = offset_y + 4
    center_x = width / 2
    parts.append(
        f'<rect x="{center_x - pill_w / 2:.1f}" y="{pill_y:.1f}" width="{pill_w:.0f}" height="{pill_h}" '
        f'rx="5" fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
    )
    parts.append(
        f'<text x="{center_x:.1f}" y="{pill_y + pill_h - 5:.1f}" '
        f'text-anchor="middle" font-family="sans-serif" font-size="{FONT_TITLE}" '
        f'font-weight="bold" fill="{tcol}">{escape_xml(name)}</text>'
    )

    # Keys
    for i, key_pos in enumerate(layout):
        if i >= len(keys):
            break
        key = keys[i]
        px = PAD_X + (key_pos["x"] + 0.5) * SCALE
        py = offset_y + PAD_TOP + (key_pos["y"] + 0.5) * SCALE
        parts.append(key_svg(px, py, key, current_layer_idx=layer_idx,
                             combo_target=combo_map.get(i)))

    return "\n".join(parts), content_height, width


def generate_svg_for_layer(layer: dict, layout: list, layer_idx: int, out_path: str,
                           combos: list = None):
    LEGEND_H = 28
    content, height, width = layer_svg(layer, layout, layer_idx, offset_y=0, combos=combos)
    total_h = height + LEGEND_H
    leg = legend_svg(PAD_X, height + 8)

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{total_h:.0f}" '
        f'viewBox="0 0 {width:.0f} {total_h:.0f}">\n'
        f'<rect width="{width:.0f}" height="{total_h:.0f}" fill="#fafafa"/>\n'
        f'{content}\n'
        f'{leg}\n'
        f'</svg>'
    )
    Path(out_path).write_text(svg, encoding="utf-8")
    print(f"  Written: {out_path}")


def generate_svg_all(layers: dict, layout: list, out_path: str, combos: list = None):
    all_parts = []
    current_y = 0.0
    total_width = 0.0

    for idx in sorted(layers.keys()):
        layer = layers[idx]
        content, height, width = layer_svg(layer, layout, idx, offset_y=current_y, combos=combos)
        all_parts.append(content)
        current_y += height + 30
        total_width = max(total_width, width)

    # Legend at the very bottom
    LEGEND_H = 28
    leg = legend_svg(PAD_X, current_y + 6)
    total_height = current_y + LEGEND_H

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_width:.0f}" height="{total_height:.0f}" '
        f'viewBox="0 0 {total_width:.0f} {total_height:.0f}">\n'
        f'<rect width="{total_width:.0f}" height="{total_height:.0f}" fill="#fafafa"/>\n'
        + "\n".join(all_parts) +
        f'\n{leg}\n'
        '</svg>'
    )
    Path(out_path).write_text(svg, encoding="utf-8")
    print(f"  Written: {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate SVG keymaps for CCK BALL")
    parser.add_argument("--out-dir", default="keymap_svg", help="Output directory (default: keymap_svg)")
    parser.add_argument("--keymap", default=None, help="Path to cck_ball.keymap (default: auto-detect)")
    parser.add_argument("--json", default=None, help="Path to cck_ball.json (default: auto-detect)")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    keymap_path = args.keymap or str(script_dir / "config" / "cck_ball.keymap")
    json_path = args.json or str(script_dir / "config" / "cck_ball.json")
    out_dir = Path(args.out_dir)

    print(f"Keymap:  {keymap_path}")
    print(f"Layout:  {json_path}")
    print(f"Out dir: {out_dir}")

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    layout = data["layouts"]["default_transform"]["layout"]
    print(f"Keys in layout: {len(layout)}")

    raw_layers = parse_keymap(keymap_path)
    print(f"Raw layers found: {sorted(raw_layers.keys())}")
    for idx, layer in raw_layers.items():
        print(f"  Layer {idx}: {layer['name']} — {len(layer['keys'])} keys")

    combos = parse_combos(keymap_path)
    print(f"Combos found: {len(combos)}")

    # Merge Sym-en + Sym-ru into single Sym layer, drop Sym-ru
    layers = merge_sym_layers(raw_layers)
    print(f"Visual layers: {sorted(layers.keys())}")
    for idx, layer in layers.items():
        print(f"  Layer {idx}: {layer['name']}")

    out_dir.mkdir(parents=True, exist_ok=True)

    generate_svg_all(layers, layout, str(out_dir / "keymap_all.svg"), combos=combos)
    print("Done.")


if __name__ == "__main__":
    main()
