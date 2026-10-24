# Testing on your system

These steps confirm the split devices work with your distribution and PipeWire or PulseAudio
version. Switching the card profile interrupts audio on the GCS-8 for a moment.

1. Install: `sudo ./install.sh`. Nothing changes yet; the card stays on its current profile.
2. Re-probe the card: unplug and replug the GCS-8, or run `systemctl --user restart wireplumber`.
   `pactl list cards | grep -A12 'BOSS_GCS-8' | grep -i hifi` should list a HiFi profile.
3. Switch to it: `pactl set-card-profile alsa_card.usb-BOSS_GCS-8-01 HiFi`.
   Use the exact profile name from step 2 if it differs.
4. `wpctl status` (or `pactl list sinks short` / `pactl list sources short`) should show 7 GCS-8
   outputs (CH USB … CH SOUND PAD) and 10 GCS-8 inputs (MAIN … CH SOUND PAD).
5. Sound:
   - `pw-play --target <CH 3-AUX sink name> /usr/share/sounds/alsa/Front_Center.wav` plays from the
     GCS-8's CH 3 USB return only.
   - `pw-record --target <CH 2 source name> /tmp/ch2.wav`: speak into the CH 2 mic, press Ctrl-C,
     then play `/tmp/ch2.wav` back.
   - Play into two outputs at once. Both should be heard.
6. Optional: `pw-top` while audio plays; the ERR count on the GCS-8 nodes should stay flat.

To go back: `pactl set-card-profile alsa_card.usb-BOSS_GCS-8-01 pro-audio` (or any other
profile), and `sudo ./uninstall.sh` to remove the profile entirely.

## Reporting

Please open an issue with:
- your distribution, `pipewire --version` (or PulseAudio version), and the `alsa-ucm-conf` version
- which steps passed or failed
- on failure: `journalctl --user -u wireplumber -u pipewire -b | tail -60`

## Expected node names

The device names apps remember are stable across boots. They are built from the card ID and the
channel pair:
- `alsa_output.usb-BOSS_GCS-8-01.HiFi__gcs8_stereo_out_GCS8_0_8_9__sink` (CH 3-AUX)
- `alsa_input.usb-BOSS_GCS-8-01.HiFi__gcs8_stereo_in_GCS8_0_6_7__source` (CH 2)
