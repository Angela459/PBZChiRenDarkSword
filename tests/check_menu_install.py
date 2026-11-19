"""Check menu installation against a temporary game tree, without starting a game."""
from pathlib import Path
import json
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='pbz-menu-install-') as temporary:
    game = Path(temporary) / 'Game with spaces'
    mod = game / 'platform/steam/ue4ss/Mods/PBZChiRenDarkSword'
    menu = game / 'ProjectPBZ/Content/JavaScript/PBZModsMenu'
    (mod / 'Menu').mkdir(parents=True)
    menu.mkdir(parents=True)
    (menu / 'bootstrap.js').write_text('// existing menu', encoding='utf-8')
    manifest = {'version': 1, 'mods': [
        {'id': 'PBZModsMenu', 'entry': 'PBZModsMenu/Mods/PBZModsMenu/main', 'enabled': True},
        {'id': 'PBZChiRenAudioReplace', 'entry': 'PBZModsMenu/Mods/PBZChiRenAudioReplace/main', 'enabled': True},
        {'id': 'OtherMod', 'entry': 'PBZModsMenu/Mods/OtherMod/main', 'enabled': False},
    ]}
    discovered = menu / 'discovered.txt'
    discovered.write_text(json.dumps(manifest), encoding='utf-8')
    for name in ('main.js', 'install.ps1'):
        shutil.copyfile(ROOT / 'Menu' / name, mod / 'Menu' / name)
    command = ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
               '-File', str(mod / 'Menu/install.ps1'), '-ModRoot', str(mod)]
    subprocess.run(command, check=True, capture_output=True)
    installed = menu / 'Mods/PBZChiRenDarkSword/main.js'
    source = installed.read_text(encoding='utf-8')
    prefix = 'const MOD_ROOT = '
    injected = next(line for line in source.splitlines() if line.startswith(prefix))
    assert Path(json.loads(injected[len(prefix):-1])) == mod
    result = json.loads(discovered.read_text(encoding='utf-8'))
    assert result['mods'] == [manifest['mods'][0], manifest['mods'][2],
                              {'id': 'PBZChiRenDarkSword', 'entry': 'PBZModsMenu/Mods/PBZChiRenDarkSword/main', 'enabled': True}]
    assert (mod / 'Menu/install-version.txt').read_text(encoding='utf-8') == 'v1.1\n'
    before = (discovered.read_bytes(), installed.read_bytes())
    subprocess.run(command, check=True, capture_output=True)
    assert before == (discovered.read_bytes(), installed.read_bytes())
    assert (menu / 'bootstrap.js').read_text(encoding='utf-8') == '// existing menu'
    print('PASS automatic menu install: spaces, absolute mod path, preserves other mods/core, idempotent discovery')
