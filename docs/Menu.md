# 菜单接入

“炽♂刃音效”栏目下的“启用”和“音量”为同级设置；音量范围 0–200%，默认 100%。

`PBZChiRenDarkSword.modsmenu.json` 声明两个控件。没有官方 Bridge 时，菜单值保存在 `Content/Paks/~mods/PBZChiRenDarkSword.txt`，Lua 直接读取该文件；Bridge 存在时，继续使用 Bridge 写入的模组 JSON 配置。未通过菜单设置时，Lua 使用 `PBZChiRenDarkSword.config.json` 中的默认值。

仅有 PBZ Mods Menu 时，`Menu/main.js` 直接注册栏目。菜单首次创建设置文件时从 JSON 读取默认值，不会覆盖已有选择。无需 Bridge。

Lua 在加载时检测菜单 bootstrap，并调用 `Menu/install.ps1` 自动放置本模组注册脚本、添加发现条目，不修改菜单核心。若菜单早于 Lua 启动，首次自动安装后需重启一次游戏。没有安装菜单时跳过此步骤，音效仍能独立运行。

已经有官方 Bridge 时，注册脚本不再添加栏目，使用 Bridge 原有的 JSON 发现与写入功能，避免重复显示。
