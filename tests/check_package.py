"""Check install ZIP contents and bundled WAV checksums without starting the game."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import zipfile

audio_names = ('charge_stage_1.wav', 'charge_stage_2.wav', 'charge_stage_3.wav',
               'ground_impact.wav', 'full_charge_hit_1.wav', 'full_charge_hit_2.wav')
lua_files = ('Scripts/main.lua', 'enabled.txt', 'README.md', 'audio-manifest.json',
             'PBZChiRenDarkSword.config.json', 'PBZChiRenDarkSword.modsmenu.json',
             'Menu/main.js', 'Menu/install.ps1') + tuple('Audio/' + name for name in audio_names)
native_files = ('dlls/main.dll', 'enabled.txt')

with tempfile.TemporaryDirectory(prefix='pbz-native-package-') as temp:
    root = Path(temp) / 'Mods'
    with zipfile.ZipFile(sys.argv[1]) as archive:
        assert archive.testzip() is None
        names = set(archive.namelist())
        expected = {'PBZChiRenDarkSword/' + name for name in lua_files}
        expected.update('PBZChiRenNativeAudio/' + name for name in native_files)
        assert names == expected, names ^ expected
        assert not any('AudioHost' in name or '/Runtime/' in name or '/tests/' in name for name in names)
        archive.extractall(root)

    lua_mod = root / 'PBZChiRenDarkSword'
    native_mod = root / 'PBZChiRenNativeAudio'
    assert (native_mod / 'dlls/main.dll').stat().st_size > 0
    assert (native_mod / 'enabled.txt').exists()
    for entry in json.loads((lua_mod / 'audio-manifest.json').read_text(encoding='utf-8')):
        audio = lua_mod / entry['wav']
        assert hashlib.sha256(audio.read_bytes()).hexdigest() == entry['sha256']

print('PASS install ZIP contains both UE4SS mods and all checksum-verified WAV files')
