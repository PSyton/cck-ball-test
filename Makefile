# CCK-BALL ZMK Firmware Build Makefile

# Configuration
BOARD := nice_nano_v2
ZMK_CONFIG := /work/config
BUILD_DIR := build
OUTPUT_DIR := /work

# Snippet for ZMK Studio support (right side only)
STUDIO_SNIPPET := studio-rpc-usb-uart

# Docker configuration
DOCKER_IMAGE := zmkfirmware/zmk-build-arm:stable
DOCKER_CMD := docker run --rm -w /work -v $(CURDIR):/work $(DOCKER_IMAGE)

# Docker image for Python-based targets (SVG generation)
PYTHON_DOCKER_CMD := docker run --rm -w /work -v $(CURDIR):/work python:3-slim

.PHONY: all setup left right clean settings-reset keymap-svg help

# Default target: build both halves
all: left right

# Build left half (peripheral)
left:
	west zephyr-export
	west build -p always -s zmk/app -b $(BOARD) -- \
		-DZMK_CONFIG=$(ZMK_CONFIG) \
		-DSHIELD=cck_ball_left
	cp $(BUILD_DIR)/zephyr/zmk.uf2 $(OUTPUT_DIR)/zmk_cck_ball_left.uf2
	@echo "Left half built: $(OUTPUT_DIR)/zmk_cck_ball_left.uf2"

# Build right half (central - with ZMK Studio support)
right:
	west zephyr-export
	west build -p always -s zmk/app -b $(BOARD) -S $(STUDIO_SNIPPET) -- \
		-DZMK_CONFIG=$(ZMK_CONFIG) \
		-DSHIELD=cck_ball_right \
		-DCONFIG_ZMK_STUDIO=y
	cp $(BUILD_DIR)/zephyr/zmk.uf2 $(OUTPUT_DIR)/zmk_cck_ball_right.uf2
	@echo "Right half built: $(OUTPUT_DIR)/zmk_cck_ball_right.uf2"

# Build settings reset firmware
settings-reset:
	west zephyr-export
	west build -p always -s zmk/app -b $(BOARD) -- \
		-DZMK_CONFIG=$(ZMK_CONFIG) \
		-DSHIELD=settings_reset
	cp $(BUILD_DIR)/zephyr/zmk.uf2 $(OUTPUT_DIR)/settings_reset.uf2
	@echo "Settings reset built: $(OUTPUT_DIR)/settings_reset.uf2"

# Clean build directory
clean:
	rm -rf $(BUILD_DIR)
	@echo "Build directory cleaned"

# Initialize west workspace (first time setup)
setup:
	west init -l config
	west update
	west zephyr-export

# Generate SVG keymap diagrams (requires python3)
keymap-svg:
	python3 gen_svg.py --out-dir keymap_svg
	@echo "SVG keymaps written to keymap_svg/"

# ============================================
# Docker Build Targets
# ============================================

docker-all:
	$(DOCKER_CMD) make all

docker-setup:
	$(DOCKER_CMD) make setup

docker-left:
	$(DOCKER_CMD) make left

docker-right:
	$(DOCKER_CMD) make right

docker-settings-reset:
	$(DOCKER_CMD) make settings-reset

docker-clean:
	$(DOCKER_CMD) make clean

docker-keymap-svg:
	$(PYTHON_DOCKER_CMD) python3 gen_svg.py --out-dir keymap_svg
	@echo "SVG keymaps written to keymap_svg/"

.PHONY: docker-all docker-setup docker-left docker-right docker-settings-reset docker-clean docker-keymap-svg

# Help
help:
	@echo "CCK-BALL ZMK Firmware Build"
	@echo ""
	@echo "Docker targets (recommended):"
	@echo "  make docker-setup          - Initialize west workspace"
	@echo "  make docker-all            - Build both halves"
	@echo "  make docker-left           - Build left half"
	@echo "  make docker-right          - Build right half (with ZMK Studio)"
	@echo "  make docker-settings-reset - Build settings reset firmware"
	@echo "  make docker-clean          - Clean build directory"
	@echo "  make docker-keymap-svg     - Generate SVG keymap diagrams (via Docker)"
	@echo ""
	@echo "Local targets (requires west + Zephyr toolchain):"
	@echo "  make setup                 - Initialize west workspace"
	@echo "  make all                   - Build both halves"
	@echo "  make left                  - Build left half"
	@echo "  make right                 - Build right half (with ZMK Studio)"
	@echo "  make settings-reset        - Build settings reset firmware"
	@echo "  make clean                 - Clean build directory"
	@echo "  make keymap-svg            - Generate SVG keymap diagrams (requires python3)"
	@echo ""
	@echo "Output files are placed in the project root directory."
