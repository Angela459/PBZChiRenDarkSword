"""Build the native UE4SS audio mod and create install packages."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = ('.gitattributes', '.gitignore', 'README.md', 'audio-manifest.json',
         'PBZChiRenDarkSword.config.json', 'PBZChiRenDarkSword.modsmenu.json',
         'docs/Menu.md', 'Scripts/main.lua', 'enabled.txt', 'Menu/main.js', 'Menu/install.ps1')
AUDIO_FILES = ('charge_stage_1.wav', 'charge_stage_2.wav', 'charge_stage_3.wav',
               'ground_impact.wav', 'full_charge_hit_1.wav', 'full_charge_hit_2.wav')
PACKAGE_FILES = ('Scripts/main.lua', 'enabled.txt', 'README.md',
                 'audio-manifest.json', 'PBZChiRenDarkSword.config.json',
                 'PBZChiRenDarkSword.modsmenu.json', 'Menu/main.js', 'Menu/install.ps1') + tuple('Audio/' + name for name in AUDIO_FILES)
NATIVE_FILES = ('PBZChiRenNativeAudio/dlls/main.dll', 'PBZChiRenNativeAudio/enabled.txt')


def strip_dev(source, prefix):
    result, inside = [], False
    for line in source.splitlines():
        if line == prefix + ' DEV-BEGIN':
            if inside:
                raise ValueError('Nested development block')
            inside = True
        elif line == prefix + ' DEV-END':
            if not inside:
                raise ValueError('Unmatched development block')
            inside = False
        elif not inside:
            result.append(line)
    if inside:
        raise ValueError('Unclosed development block')
    return '\n'.join(result) + '\n'


def build_native(destination):
    import_library = os.environ.get('UE4SS_IMPORT_LIBRARY')
    if not import_library or not Path(import_library).is_file():
        raise ValueError('Set UE4SS_IMPORT_LIBRARY to the import library for the installed UE4SS version')
    build_dir = destination.parent / (destination.name + '-native-build')
    subprocess.run(['cmake', '-S', str(ROOT / 'NativeAudio'), '-B', str(build_dir),
                    '-A', 'x64', '-DUE4SS_IMPORT_LIBRARY=' + str(Path(import_library).resolve())], check=True)
    subprocess.run(['cmake', '--build', str(build_dir), '--config', 'Release'], check=True)
    result = build_dir / 'Release/main.dll'
    if not result.is_file():
        raise ValueError('Native UE4SS audio DLL was not produced')
    target = destination / NATIVE_FILES[0]
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(result, target)


def release(destination):
    destination = Path(destination).resolve()
    # Never write into a checkout or replace a previous build.
    if destination.exists() or destination.is_relative_to(ROOT):
        raise ValueError('Use a new output directory outside this repository')
    destination.mkdir(parents=True)
    for relative in FILES:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        text = (ROOT / relative).read_text(encoding='utf-8')
        if relative == 'Scripts/main.lua':
            text = strip_dev(text, '--')
            text = text.replace('local function startCast(reason,count)', 'local function startCast()')
            text = re.sub(r'startCast\("[^"\n]+",[^)\n]+\)', 'startCast()', text)
            text = text.replace('local function queueHit(enemy,via)', 'local function queueHit(enemy)')
            text = text.replace('queueHit(enemy,"marker "..path.." target="..resolvedBy)', 'queueHit(enemy)')
            text = text.replace('local enemy,resolvedBy=eventTarget(data)', 'local enemy=eventTarget(data)')
            text = text.replace('return actor,"EventActor"', 'return actor')
            text = text.replace('return owner,"EventBody.Component.GetOwner"', 'return owner')
            for token in ('diagnoseHit', 'hitDiagnostics', 'hitCounts', 'local calls=', 'via..', 'DEV-'):
                if token in text:
                    raise ValueError('Development code leaked into release: ' + token)
        elif relative == 'README.md':
            text = text.split('## 开发与验证', 1)[0]
            text += ('## 分支\n\n'
                     '`main` 为 v1.1 安装版本，包含运行时、音频文件和 UE4SS 原生后端。'
                     '源码构建、详细日志及回归测试见 [dev 分支]'
                     '(https://github.com/Angela459/PBZChiRenDarkSword/tree/dev)。\n\n'
                     '原生播放日志位于 `Mods/PBZChiRenNativeAudio/native-audio.log`。\n')
        with target.open('w', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
    (destination / 'Audio').mkdir()
    for name in AUDIO_FILES:
        shutil.copy2(ROOT / 'Audio' / name, destination / 'Audio' / name)
    build_native(destination)
    (destination / 'PBZChiRenNativeAudio/enabled.txt').write_text('', encoding='ascii')
    print('Release v1.1: ' + str(destination))


def package(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    for relative in PACKAGE_FILES + NATIVE_FILES:
        if not (source / relative).is_file():
            raise ValueError('Missing release file: ' + relative)
    if 'DEV-BEGIN' in (source / 'Scripts/main.lua').read_text(encoding='utf-8'):
        raise ValueError('Package a release build, not a development checkout')
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in PACKAGE_FILES:
            archive.write(source / relative, 'PBZChiRenDarkSword/' + relative)
        for relative in NATIVE_FILES:
            archive.write(source / relative, relative)
    print('Install ZIP v1.1: ' + str(destination))


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'native':
        build_native(Path(sys.argv[2]).resolve())
        print('Native UE4SS audio mod built')
    elif len(sys.argv) == 3 and sys.argv[1] == 'release':
        release(sys.argv[2])
    elif len(sys.argv) == 4 and sys.argv[1] == 'package':
        package(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit('Usage: python tools/build.py native OUTPUT_DIRECTORY | release NEW_OUTPUT_DIRECTORY | package RELEASE_DIRECTORY ZIP_PATH')
