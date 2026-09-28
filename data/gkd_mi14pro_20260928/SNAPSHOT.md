# mi14pro GKD 配置快照

- 抓取时间：`2026-09-28T11:37:09+08:00`
- 设备：mi14pro `4236fdb8` · 23116PN5BC/shennong · 1440x3200
- GKD `1.12.1` · 拼多多 `8.26.0`
- 系统无障碍：`com.x8bit.bitwarden/.Accessibility.AccessibilityService`
- GKD 无障碍组件是否启用：**否**（当前仅 Bitwarden）
- 来源：`/sdcard/Android/data/li.songe.gkd/files/` 只读拉取（store + db + subscription）
- 用途：OnePlus 13 配置丢失后对照恢复；含已订阅但总开关关闭的条目

## 全局 store（关键设置）

| 键 | 含义 | 值 |
|---|---|---|
| `enableMatch` | 规则匹配 | `False` |
| `enableStatusService` | 状态栏/服务相关 | `False` |
| `enableAutomator` | 自动操作器 | `False` |
| `toastWhenClick` | 点击提示 | `True` |
| `actionToast` | 点击 Toast 文案 | `GKD` |
| `updateSubsInterval` | 订阅更新间隔(ms) | `259200000` |
| `httpServerPort` | HTTP 端口 | `8888` |
| `showDisabledRule` | 显示已禁用规则 | `True` |

**结论**：全局规则匹配 `enableMatch=False`；与无障碍关闭一致，当前不会自动点击。

## 订阅列表（含未启用）

| 顺序 | id | 名称 | 版本 | 总开关 | 自动更新 | updateUrl |
|---:|---:|---|---:|---|---|---|
| 0 | `666` | AIsouler的GKD订阅-已停止维护 · AIsouler | 406 | 关 | 开 | `https://registry.npmmirror.com/@aisouler/gkd_subscription/latest/files/dist/AIsouler_gkd.json5` |
| 1 | `86` | 奥怪的GKD订阅 · aoguai | 89 | **开** | 开 | `https://raw.githubusercontent.com/aoguai/subscription/custom/dist/aoguai_gkd.json5` |
| 2 | `-2` | 本地订阅 | 0 | 关 | 开 | `` |
| 3 | `82640113` | MarsGao薅羊毛领券 · MarsGao | 7 | **开** | 开 | `http://127.0.0.1:38080/gkd.json5` |

## 分类开关覆盖（category_config）

| 订阅 | category_key | 名称 | 覆盖 |
|---|---:|---|---|
| `86` 奥怪的GKD订阅 | 0 | 开屏广告 | 开 |
| `86` 奥怪的GKD订阅 | 1 | 青少年模式 | 默认(跟随订阅) |
| `86` 奥怪的GKD订阅 | 6 | 局部广告 | 默认(跟随订阅) |
| `86` 奥怪的GKD订阅 | 7 | 全屏广告 | 默认(跟随订阅) |
| `86` 奥怪的GKD订阅 | 8 | 分段广告 | 默认(跟随订阅) |
| `86` 奥怪的GKD订阅 | 9 | 功能类 | 默认(跟随订阅) |
| `666` AIsouler的GKD订阅-已停止维护 | 3 | 评价提示 | 默认(跟随订阅) |
| `666` AIsouler的GKD订阅-已停止维护 | 6 | 局部广告 | 开 |
| `666` AIsouler的GKD订阅-已停止维护 | 7 | 全屏广告 | 开 |
| `666` AIsouler的GKD订阅-已停止维护 | 8 | 分段广告 | 开 |
| `666` AIsouler的GKD订阅-已停止维护 | 9 | 功能类 | 默认(跟随订阅) |
| `666` AIsouler的GKD订阅-已停止维护 | 10 | 其他 | 关 |

## 规则组开关覆盖（subs_config）

说明：`enable=null` 表示未单独覆盖，跟随订阅默认；表中仍列出全部覆盖行（含排除 Activity）。

| 订阅 | type | app_id | group_key | 规则名 | 覆盖 | exclude |
|---|---:|---|---:|---|---|---|
| `666` | 3 | `(global)` | 0 | 开屏广告-全局 | 开 | `!app.podcast.cosmos / app.podcast.cosmos/io.iftech.android.podcast.app.playerpage.view.PlayerActivity / com.microsoft.todos` |
| `666` | 3 | `(global)` | 1 | 更新提示-全局 | 关 | `com.xiaomi.market/com.xiaomi.market.ui.UpdateListActivity` |
| `666` | 2 | `cn.wps.moffice_eng` | 9 | 功能类-自动签到 | 开 | `` |
| `666` | 2 | `com.alicloud.databox` | 0 | 功能类-自动签到 | 开 | `` |
| `666` | 2 | `com.autonavi.minimap` | 13 | 局部广告-卡片广告 | 默认(跟随订阅) | `com.autonavi.minimap/com.autonavi.map.activity.NewMapActivity` |
| `666` | 2 | `com.douban.frodo` | 11 | 更新提示 | 开 | `` |
| `666` | 2 | `com.douban.frodo` | 13 | 其他-标记看过的影视弹窗 | 开 | `` |
| `666` | 2 | `com.eg.android.AlipayGphone` | 3 | 更新提示-版本更新弹窗 | 开 | `` |
| `666` | 2 | `com.eg.android.AlipayGphone` | 22 | 其他-蚂蚁理财社区-[加入同路人]弹窗 | 开 | `` |
| `666` | 2 | `com.google.android.apps.photos` | 0 | 更新提示 | 开 | `` |
| `666` | 2 | `com.google.android.documentsui` | 10 | 功能类-授权第三方应用访问文件夹 | 默认(跟随订阅) | `com.google.android.documentsui/com.android.documentsui.picker.PickActivity` |
| `666` | 2 | `com.google.android.youtube` | 3 | 全屏广告-会员广告 | 默认(跟随订阅) | `com.google.android.youtube/com.google.android.apps.youtube.app.watchwhile.MainActivity` |
| `666` | 2 | `com.lbe.security.miui` | 1 | 功能类-权限授予弹窗 | 关 | `` |
| `666` | 2 | `com.mcdonalds.gma.cn` | 3 | 功能类-关闭[开通免密支付]弹窗 | 开 | `` |
| `666` | 2 | `com.nowcasting.activity` | 3 | 分段广告-卡片广告 | 默认(跟随订阅) | `com.nowcasting.activity/com.nowcasting.activity.WeatherActivity` |
| `666` | 2 | `com.taobao.idlefish` | 6 | 功能类-自动点击[查看原图] | 关 | `` |
| `666` | 2 | `com.taobao.taobao` | 3 | 局部广告-悬浮广告 | 默认(跟随订阅) | `com.taobao.taobao/com.taobao.browser.BrowserActivity` |
| `666` | 2 | `com.tencent.mm` | 1 | 功能类-电脑微信快捷自动登录 | 关 | `` |
| `666` | 2 | `com.tencent.mm` | 7 | 功能类-自动选中发送原图 | 关 | `` |
| `666` | 2 | `com.tencent.mm` | 9 | 功能类-自动查看原图 | 关 | `` |
| `666` | 2 | `com.tencent.mm` | 18 | 功能类-青少年模式自动点击验证密码 | 开 | `` |
| `666` | 2 | `com.tencent.mm` | 19 | 功能类-订阅号-展开更早的消息 | 开 | `` |
| `666` | 2 | `com.tencent.mm` | 22 | 功能类-开启青少年模式后的每日验证 | 开 | `` |
| `666` | 2 | `com.tencent.mm` | 34 | 功能类-付款时自动点击[支付] | 关 | `` |
| `666` | 2 | `com.tencent.mm` | 35 | 分段广告-公众号文章内广告 | 开 | `` |
| `666` | 2 | `com.tencent.mm` | 36 | 功能类-自动点击[查看原视频] | 关 | `` |
| `666` | 2 | `com.tencent.mm` | 38 | 功能类-自动语音转文字 | 关 | `` |
| `666` | 2 | `com.tencent.mm` | 39 | 功能类-语音/视频通话呼入10秒后自动点击接听 | 关 | `` |
| `666` | 2 | `com.tencent.mm` | 40 | 功能类-点击语音条菜单里的转文字 | 关 | `` |
| `666` | 2 | `com.tencent.mm` | 41 | 功能类-自动接龙 | 关 | `` |
| `666` | 2 | `com.tencent.mm` | 42 | 功能类-自动点击未读消息（头像右上角为数字） | 关 | `` |
| `666` | 2 | `com.tencent.mm` | 43 | 功能类-自动点击未读消息（头像右上角为红点） | 关 | `` |
| `666` | 2 | `com.twitter.android` | 8 | 其他-关闭[开启个性化广告]弹窗 | 开 | `` |
| `666` | 2 | `com.xiaomi.market` | 10 | 功能类-忽略升级 | 关 | `` |
| `666` | 2 | `com.xunmeng.pinduoduo` | 1 | 更新提示 | 开 | `` |
| `666` | 2 | `com.xunmeng.pinduoduo` | 2 | 全屏广告-弹窗广告 | 默认(跟随订阅) | `com.xunmeng.pinduoduo/com.xunmeng.pinduoduo.ui.activity.HomeActivity` |
| `666` | 2 | `com.xunmeng.pinduoduo` | 9 | 功能类-多多视频每日自动签到 | 开 | `` |
| `666` | 2 | `com.xunmeng.pinduoduo` | 12 | 全屏广告-下单后出现的弹窗 | 关 | `` |
| `666` | 2 | `com.xunmeng.pinduoduo` | 16 | 青少年模式 | 开 | `` |
| `666` | 2 | `com.xunmeng.pinduoduo` | 20 | 其他-登录提现页面点击[跳过] | 开 | `` |
| `666` | 2 | `me.ele` | 2 | 全屏广告-红包弹窗 | 默认(跟随订阅) | `me.ele/me.ele.muise.page.WeexPageActivity` |

## 拼多多相关（恢复时优先核对）

### 本仓订阅 `82640113` MarsGao薅羊毛领券

- 总开关：**开** · 版本 v7 · updateUrl `http://127.0.0.1:38080/gkd.json5`

| group_key | 名称 | 订阅默认 | 手机覆盖 | 有效推测 |
|---:|---|---|---|---|
| 1 | 领券签到-百亿补贴会员每日打卡 | 开 | 无覆盖 | 开 |
| 2 | 领券签到-会员等级礼包无门槛券领取 | 开 | 无覆盖 | 开 |
| 3 | 弹窗处理-关闭已知诱导弹窗 | 开 | 无覆盖 | 开 |
| 4 | 领券签到-进入百亿消费券会场 | 关 | 无覆盖 | 关 |
| 5 | 领券签到-消费券会场立即领取（单规则·遗留） | 关 | 无覆盖 | 关 |
| 6 | 领券签到-消费券会场立即点亮（单规则·遗留） | 关 | 无覆盖 | 关 |
| 7 | 领券签到-切换地区专享（单规则·遗留） | 关 | 无覆盖 | 关 |
| 8 | 领券签到-会场有序流水线（先领后点亮） | 开 | 无覆盖 | 开 |

### 第三方订阅中拼多多 group 覆盖

| 订阅 | group_key | 规则名 | 覆盖 |
|---|---:|---|---|
| `666` | 1 | 更新提示 | 开 |
| `666` | 2 | 全屏广告-弹窗广告 | 默认(跟随订阅) |
| `666` | 9 | 功能类-多多视频每日自动签到 | 开 |
| `666` | 12 | 全屏广告-下单后出现的弹窗 | 关 |
| `666` | 16 | 青少年模式 | 开 |
| `666` | 20 | 其他-登录提现页面点击[跳过] | 开 |

## OnePlus 13 恢复清单（稍后执行）

1. 安装 GKD 1.12.1（或同主版本），打开无障碍前先按目标模式决定是否启用。
2. **真源路径**为私有目录 `/data/data/li.songe.gkd/files/`（需 root）；`/sdcard/Android/data/...` 仅为副本，直接改副本无效。
3. 按上表写入 `subs_item`（含总开关为关的 AIsouler `666` 与本地 `-2`）及订阅正文 JSON。
4. 导入/更新本仓 `82640113` 到相同 version；OP13 建议用 GitHub `updateUrl`，不要写 mi 本机 `127.0.0.1:38080`。
5. 对照 `subs_config` / `category_config` 写入覆盖；对齐 `store.json`（至少 `enableMatch`）。
6. 回读：订阅列表 UI + 再拉私有 db/store 核对。

已完成记录见：`data/gkd_op13_private_restore/RESTORE.md`（2026-09-28）。

## 原始文件

目录：`data/gkd_mi14pro_20260928/`

| 文件 | 说明 | 是否建议入库 |
|---|---|---|
| `SNAPSHOT.md` | 本说明 | 是 |
| `snapshot.json` | 机读摘要 | 是 |
| `store.json` | 全局设置原样 | 是 |
| `subs_item.json` 等导出 | 表导出 | 是 |
| `gkd.db*` | SQLite 原库 | 否（体积/日志） |
| `subscription/*.json` | 订阅正文缓存 | 否（可从源更新；本仓权威仍是 `dist/gkd.json5`） |
