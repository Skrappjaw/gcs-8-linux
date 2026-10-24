#!/usr/bin/env bash
# Remove what install.sh added, leaving USB-Audio.conf exactly as it was before.
#
#   sudo ./uninstall.sh
#   UCM2_DIR=/path ./uninstall.sh
set -euo pipefail

UCM2_DIR="${UCM2_DIR:-/usr/share/alsa/ucm2}"
CONF="$UCM2_DIR/USB-Audio/USB-Audio.conf"
BEGIN="# >>> gcs8-linux: BOSS GCS-8 split devices >>>"
END="# <<< gcs8-linux <<<"

if [[ -f "$CONF" ]] && grep -q "^$BEGIN\$" "$CONF"; then
    if [[ ! -w "$CONF" ]]; then
        echo "cannot write $CONF; run with sudo" >&2
        exit 1
    fi
    tmp="$(mktemp)"
    sed "/^$BEGIN\$/,/^$END\$/d" "$CONF" > "$tmp"
    cat "$tmp" > "$CONF"
    rm -f "$tmp"
fi
rm -f "$UCM2_DIR/USB-Audio/BOSS/GCS-8.conf" "$UCM2_DIR/USB-Audio/BOSS/GCS-8-HiFi.conf"
rmdir "$UCM2_DIR/USB-Audio/BOSS" 2>/dev/null || true   # only if empty; upstream keeps BOSS/Katana here

echo "removed the GCS-8 profile from $UCM2_DIR"
echo "next: replug the GCS-8 (or: systemctl --user restart wireplumber) and pick 'Pro Audio' again."
