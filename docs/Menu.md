# 自动菜单接入

PBZChiRenDarkSword 使用 PBZ Mods Menu 已有的 UE4SS 配置发现机制，不需要手动放置 `main.js`，不修改菜单核心。

安装 ZIP 在模组目录内自带：

- `PBZChiRenDarkSword.config.json`：唯一的 `Enabled` 布尔开关，默认 `true`；Lua 定期读取，开关变更后切换音效。
- `PBZChiRenDarkSword.modsmenu.json`：栏目标题“炽♂刃音效”、说明和版本。菜单从配置自动生成唯一的开关；不增加恢复默认行。

已经安装 PBZ Mods Menu 及其官方可选 **PBZModsMenuBridge** 时，菜单会自动发现并允许修改，无需复制脚本。Bridge 负责枚举由 `enabled.txt` 启动的 UE4SS 模组，以及将菜单修改写回 JSON；它属于菜单的可选支持组件，本模组不捆绑它。

仅安装菜单而没有 Bridge 时，已被菜单枚举到的配置只能查看；仅以 `enabled.txt` 启动的模组也可能不会被列出。没有菜单或 Bridge 时，音效仍正常运行，可直接将模组内 JSON 的 `Enabled` 改为 `false` 关闭。

接入依据是本地 Mods Menu 0.9.8 的 `ue4ssNames()`、`ue4ssMod()` 与配置写入 Bridge 分支。开发回归直接执行这些菜单函数，并检查未修改菜单核心时只生成本模组标题和一个开关。
