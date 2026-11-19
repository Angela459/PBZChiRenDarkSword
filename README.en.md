# PBZChiRenDarkSword v1.1 - Chi♂Ren Audio

简体中文: [README.md](README.md)

Video demonstrations:

- Bilibili: [Deep Dark Sword](https://www.bilibili.com/video/BV1dosu6HERz)
- YouTube: [Deep Dark Sword](https://youtu.be/qU0BHfrs_MM?si=PKaqolOyO2Ukn2PM)

An audio replacement mod for Chi Ren's ultimate ability in *Phantom Blade Zero*. UE4SS reads the ability state, while a UE4SS C++ mod plays replaceable WAV files inside the game process. Enabled by default.

| Game event | Replacement audio |
| --- | --- |
| Charge stages 1, 2, and 3 | `charge_stage_1.wav`, `charge_stage_2.wav`, then `charge_stage_3.wav` |
| Ground impact, unless a full-charge hit is confirmed | `ground_impact.wav` |
| Full-charge hit on an enemy | Cancels the ground-impact clip and plays `full_charge_hit_1.wav` followed by `full_charge_hit_2.wav` |

Low-charge hits and full-charge misses still play the ground-impact clip. Consecutive ultimates and repeated confirmed hits are supported.

## Installation

Requires a working UE4SS installation compatible with the current game version.

1. Close the game and download [PBZChiRenDarkSword-v1.1.zip](https://github.com/Angela459/PBZChiRenDarkSword/releases/download/v1.1/PBZChiRenDarkSword-v1.1.zip) from [Releases](https://github.com/Angela459/PBZChiRenDarkSword/releases/tag/v1.1).
2. Open the game folder from Steam by choosing **Manage > Browse local files**, then open `platform/steam/ue4ss/Mods/`.
3. Copy both `PBZChiRenDarkSword` and `PBZChiRenNativeAudio` from the ZIP into the `Mods` folder.
4. Start the game. On the first launch, the mod adds the native audio mod to `mods.txt`. Restart the game once so UE4SS can load it.

To uninstall, close the game, delete `Mods/PBZChiRenDarkSword/` and `Mods/PBZChiRenNativeAudio/`, then remove the `PBZChiRenNativeAudio` entry from `mods.txt`.

## Settings

Configure the mod in the **Chi♂Ren Audio** section of PBZ Mods Menu. The **Play original sounds too** toggle is off by default. When enabled, the game's original sound and the replacement audio play together. The volume range is 0-200%, with 100% matching the source audio level.

Without PBZ Mods Menu, edit `PBZChiRenDarkSword.config.json`. The available settings are `Enabled`, `Volume`, and `PlayOriginal`.

## Replacing Audio

Close the game and replace the matching WAV file in `Mods/PBZChiRenDarkSword/Audio/`, keeping its filename. The audio must be PCM, mono, 48 kHz, 16-bit WAV. Restart the game after replacing files. Back up the original files first.

| File | Use |
| --- | --- |
| `charge_stage_1.wav` | First charge stage |
| `charge_stage_2.wav` | Second charge stage |
| `charge_stage_3.wav` | Third charge stage |
| `ground_impact.wav` | Ground impact, including low-charge hits and full-charge misses |
| `full_charge_hit_1.wav` | First part of a confirmed full-charge hit |
| `full_charge_hit_2.wav` | Second part of a confirmed full-charge hit |
