# AGENTS.md — AI Agent Instructions

This document describes the project structure and provides guidelines for AI coding assistants (Copilot, Claude, Cursor, etc.) working in this repository.

---

## Project Overview

**CCK BALL** is a ZMK firmware configuration for a custom 4×6 split wireless mechanical keyboard with:

- **Microcontroller**: nice!nano v2 (nRF52840 BLE) on both halves
- **Trackball**: PMW3610 optical sensor (right half, SPI0)
- **Encoders**: ALPS EC11 rotary encoders (both halves)
- **RGB**: WS2812 underglow LEDs (left: 29, right: 27, SPI3)
- **Framework**: [ZMK Firmware](https://zmk.dev/) v0.3.0 on Zephyr RTOS v4.1.0
- **Build**: CMake + Ninja, orchestrated by `west` (Zephyr meta-tool)

---

## Repository Layout

```
/
├── config/                    ← USER CONFIG — the only directory you should edit
│   ├── west.yml               # West manifest (pins ZMK to zmkfirmware/zmk@main)
│   ├── zephyr/module.yml      # Registers config/ as a Zephyr board_root module
│   ├── cck_ball.conf          # Global Kconfig (both halves)
│   ├── cck_ball.keymap        # Keymap: layers, behaviors, macros
│   ├── cck_ball.json          # Physical layout for ZMK Studio
│   └── boards/shields/cck_ball/
│       ├── cck_ball.dtsi           # Shared hardware (matrix, kscan, encoders)
│       ├── cck_ball-layouts.dtsi   # ZMK Studio physical layout
│       ├── cck_ball_left.overlay   # Left half: columns, RGB LEDs, encoder
│       ├── cck_ball_right.overlay  # Right half: columns, PMW3610, RGB, encoder, input listener
│       ├── cck_ball_left.conf      # Left-specific Kconfig
│       ├── cck_ball_right.conf     # Right-specific Kconfig
│       ├── cck_ball.zmk.yml        # ZMK shield metadata
│       ├── Kconfig.defconfig       # Split role defaults
│       └── Kconfig.shield          # Shield name detection
│
├── .gitignore                 # Root gitignore (covers west deps + build output)
├── build.yaml                 # GitHub Actions build matrix
├── .github/workflows/build.yml # CI: delegates to ZMK reusable workflow
├── Makefile                   # Local + Docker build orchestration
├── README.md                  # Hardware description and flashing notes
│
├── zmk_cck_ball_left.uf2      # Pre-built left firmware (output of `make left`)
├── zmk_cck_ball_right.uf2     # Pre-built right firmware (output of `make right`)
│
# --- Fetched by `west update`, NOT committed ---
├── zmk/                       # ZMK firmware source (upstream, read-only)
├── zephyr/                    # Zephyr RTOS source (upstream, read-only)
├── modules/                   # Zephyr HAL and library modules (upstream, read-only)
├── optional/                  # Optional Zephyr modules (upstream, read-only)
└── build/                     # CMake/Ninja build output (generated, read-only)
```

---

## Source of Truth

**Only `config/` is owned by this repository.** Everything else (`zmk/`, `zephyr/`, `modules/`, `optional/`, `build/`) is either fetched from upstream or generated at build time. Never suggest editing files outside `config/`.

---

## Key Files and Their Purpose

| File | Purpose |
|---|---|
| `config/cck_ball.keymap` | Keymap: all layers, behaviors, macros. Edit this to change key bindings. |
| `config/cck_ball.conf` | Global Kconfig flags for both halves (BT power, RGB, encoder, pointing, Studio). |
| `config/boards/shields/cck_ball/cck_ball.dtsi` | Shared hardware: GPIO matrix, kscan, encoder nodes. |
| `config/boards/shields/cck_ball/cck_ball_right.overlay` | Right-half hardware: PMW3610 trackball, input listener with scroll/snipe mode. |
| `config/boards/shields/cck_ball/cck_ball_left.overlay` | Left-half hardware: column GPIOs, RGB LEDs, encoder. |
| `config/boards/shields/cck_ball/cck_ball_right.conf` | Right-half Kconfig: SPI, INPUT, EXT_POWER. |
| `config/west.yml` | West manifest: change this to pin ZMK to a specific revision or fork. |

---

## Layers

| Index | Name | Description |
|---|---|---|
| 0 | `En` | Base layer — Colemak-DH (English) |
| 1 | `Sym-en` | Symbols for English layer |
| 2 | `Ru` | Russian QWERTY layout |
| 3 | `Sym-ru` | Symbols for Russian layer; also activates **scroll mode** on trackball |
| 4 | `F_layers` | F-keys, arrows, media |
| 5 | `Numbers` | Numpad, Bluetooth management |

Trackball behavior is layer-conditional (configured in `cck_ball_right.overlay`):
- **Default**: pointer mode (1200 CPI equivalent)
- **Layer 3 active**: scroll mode (XY→scroll, divided by 8)
- **Layer 4 active**: sniper mode (speed divided by 3)

---

## Behaviors and Macros

Defined in `config/cck_ball.keymap`:

| Name | Type | Description |
|---|---|---|
| `hrm_l` / `hrm_r` | Hold-tap | Home-row mods (left/right, 280 ms tapping term) |
| `scroll_vertical_encoder` | Sensor rotation | Vertical scroll via left encoder |
| `scroll_horizontal_encoder` | Sensor rotation | Horizontal scroll via right encoder |
| `layer_en` / `layer_ru` | Macro | Switch base layer to English / Russian |
| `in_en` | Macro | Type one key in English while Russian layer is active |
| `to_en` / `to_ru` | Macro | Transition to English / Russian layer |
| `dash_long` | Macro | Insert em-dash (—) |
| `open_rquote_en` / `close_rquote_en` | Macro | Insert Russian typographic quotes («») in English input mode |

---

## Build Commands

All local builds require a configured west workspace (`make setup` on first run).

```bash
# First-time workspace init
make setup

# Build both halves
make all

# Build individual halves
make left          # → zmk_cck_ball_left.uf2
make right         # → zmk_cck_ball_right.uf2 (includes ZMK Studio)
make settings-reset # → settings_reset.uf2

# Clean build artefacts
make clean
```

Docker targets mirror the above (prefix `docker-`, e.g. `make docker-all`).

CI builds automatically on every push/PR via `.github/workflows/build.yml`.

---

## Flashing

1. Always flash **left half first**, then right half.
2. Put a half into bootloader mode: double-press the reset button → a USB drive appears.
3. Drag the appropriate `.uf2` file onto the drive.
4. For a full settings reset: flash `settings_reset.uf2` on each half first, then re-flash left and right firmware.

---

## Hardware Details

### Matrix

- 5 rows × 12 columns (6 columns per half, right half uses `col-offset = <6>`)
- Diode direction: col2row
- Row GPIOs: defined in `cck_ball.dtsi`
- Column GPIOs: defined in `cck_ball_left.overlay` and `cck_ball_right.overlay`

### PMW3610 Trackball (right half)

- Interface: SPI0 (CS: P0.24, MOSI: P0.17, MISO: P0.20, SCLK: P0.22)
- Motion interrupt: P0.06 (active high, requires pull-down)
- Default CPI: 400 (tuned in `.overlay` with `res-cpi = <400>`)
- Axes: standard X/Y

### RGB LEDs (WS2812)

- Interface: SPI3 (MOSI as data line)
- Left: 29 LEDs, GRB color order
- Right: 27 LEDs, GRB color order

### Encoders (EC11)

- 24 steps per revolution, 12 triggers per rotation
- Left encoder: enabled in `cck_ball_left.overlay`
- Right encoder: enabled in `cck_ball_right.overlay`

---

## Common Modification Patterns

### Add/change a key binding

Edit `config/cck_ball.keymap` — find the appropriate layer block and modify the `bindings` array.

### Add a new macro

1. Define the macro node in the `macros` block in `config/cck_ball.keymap`.
2. Reference it via `&macro_name` in a layer binding.

### Add a new layer

1. Add a layer `#define` at the top of `config/cck_ball.keymap`.
2. Add the layer node to `keymap { ... }`.
3. If the layer needs special trackball behavior, add an entry to `trackball_listener` in `config/boards/shields/cck_ball/cck_ball_right.overlay`.

### Enable/disable a firmware feature

Edit `config/cck_ball.conf` (both halves) or the per-side `.conf` files. Use Kconfig symbols — see [ZMK Kconfig docs](https://zmk.dev/docs/config).

### Change ZMK version

Edit `config/west.yml` — update `revision:` to a commit hash, tag, or branch name, then run `west update`.

---

## Constraints and Cautions

- **Do not edit** files in `zmk/`, `zephyr/`, `modules/`, `optional/`, or `build/` — they are upstream dependencies managed by west.
- DTS overlay files use Devicetree syntax. Property names with `-` are correct (e.g. `col-offset`, `res-cpi`). Do not convert them to underscores.
- ZMK keymap syntax uses `&behavior_name arg` — not C function calls. Bindings are whitespace-separated.
- `CONFIG_ZMK_STUDIO=y` is set for the right half only (it is the BLE central). The left half is peripheral-only.
- The right half (`cck_ball_right`) is the **BLE central** (host-facing). The left half is the **peripheral** (connects to the right half via internal BLE link).
