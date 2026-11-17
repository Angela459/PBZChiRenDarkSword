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

## 菜单设置

开关和音量可在“炽♂刃音效”菜单栏目中设置，两个控件同级。音量范围为 0–200%，默认 100%。未安装 PBZ Mods Menu 时，可在 `PBZChiRenDarkSword.config.json` 修改 `Enabled` 和 `Volume`；100% 为音源原始电平。菜单安装后会自动接入，无需手动复制脚本。

## 分支

`main` 为 v1.0 安装版本，仅保留运行、音频及安装所需文件。源码构建、详细日志及回归测试见 [dev 分支](https://github.com/Angela459/PBZChiRenDarkSword/tree/dev)。

运行故障日志位于模组目录的 `Runtime/`；正式版不记录逐次播放、接口枚举或性能计时。
