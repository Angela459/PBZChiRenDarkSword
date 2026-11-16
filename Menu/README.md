# 可选菜单集成

本模组默认开启，基础安装和声音播放不依赖 PBZ Mods Menu。本目录仅供已经使用菜单、希望通过界面切换的玩家选用。

退出游戏，把本目录的 `main.js` 放到：

`<PBZ>/ProjectPBZ/Content/JavaScript/PBZModsMenu/Mods/PBZChiRenAudioReplace/main.js`

重新启动后，**炽♂刃音效** 与“设置”等栏目并列，只提供“启用”开关。配置自动保存至 `ProjectPBZ/Content/Paks/~mods/PBZChiRenAudioReplace.txt`；关闭会恢复原声。

若使用 Mods Menu **0.9.8**，希望隐藏额外的“恢复默认”行，可选用本目录的补丁。备份菜单核心 `Mods/PBZModsMenu/main.js`，运行：

```powershell
python Menu/patch_menu_core.py "菜单核心 main.js 的路径" "打补丁后的 main.js 路径"
```

将输出替换回核心路径。脚本遇到不认识的核心版本会拒绝修改，已经打过相同补丁则无需重复。
