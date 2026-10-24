"""Checks for the GCS-8 UCM profile and its installer.

Static checks run anywhere. The live check parses the profile with alsaucm against a GCS-8 that is
plugged in, using a private copy of the system UCM tree; it reads the card's control interface only,
so audio is never interrupted and no root is needed.
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import gen_hifi

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "ucm2" / "USB-Audio" / "BOSS"
SYSTEM_UCM2 = Path("/usr/share/alsa/ucm2")


def hifi():
    return (PROFILE / "GCS-8-HiFi.conf").read_text()


# --- the channel table ---------------------------------------------------------

def test_table_matches_windows_driver():
    outs = [(p.aux, p.name) for p in gen_hifi.PAIRS if p.direction == "Playback"]
    ins = [(p.aux, p.name) for p in gen_hifi.PAIRS if p.direction == "Capture"]
    assert outs == [(0, "CH USB"), (2, "MAIN-AUX"), (4, "CH 1-AUX"), (6, "CH 2-AUX"), (8, "CH 3-AUX"),
                    (10, "CH 4-AUX"), (12, "CH SOUND PAD")]
    assert ins == [(0, "MAIN"), (2, "MONITOR"), (4, "CH 1"), (6, "CH 2"), (8, "CH 3"), (10, "CH 4"),
                   (12, "CH USB"), (14, "CH MOBILE"), (16, "CH BLUETOOTH"), (18, "CH SOUND PAD")]


def test_pairs_cover_every_hardware_channel_once():
    for direction, total in (("Playback", gen_hifi.HW_CHANNELS["Playback"]),
                             ("Capture", gen_hifi.HW_CHANNELS["Capture"])):
        used = sorted(c for p in gen_hifi.PAIRS if p.direction == direction for c in (p.aux, p.aux + 1))
        assert used == list(range(total)), direction
    assert gen_hifi.HW_CHANNELS == {"Playback": 14, "Capture": 20}


# --- the generated profile -----------------------------------------------------

def test_committed_profile_matches_generator():
    assert hifi() == gen_hifi.render(), "run: python3 tools/gen_hifi.py > ucm2/USB-Audio/BOSS/GCS-8-HiFi.conf"


def test_profile_has_17_devices_with_driver_names():
    text = hifi()
    devices = re.findall(r'SectionDevice\."(Line\d+)" \{\n\tComment "([^"]+)"', text)
    assert len(devices) == 17
    assert [n for n, _ in devices] == [f"Line{i}" for i in range(1, 18)]
    assert devices[0][1] == "CH USB" and devices[7][1] == "MAIN"


def test_split_pcms_use_the_cards_only_format():
    # The GCS-8 runs FLOAT_LE at 48 kHz only; the macro's S16_LE default would not open.
    text = hifi()
    assert text.count("Format FLOAT_LE") == 2
    assert "S16_LE" not in text and "S32_LE" not in text


def test_every_split_device_names_pcm_device_0():
    # alsa-ucm-conf 1.2.10's SplitPCMDevice reads ${var:__Device} without a default, so leaving
    # Device out fails to parse on Ubuntu 24.04 / Mint 22. Passing it is valid on every version.
    assert hifi().count("\t\tDevice 0\n") == 17


def test_hw_channel_positions_match_hw_channel_count():
    for block in re.findall(r"SplitPCM \{(.*?)\n\t\t\}", hifi(), re.S):
        hw = int(re.search(r"HWChannels (\d+)", block).group(1))
        assert len(re.findall(r"HWChannelPos\d+ ", block)) == hw


def test_card_file_offers_hifi_and_direct():
    card = (PROFILE / "GCS-8.conf").read_text()
    assert 'SectionUseCase."HiFi"' in card and '"/USB-Audio/BOSS/GCS-8-HiFi.conf"' in card
    assert "Define.DirectPlaybackChannels 14" in card and "Define.DirectCaptureChannels 20" in card
    assert '"/common/direct.conf"' in card


# --- installer -----------------------------------------------------------------

USB_AUDIO_STUB = 'Syntax 6\n\nDefine.ProfileName ""\nDefine.MixerRemap ""\n\nIf.inc {\n\tCondition {}\n}\n'


@pytest.fixture
def fake_ucm2(tmp_path):
    d = tmp_path / "ucm2" / "USB-Audio"
    d.mkdir(parents=True)
    (d / "USB-Audio.conf").write_text(USB_AUDIO_STUB)
    return tmp_path / "ucm2"


def run_script(name, ucm2, *args):
    return subprocess.run(["bash", str(ROOT / name), *args], env={"UCM2_DIR": str(ucm2), "PATH": "/usr/bin:/bin"},
                          capture_output=True, text=True)


def test_install_copies_profile_and_adds_one_match(fake_ucm2):
    r = run_script("install.sh", fake_ucm2)
    assert r.returncode == 0, r.stderr
    conf = (fake_ucm2 / "USB-Audio" / "USB-Audio.conf").read_text()
    assert conf.count('Needle "USB0582:02d4"') == 1
    assert conf.index('Define.ProfileName ""') < conf.index("If.boss-gcs8")
    assert (fake_ucm2 / "USB-Audio" / "BOSS" / "GCS-8-HiFi.conf").read_text() == hifi()
    assert run_script("install.sh", fake_ucm2).returncode == 0  # idempotent
    conf = (fake_ucm2 / "USB-Audio" / "USB-Audio.conf").read_text()
    assert conf.count('Needle "USB0582:02d4"') == 1


def test_uninstall_restores_original_file(fake_ucm2):
    run_script("install.sh", fake_ucm2)
    r = run_script("uninstall.sh", fake_ucm2)
    assert r.returncode == 0, r.stderr
    assert (fake_ucm2 / "USB-Audio" / "USB-Audio.conf").read_text() == USB_AUDIO_STUB
    assert not (fake_ucm2 / "USB-Audio" / "BOSS" / "GCS-8.conf").exists()


def test_install_stands_down_when_upstream_already_supports_it(fake_ucm2):
    conf = fake_ucm2 / "USB-Audio" / "USB-Audio.conf"
    conf.write_text(USB_AUDIO_STUB + "# 0582:02d4 BOSS GCS-8\n")
    r = run_script("install.sh", fake_ucm2)
    assert r.returncode == 3 and "already" in r.stdout + r.stderr
    assert not (fake_ucm2 / "USB-Audio" / "BOSS").exists()


def test_install_refuses_unknown_layout(fake_ucm2):
    (fake_ucm2 / "USB-Audio" / "USB-Audio.conf").write_text("Syntax 6\n")
    r = run_script("install.sh", fake_ucm2)
    assert r.returncode == 2
    assert (fake_ucm2 / "USB-Audio" / "USB-Audio.conf").read_text() == "Syntax 6\n"


# --- live parse against the real card ------------------------------------------

def gcs8_card():
    for usbid in Path("/proc/asound").glob("card*/usbid"):
        if usbid.read_text().strip() == "0582:02d4":
            return (usbid.parent / "id").read_text().strip()
    return None


@pytest.mark.skipif(not shutil.which("alsaucm") or not SYSTEM_UCM2.exists() or gcs8_card() is None,
                    reason="needs alsaucm, the system UCM tree and a GCS-8 plugged in")
def test_alsaucm_parses_profile_on_real_card(tmp_path):
    tree = tmp_path / "ucm2"
    shutil.copytree(SYSTEM_UCM2, tree, symlinks=True)
    r = run_script("install.sh", tree)
    assert r.returncode == 0, r.stderr
    env = {"ALSA_CONFIG_UCM2": str(tree), "PATH": "/usr/bin:/bin"}
    out = subprocess.run(["alsaucm", "-c", f"hw:{gcs8_card()}", "dump", "text"], env=env,
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "Verb.HiFi {" in out.stdout and "Verb.Direct {" in out.stdout
    assert len(re.findall(r"Device\.Line\d+ \{", out.stdout)) == 17
    # every device resolves to its own channel pair on the split PCM, e.g. CH 2-AUX -> out 6,7
    card = gcs8_card()
    # alsaucm quotes only values that contain spaces (Comment MAIN, Comment "CH 1")
    found = re.findall(r'Comment "?([^"\n]+?)"?\n\t\tValues \{.*?(Playback|Capture)PCM "_ucm\d+\.([^"]+)"',
                       out.stdout.split("Verb.Direct")[0], re.S)
    want = [(p.name, p.direction, f"{gen_hifi.PCM_NAME[p.direction]}:{card},0,{p.aux},{p.aux + 1}")
            for p in gen_hifi.PAIRS]
    assert sorted(found) == sorted(want)
