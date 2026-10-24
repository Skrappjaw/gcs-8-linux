#!/usr/bin/env bash
# Install the BOSS GCS-8 UCM profile: 17 named stereo devices whenever a GCS-8 is plugged in.
#
#   sudo ./install.sh            installs into /usr/share/alsa/ucm2
#   UCM2_DIR=/path ./install.sh  installs into another UCM tree (used by the tests)
#
# Exit codes: 0 installed (or already installed), 2 unrecognised USB-Audio.conf, 3 your
# alsa-ucm-conf already supports the GCS-8, so nothing is needed.
set -euo pipefail

UCM2_DIR="${UCM2_DIR:-/usr/share/alsa/ucm2}"
SRC="$(cd "$(dirname "$0")" && pwd)/ucm2/USB-Audio/BOSS"
CONF="$UCM2_DIR/USB-Audio/USB-Audio.conf"
BEGIN="# >>> gcs8-linux: BOSS GCS-8 split devices >>>"
END="# <<< gcs8-linux <<<"

if [[ ! -f "$CONF" ]]; then
    echo "no $CONF; is alsa-ucm-conf installed?" >&2
    exit 2
fi
if [[ ! -w "$CONF" ]]; then
    echo "cannot write $CONF; run with sudo" >&2
    exit 1
fi

# A GCS-8 match outside our own block means alsa-ucm-conf ships support already.
if sed "/^$BEGIN\$/,/^$END\$/d" "$CONF" | grep -q "0582:02d4"; then
    echo "your alsa-ucm-conf already supports the GCS-8 (0582:02d4); nothing to install"
    exit 3
fi
if ! grep -q '^Define.ProfileName ""$' "$CONF"; then
    echo "unrecognised $CONF layout (no 'Define.ProfileName \"\"' line); not touching it" >&2
    exit 2
fi

mkdir -p "$UCM2_DIR/USB-Audio/BOSS"
install -m 0644 "$SRC/GCS-8.conf" "$SRC/GCS-8-HiFi.conf" "$UCM2_DIR/USB-Audio/BOSS/"

if ! grep -q "^$BEGIN\$" "$CONF"; then
    tmp="$(mktemp)"
    awk -v begin="$BEGIN" -v end="$END" '
        { print }
        !done && $0 == "Define.ProfileName \"\"" {
            print begin
            print "If.boss-gcs8 {"
            print "\tCondition {"
            print "\t\tType String"
            print "\t\tHaystack \"${CardComponents}\""
            print "\t\tNeedle \"USB0582:02d4\""
            print "\t}"
            print "\tTrue.Define.ProfileName \"BOSS/GCS-8\""
            print "}"
            print end
            done = 1
        }' "$CONF" > "$tmp"
    cat "$tmp" > "$CONF"   # keep the file's owner and mode
    rm -f "$tmp"
fi

echo "installed the GCS-8 profile into $UCM2_DIR"
echo "next: unplug and replug the GCS-8 (or: systemctl --user restart wireplumber),"
echo "      then pick the card profile 'HiFi' (pavucontrol > Configuration, or wpctl)."
