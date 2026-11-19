# PBZChiRenDarkSword v1.1 — 炽♂刃音效

English version: [README.en.md](README.en.md)

视频演示：
B站：【〖影之刃零MOD〗deep ♂dark♂sword】 https://www.bilibili.com/video/BV1dosu6HERz
YouTube：https://youtu.be/qU0BHfrs_MM?si=PKaqolOyO2Ukn2PM

《影之刃零》炽刃大招音效模组。基于 UE4SS 读取技能节点，并由 UE4SS C++ 模组在游戏进程内播放可替换 WAV。默认开启。

| 游戏节点 | 自定义音频 |
| --- | --- |
| 三段蓄力 | 10 → 02 → 09，分别由蓄力节点触发 |
| 真实砸地，未确认本次满蓄命中 | 01，立即播放，不等技能结束 |
| 满蓄命中敌人 | 跳过或停止本次 01，依次播放 12 → 11 |

低蓄命中或满蓄空挥仍正常播放 01。每次有效满蓄命中都可触发，连续释放支持重新识别。

## 安装

需要可用的 UE4SS。

1. 退出游戏，从 [Releases](https://github.com/Angela459/PBZChiRenDarkSword/releases/tag/v1.1) 下载 **PBZChiRenDarkSword-v1.1.zip**。
2. 打开游戏根目录（Steam库中右键《影之刃零》→ 管理 → 浏览本地文件），找到 platform\steam\ue4ss\Mods\目录。
3. 将 zip 中的 `PBZChiRenDarkSword` 和 `PBZChiRenNativeAudio` 两个文件夹复制到 Mods 文件夹。
4. 启动游戏。首次启动时，模组会自动将原生音频 Mod 添加到 `mods.txt`，然后重启一次以便 UE4SS 加载它。

卸载时退出游戏，删除 `Mods/PBZChiRenDarkSword/` 与 `Mods/PBZChiRenNativeAudio/`，并从 `mods.txt` 移除对应条目。

## 菜单设置

启用、同时播放原版音效和音量可在“炽♂刃音效”菜单栏目中设置。原版音效开关默认关闭，开启后游戏原声音效与本模组音频叠加播放。音量范围为 0–200%，默认 100%。未安装 PBZ Mods Menu 时，可在 `PBZChiRenDarkSword.config.json` 修改 `Enabled`、`Volume` 和 `PlayOriginal`。

## 替换音频

退出游戏后，将对应 WAV 覆盖到 `Mods/PBZChiRenDarkSword/Audio/`，保留文件名。`charge_stage_1.wav`、`charge_stage_2.wav`、`charge_stage_3.wav` 分别对应三段蓄力，`ground_impact.wav` 对应普通砸地，`full_charge_hit_1.wav` 与 `full_charge_hit_2.wav` 会在满蓄命中时连续播放。音频需为 PCM、单声道、48 kHz、16-bit WAV。重新启动游戏后生效。建议先备份原文件。
