# PBZChiRenDarkSword v1.0 — 炽♂刃音效

《影之刃零》炽刃大招音效模组。基于 UE4SS 读取技能节点，用本地播放器播放替换音频，提供模组菜单开关。默认开启。

| 游戏节点 | 自定义音频 |
| --- | --- |
| 三段蓄力 | 10 → 02 → 09，分别由蓄力节点触发 |
| 真实砸地，未确认本次满蓄命中 | 01，立即播放，不等技能结束 |
| 满蓄命中敌人 | 跳过或停止本次 01，依次播放 12 → 11 |

低蓄命中或满蓄空挥仍正常播放 01。每次有效满蓄命中都可触发，连续释放支持重新识别。没有快捷键、固定启动等待或一秒补播。

当前使用裁剪版 `12-00.00.00.201-00.00.01.128.mp3` 转换出的 12 音频，解码后时长 **0.850 秒**；11 在它完整播放后接上。六段音频的格式、时长和 SHA-256 见 [audio-manifest.json](audio-manifest.json)。

## 安装

需要已在当前游戏版本正常工作的 UE4SS 和 PBZ Mods Menu。项目目录名为 `PBZChiRenDarkSword`；为兼容已有安装和保存的开关，游戏内技术 ID 保持 `PBZChiRenAudioReplace`。

退出游戏后，以游戏根目录 `<PBZ>` 为基准：

1. 建立 `<PBZ>/platform/steam/ue4ss/Mods/PBZChiRenAudioReplace/`，把本仓库的 `Scripts/`、`Audio/`、`AudioHost.exe` 放进去，并在该模组目录内建立空的 `Runtime/` 文件夹。
2. 在 UE4SS 的 `Mods/mods.txt` 中添加或确认 `PBZChiRenAudioReplace : 1`。旧探针 `PBZChiRenAudioProbe` 如存在则设为 `0`，避免重复安装音频模组。
3. 把 `Menu/main.js` 放到 `<PBZ>/ProjectPBZ/Content/JavaScript/PBZModsMenu/Mods/PBZChiRenAudioReplace/main.js`。
4. 如需菜单里只有一个开关、没有“恢复默认”行，可对 Mods Menu **0.9.8** 应用可选补丁。先备份其 `Mods/PBZModsMenu/main.js`，再运行：

   ```powershell
   python Menu/patch_menu_core.py "菜单核心 main.js 的路径" "打补丁后的 main.js 路径"
   ```

   脚本遇到不认识的核心版本会拒绝修改。将输出替换回核心路径；已经应用过则不必重复。

进入游戏后，在与“设置”并列的 **炽♂刃音效** 栏目展开唯一的“启用”开关。选择自动保存在 `ProjectPBZ/Content/Paks/~mods/PBZChiRenAudioReplace.txt`，支持 `Enabled=On/Off`；无配置时默认开启。

关闭开关会停止自定义声音并恢复本模组修改过的原声引用。卸载时退出游戏，移除上述模组目录、菜单描述目录及 `mods.txt` 对应启用项即可。

## 原理与限制

- 游戏线程采样 `ChargeCount`；真实砸地通过时间轴声音动作的 `PlayingID` 变化识别。
- 命中使用游戏的 `PBZ_BulletEvent_MarkBulletHitTarget_C:Trigger`，核对角色目标、当前玩家及炽刃技能来源。接受 UE4SS 的 `AActor` 封装；必要时从命中组件取所属角色，不依靠血量或瞄准目标猜测。
- 大招的九处指定原声引用在运行时临时清空，关闭后恢复。保留其他声音层；这不是 Wwise Bank/PAK 替换，不修改游戏 EXE 或存档。
- 满蓄命中一经核实就直接提交播放命令。播放器提前准备四路命中缓冲，省去每次打开设备的等待；12 与 11 在同一个 PCM 缓冲中顺序播放。
- 每次施放有独立编号，只取消该次 01。如果 01 在实际命中前已经播出一小段，已听到的部分无法撤回；不会为了预测命中而延迟空挥的 01。
- 输出使用 Windows 系统默认音频设备和音量，不跟随游戏音效音量或暂停状态。原生接口和游戏更新兼容性仍取决于当前 UE4SS/游戏构建。

## 开发与验证

本分支为 `dev`，版本 **v1.0**。保留播放器源码、详细运行日志、构建工具和回归测试；`main` 仅保留正式运行与安装文件。开发版与正式版的音频和触发行为一致。

Windows 下使用 Python 3.9+ 和系统 .NET Framework 编译带详细日志的播放器：

```powershell
python tools/build.py dev
```

Python 依赖与检查：

```powershell
python -m pip install -r tests/requirements.txt
python tests/check_replace.py
node tests/check_menu.js "已打补丁的 Mods Menu 核心 main.js 路径"
```

测试包含本仓库内的 Unreal 模拟，无需旁边的探针项目。原生音频检查使用全零 PCM，不试听素材；覆盖连续施放、满蓄命中、01 抑制、回调即时提交、通道复用、开关持久化和通信冲突恢复。模拟检查不能代替真实游戏测试。

运行日志位于安装目录的 `Runtime/run-*.log` 和 `Runtime/host-*.log`。命中记录 `PLAY sequence=12,11 dispatch=callback`；播放器记录 `STOP_GROUND`、`prepared=True` 和 `submit_ms`，可区分命中检测与播放提交的延迟。运行日志、临时研究输出和旧的拼接音频不上传到仓库。
## 生成 main 安装版本

```powershell
python tools/build.py release "仓库之外的全新输出目录"
```

构建会删除 Lua/菜单中的 `DEV-BEGIN` 至 `DEV-END` 诊断区段，并编译关闭 `DEVELOPMENT` 的播放器。输出不包含测试、构建工具或 C# 源文件，不会改动当前分支。安装需要的菜单补丁脚本仍然保留。

对输出执行同一套行为检查（PowerShell）：

```powershell
$env:PBZ_TEST_ROOT = "生成的输出目录"
python tests/check_replace.py
node tests/check_menu.js "已打补丁的 Mods Menu 核心 main.js 路径"
Remove-Item Env:PBZ_TEST_ROOT
```

正式版检查仍覆盖 Lua 音频命令、菜单、恢复机制和静音原生播放路径，仅跳过正式版已移除的诊断输出断言。
