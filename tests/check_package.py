"""Extract the install ZIP and run the real Lua -> PowerShell -> host startup.

Only Unreal discovery is mocked. Uses real files and bundled WAV loading,
but never sends play commands, so user audio is not auditioned.
"""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import time
import zipfile

from lupa.lua54 import LuaRuntime


def wait_for(condition):
    end = time.monotonic() + 10
    while time.monotonic() < end:
        if condition():
            return
        time.sleep(.05)
    raise AssertionError('Timeout waiting for native host')


with tempfile.TemporaryDirectory(prefix='pbz-clean-install-') as temp:
    mods = Path(temp) / 'Mods with spaces'
    with zipfile.ZipFile(sys.argv[1]) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        expected={'Scripts/main.lua','AudioHost.exe','enabled.txt','README.md','audio-manifest.json',
                  'PBZChiRenDarkSword.config.json','PBZChiRenDarkSword.modsmenu.json'}
        expected.update('Audio/'+name for name in ('1_10.wav','2_02.wav','3_09.wav','4_01.wav','5_12.wav','6_11.wav'))
        assert set(names)=={'PBZChiRenDarkSword/'+name for name in expected}
        assert not any('/Runtime/' in n or '/Menu/' in n or '/tests/' in n for n in names)
        assert 'PBZChiRenDarkSword/enabled.txt' in names
        archive.extractall(mods)
    root = mods / 'PBZChiRenDarkSword'
    assert not (root / 'Runtime').exists()
    for entry in json.loads((root / 'audio-manifest.json').read_text(encoding='utf-8')):
        assert hashlib.sha256((root / entry['wav']).read_bytes()).hexdigest() == entry['sha256']

    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('''
        print=function() end
        LoopInGameThreadWithDelay=function(ms,fn) assert(ms==50);step=fn end
        FindAllOf=function() return {} end
    ''')
    script = root / 'Scripts/main.lua'
    lua.execute(script.read_text(encoding='utf-8'), name='@' + str(script))
    session = None
    try:
        lua.globals().step()
        ipc = root / 'Runtime'
        assert ipc.is_dir()
        session = (ipc / 'heartbeat.txt').read_text().split('|')[0]
        ready = ipc / 'ready.txt'
        wait_for(ready.exists)
        assert ready.read_text().startswith(session + '|ready|')
        lua.globals().step()
        logs = list(ipc.glob('run-*.log'))
        assert len(logs) == 1
        log = logs[0].read_text()
        assert 'HOST_READY' in log and 'IPC_WRITE_RETRY' not in log, log
        print('PASS clean ZIP without menu, Runtime or mods.txt creates its directory and starts the real host from a path with spaces')
        (root / 'PBZChiRenDarkSword.config.json').write_text('{"Enabled":false}\n', encoding='utf-8')
        for _ in range(5):
            lua.globals().step()
        assert 'ORIGINAL menu off' in logs[0].read_text()
        print('PASS actual mod-local JSON changes stop replacement without JavaScript or the legacy ~mods config')
    finally:
        if session:
            (ipc / 'command.txt').write_text(session + '|1|quit\n', encoding='ascii')
            host_log = ipc / ('host-' + session + '.log')
            wait_for(lambda: host_log.exists() and 'EXIT' in host_log.read_text())
            assert 'ERROR' not in host_log.read_text()
            assert 'PLAY ' not in host_log.read_text()
            # EXIT is logged before finally closes native handles and the process exits.
            def remove_exited_host():
                try:
                    (root / 'AudioHost.exe').unlink()
                    return True
                except PermissionError:
                    return False
            wait_for(remove_exited_host)
            print('PASS native host shuts down without audition; six audio checksums match')
        del lua  # release Lua's open log handle before TemporaryDirectory cleanup
