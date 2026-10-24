# BOSS GIGCASTER 8 (GCS-8) on Linux: split stereo devices

ALSA UCM profile for the BOSS GIGCASTER 8. Splits channel pairs into named stereo devices for easy
selection in apps.

On Windows, the BOSS GCS-8 driver shows each channel pair as its own stereo device: "CH USB",
"CH 3-AUX", "CH 2" and so on. On Linux the GCS-8 is class compliant, so it shows up as one
14-channel output and one 20-channel input, and apps can't pick a pair by name.

This is an ALSA UCM profile that gives Linux the same split. Once installed, plugging in a GCS-8
gives every app 7 named stereo outputs and 10 named stereo inputs. It works with PipeWire and
PulseAudio, needs no background service, and creates no devices while the GCS-8 is unplugged.

## Devices

| Outputs (to the GCS-8) | Channels | Inputs (from the GCS-8) | Channels |
|---|---|---|---|
| CH USB | 1/2 | MAIN | 1/2 |
| MAIN-AUX | 3/4 | MONITOR | 3/4 |
| CH 1-AUX | 5/6 | CH 1 | 5/6 |
| CH 2-AUX | 7/8 | CH 2 | 7/8 |
| CH 3-AUX | 9/10 | CH 3 | 9/10 |
| CH 4-AUX | 11/12 | CH 4 | 11/12 |
| CH SOUND PAD | 13/14 | CH USB | 13/14 |
| | | CH MOBILE | 15/16 |
| | | CH BLUETOOTH | 17/18 |
| | | CH SOUND PAD | 19/20 |

The names and order come from the BOSS Windows driver (`RDIF1240.INF`). CH USB is the default
output and MAIN the default input.

The card also keeps a **Direct** profile that opens all 14/20 channels raw, for DAWs, and
PipeWire's own **Pro Audio** profile is still there.

## Install

Requires `alsa-ucm-conf` (installed on almost every desktop distribution).

```
git clone https://github.com/Skrappjaw/gcs-8-linux.git
cd gcs-8-linux
sudo ./install.sh
```

Then unplug and replug the GCS-8, and choose the card profile **HiFi**:
- pavucontrol → Configuration → GCS-8 → "HiFi" (or "Default"), or
- `pactl set-card-profile alsa_card.usb-BOSS_GCS-8-01 HiFi`

The installer:
- copies `ucm2/USB-Audio/BOSS/GCS-8.conf` and `GCS-8-HiFi.conf` into `/usr/share/alsa/ucm2/USB-Audio/BOSS/`
- adds one marked block to `/usr/share/alsa/ucm2/USB-Audio/USB-Audio.conf` that matches the GCS-8's
  USB ID (`0582:02d4`)
- does nothing (exit 3) if your `alsa-ucm-conf` already supports the GCS-8

An `alsa-ucm-conf` package update replaces `USB-Audio.conf` and drops the block. Run
`sudo ./install.sh` again after one, until the profile ships in `alsa-ucm-conf` itself.

## Uninstall

```
sudo ./uninstall.sh
```

This removes the two files and the block, leaving `USB-Audio.conf` exactly as it was. Switch the
card back to "Pro Audio" or another profile afterwards.

## How it works

The profile uses UCM's `SplitPCM` macros, the same mechanism `alsa-ucm-conf` uses for the Roland
Bridge Cast and Arturia MiniFuse:
- **PipeWire 1.4 and newer** do the split natively.
- **Older PipeWire, and PulseAudio,** use alsa-lib's `dshare`/`dsnoop` plugins.

The GCS-8 runs at 48 kHz in 32-bit float only, so the split runs at 48 kHz/`FLOAT_LE`.

## Status

- **Parses** against a real GCS-8 with alsa-lib 1.2.11 and alsa-ucm-conf 1.2.10 (Ubuntu 24.04 / Mint 22).
- **Audio:** confirmed with PipeWire 1.0.5, the alsa-lib split path, on 2026-10-24.
- **Upstream:** submission to `alsa-ucm-conf` is planned.

Reports from other distributions and PipeWire versions are welcome. `docs/testing.md` has the
steps and what to include in an issue.

## Licence

BSD 3-Clause, the same as alsa-ucm-conf. See `LICENSE`.

## Development

```
python3 tools/gen_hifi.py > ucm2/USB-Audio/BOSS/GCS-8-HiFi.conf   # regenerate from the channel table
python3 -m pytest -q                                              # checks; the live one needs a GCS-8
```

The live test parses the profile with `alsaucm` against a plugged-in GCS-8, using a private copy of
the UCM tree. It needs no root and doesn't touch audio.
