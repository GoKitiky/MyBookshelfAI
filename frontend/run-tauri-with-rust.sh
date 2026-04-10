#!/usr/bin/env sh
set -eu

probe_pkg_dep() {
  probe_dep_name="$1"
  probe_dep_exists=false
  if command -v pkg-config >/dev/null 2>&1; then
    if pkg-config --exists "$probe_dep_name" 2>/dev/null; then
      probe_dep_exists=true
    fi
  fi
}

COMMAND="${1:-}"
if [ "$COMMAND" != "dev" ] && [ "$COMMAND" != "build" ]; then
  echo "Usage: sh ./run-tauri-with-rust.sh <dev|build>"
  exit 1
fi

if ! command -v cargo >/dev/null 2>&1; then
  if [ -f "$HOME/.cargo/env" ]; then
    # Load rustup-managed PATH in non-login shells (for example, IDE terminals).
    # shellcheck disable=SC1090
    . "$HOME/.cargo/env"
  fi
fi

if ! command -v cargo >/dev/null 2>&1; then
  echo "cargo is not available in PATH. Install Rust with rustup: https://rustup.rs"
  exit 1
fi

probe_pkg_dep "glib-2.0"
glib_exists="$probe_dep_exists"

probe_pkg_dep "gtk+-3.0"
gtk_exists="$probe_dep_exists"

probe_pkg_dep "webkit2gtk-4.1"
webkit_exists="$probe_dep_exists"

probe_pkg_dep "ayatana-appindicator3-0.1"
ayatana_exists="$probe_dep_exists"

missing_deps=""
if [ "$glib_exists" != "true" ]; then
  missing_deps="$missing_deps glib-2.0"
fi
if [ "$gtk_exists" != "true" ]; then
  missing_deps="$missing_deps gtk+-3.0"
fi
if [ "$webkit_exists" != "true" ]; then
  missing_deps="$missing_deps webkit2gtk-4.1"
fi
if [ "$ayatana_exists" != "true" ]; then
  missing_deps="$missing_deps ayatana-appindicator3-0.1"
fi

if [ -n "$missing_deps" ]; then
  missing_deps="$(printf "%s" "$missing_deps" | xargs)"
  echo "Missing Linux system libraries required by Tauri: $missing_deps"
  echo "Install them (Ubuntu/Debian):"
  echo "  sudo apt install -y libglib2.0-dev libwebkit2gtk-4.1-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev patchelf"
  exit 1
fi

npm run desktop:sidecar

tauri "$COMMAND"
