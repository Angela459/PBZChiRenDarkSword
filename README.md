# PBZChiRenDarkSword v1.0 — 炽♂刃音效

《影之刃零》炽刃大招音效模组。基于 UE4SS 读取技能节点，用本地播放器播放替换音频。默认开启。

| 游戏节点 | 自定义音频 |
| --- | --- |
| 三段蓄力 | 10 → 02 → 09，分别由蓄力节点触发 |
| 真实砸地，未确认本次满蓄命中 | 01，立即播放，不等技能结束 |
| 满蓄命中敌人 | 跳过或停止本次 01，依次播放 12 → 11 |

低蓄命中或满蓄空挥仍正常播放 01。每次有效满蓄命中都可触发，连续释放支持重新识别。

## 安装

仅需已在当前游戏版本正常工作的 UE4SS。

1. 退出游戏，从 [Releases](https://github.com/Angela459/PBZChiRenDarkSword/releases/tag/v1.0) 下载 **PBZChiRenDarkSword-v1.0.zip**。
2. 打开游戏根目录（Steam库中右键《影之刃零》→ 管理 → 浏览本地文件），找到 platform\steam\ue4ss\Mods\目录。
3. 将zip里面的PBZChiRenDarkSword文件夹复制到Mods文件夹里，再启动游戏。

卸载时退出游戏，删除 `Mods/PBZChiRenDarkSword/` 即可；若曾手动添加本模组的 `mods.txt` 条目，也可移除。

## 可选开关

开关位于模组目录内的 `PBZChiRenDarkSword.config.json`，默认 `"Enabled": true`，改为 `false` 会停止自定义声音并恢复本模组修改的原声引用。已安装 PBZ Mods Menu 和它的可选 UE4SS Bridge 时，菜单自动提供“炽♂刃音效”栏目，只有一个“启用”开关；不需要菜单也能使用音效。
