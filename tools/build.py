"""Build v1.0 dev host, or generate a clean main payload in a NEW directory."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CSC = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
FILES = ('.gitattributes', '.gitignore', 'README.md', 'audio-manifest.json',
         'Menu/main.js', 'Menu/patch_menu_core.py', 'Scripts/main.lua')


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


def compile_host(destination, development=False):
    args = [str(CSC), '/nologo', '/target:winexe', '/out:' + str(destination)]
    if development:
        args.append('/define:DEVELOPMENT')
    subprocess.run(args + [str(ROOT / 'AudioHost.cs')], check=True)


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
        elif relative == 'Menu/main.js':
            text = strip_dev(text, '//')
        elif relative == 'README.md':
            text = text.split('## 开发与验证', 1)[0]
            text += ('## 分支\n\n'
                     '`main` 为 v1.0 安装版本，仅保留运行、音频及安装所需文件。'
                     '源码构建、详细日志及回归测试见 [dev 分支]'
                     '(https://github.com/Angela459/PBZChiRenDarkSword/tree/dev)。\n\n'
                     '运行故障日志位于模组目录的 `Runtime/`；正式版不记录逐次播放、接口枚举或性能计时。\n')
        with target.open('w', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
    (destination / 'Audio').mkdir()
    for name in ('1_10.wav', '2_02.wav', '3_09.wav', '4_01.wav', '5_12.wav', '6_11.wav'):
        shutil.copy2(ROOT / 'Audio' / name, destination / 'Audio' / name)
    compile_host(destination / 'AudioHost.exe')
    print('Release v1.0: ' + str(destination))


if __name__ == '__main__':
    if sys.argv[1:] == ['dev']:
        compile_host(ROOT / 'AudioHost.exe', development=True)
        print('Development v1.0 host built')
    elif len(sys.argv) == 3 and sys.argv[1] == 'release':
        release(sys.argv[2])
    else:
        raise SystemExit('Usage: python tools/build.py dev | release NEW_OUTPUT_DIRECTORY')
