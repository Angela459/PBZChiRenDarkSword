# PBZChiRenDarkSword v1.0 — 炽♂刃音效

《影之刃零》炽刃大招音效模组。基于 UE4SS 读取技能节点，用本地播放器播放替换音频。默认开启。

| 游戏节点 | 自定义音频 |
| --- | --- |
| 三段蓄力 | 10 → 02 → 09，分别由蓄力节点触发 |
| 真实砸地，未确认本次满蓄命中 | 01，立即播放，不等技能结束 |
| 满蓄命中敌人 | 跳过或停止本次 01，依次播放 12 → 11 |

低蓄命中或满蓄空挥仍正常播放 01。每次有效满蓄命中都可触发，连续释放支持重新识别。没有快捷键、固定启动等待或一秒补播。

当前使用裁剪版 `12-00.00.00.201-00.00.01.128.mp3` 转换出的 12 音频，解码后时长 **0.850 秒**；11 在它完整播放后接上。六段音频的格式、时长和 SHA-256 见 [audio-manifest.json](audio-manifest.json)。

## 安装

仅需已在当前游戏版本正常工作的 UE4SS。

1. 退出游戏，从 [Releases](https://github.com/Angela459/PBZChiRenDarkSword/releases/tag/v1.0) 下载 **PBZChiRenDarkSword-v1.0.zip**。
2. 解压到 `E:\SteamLibrary\steamapps\common\PBZ\platform\steam\ue4ss\Mods\`，然后启动游戏。

解压后的结构为 `Mods/PBZChiRenAudioReplace/Scripts/main.lua`。ZIP 已包含 `enabled.txt` 启用标记，不覆盖现有 `mods.txt`。如以前在 `mods.txt` 中明确将本模组设为 `0`，需改为 `1`。

首次启动会自动创建 `Runtime/`，不需要手动建目录。请下载命名的安装 ZIP；GitHub 自动生成的 Source code 压缩包是仓库源码。

卸载时退出游戏，删除 `Mods/PBZChiRenAudioReplace/` 即可；若曾手动添加本模组的 `mods.txt` 条目，也可移除。

## 播放器与音频格式

`AudioHost.exe` 是本项目编译的 Windows 后台播放器，由 Lua 自动启动。Lua 负责识别游戏节点、临时清空指定原声引用并发送播放指令；播放器通过 Windows WinMM 播放自定义声音，支持多个声音并行、停止本次 01，以及无间隔衔接 12→11。

六段声音使用 **WAV / PCM 16 位 / 单声道 / 48 kHz**，合计约 **517 KiB**。短音效无需运行时解码，便于提前准备播放缓冲。MP3/OGG 可进一步压缩，但需要额外解码实现；现有资源很小，保留 PCM 更合适。由 MP3 转出的 WAV 不会提升原始音质。

`Runtime/` 存放 Lua 与播放器之间的指令、心跳和日志。退出游戏后可删除，下次启用时会自动重建。

## 可选开关

默认无需菜单组件即可运行。[可选菜单集成](https://github.com/Angela459/PBZChiRenDarkSword/blob/main/Menu/README.md)单独提供，不包含在基础安装 ZIP 中。

如已有保存的配置，仍遵从 `ProjectPBZ/Content/Paks/~mods/PBZChiRenAudioReplace.txt` 中的 `Enabled=On/Off`。关闭会停止自定义声音并恢复本模组修改的原声引用；无配置时默认开启。

## 原理与限制

- 游戏线程采样 `ChargeCount`；真实砸地通过时间轴声音动作的 `PlayingID` 变化识别。
- 命中使用游戏的 `PBZ_BulletEvent_MarkBulletHitTarget_C:Trigger`，核对角色目标、当前玩家及炽刃技能来源。接受 UE4SS 的 `AActor` 封装；必要时从命中组件取所属角色，不依靠血量或瞄准目标猜测。
- 大招的九处指定原声引用在运行时临时清空，关闭后恢复。保留其他声音层；这不是 Wwise Bank/PAK 替换，不修改游戏 EXE 或存档。
- 满蓄命中一经核实就直接提交播放命令。播放器提前准备四路命中缓冲，省去每次打开设备的等待；12 与 11 在同一个 PCM 缓冲中顺序播放。
- 每次施放有独立编号，只取消该次 01。如果 01 在实际命中前已经播出一小段，已听到的部分无法撤回；不会为了预测命中而延迟空挥的 01。
- 输出使用 Windows 系统默认音频设备和音量，不跟随游戏音效音量或暂停状态。原生接口和游戏更新兼容性仍取决于当前 UE4SS/游戏构建。

## 分支

`main` 为 v1.0 安装版本，仅保留运行、音频及安装所需文件。源码构建、详细日志及回归测试见 [dev 分支](https://github.com/Angela459/PBZChiRenDarkSword/tree/dev)。

运行故障日志位于模组目录的 `Runtime/`；正式版不记录逐次播放、接口枚举或性能计时。
