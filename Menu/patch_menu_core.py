"""A separate single-toggle section for the installed PBZ Mods Menu 0.9.8.

Usage: python patch_menu_core.py INPUT.js OUTPUT.js
Back up INPUT before replacing it. Unrecognized core versions are never written.
"""
import sys
from pathlib import Path

LEGACY_PATCHES = [
    (
        '            mod.lastWins = raw.lastWins === true;',
        '            // Opt-in: one registered toggle can occupy a top-level row.\n'
        '            mod.topLevel = origin === "registered" && raw.topLevel === true && list.length === 1\n'
        '                && mod.settings.length === 1 && mod.settings[0].type === "toggle";\n'
        '            mod.lastWins = raw.lastWins === true;',
    ),
    (
        '                const folded = S.folded.has(mod.id);',
        '                const folded = !mod.topLevel && S.folded.has(mod.id);',
    ),
    (
        '                const items = mod.id ? [{ s: { type: "header",',
        '                const items = mod.id && !mod.topLevel ? [{ s: { type: "header",',
    ),
    (
        '                if (!folded && mod.settings.some((s) => s.default !== undefined && !s.generated))',
        '                if (!mod.topLevel && !folded && mod.settings.some((s) => s.default !== undefined && !s.generated))',
    ),
]

PATCHES = [
    (
        '            mod.lastWins = raw.lastWins === true;',
        '            // A separate mod section with one toggle and no Restore defaults row.\n'
        '            mod.singleToggleSection = origin === "registered" && raw.singleToggleSection === true && list.length === 1\n'
        '                && mod.settings.length === 1 && mod.settings[0].type === "toggle";\n'
        '            mod.lastWins = raw.lastWins === true;',
    ),
    (
        '                if (!folded && mod.settings.some((s) => s.default !== undefined && !s.generated))',
        '                if (!mod.singleToggleSection && !folded && mod.settings.some((s) => s.default !== undefined && !s.generated))',
    ),
]


def patch(source):
    # Remove only our previous inline-row extension, if present. Restore the
    # real mod header so this section is a peer of Settings/Gauntlet of Masters.
    for before, after in LEGACY_PATCHES:
        if source.count(after) == 1:
            source = source.replace(after, before, 1)
    for before, after in PATCHES:
        if source.count(after) == 1:
            continue
        if source.count(before) != 1:
            raise ValueError('Unrecognized menu core; cannot locate: ' + before[:100])
        source = source.replace(before, after, 1)
    return source


if __name__ == '__main__':
    src, dst = map(Path, sys.argv[1:])
    data = src.read_bytes()
    line_end = '\r\n' if b'\r\n' in data else '\n'
    result = patch(data.decode('utf-8').replace('\r\n', '\n'))
    dst.write_bytes(result.replace('\n', line_end).encode('utf-8'))
    print('Patched separate single-toggle mod section: ' + str(dst))
