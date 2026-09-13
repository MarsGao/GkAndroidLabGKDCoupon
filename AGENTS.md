# GkAndroidLabGKDCoupon Agent Rules

个人项目（MarsGao），不是高昌机电官方仓库。  
GKD 显示名：**MarsGao薅羊毛领券** · 订阅 id：`82640113`。

## 唯一订阅来源

| 权威 | 路径 |
|---|---|
| **当前唯一可发布订阅** | [`dist/gkd.json5`](dist/gkd.json5) + [`dist/gkd.version.json5`](dist/gkd.version.json5) |
| 废止执行权威 | `GkAndroidLab/configs/gkd/*.json5`（仅历史草稿，不得回灌为本仓发布源） |
| 业务脚本 | 本仓 `scripts/`；通用 ADB helper 在 `GkAndroidLab/scripts/ecommerce/adb_ui_helper.py` |

发布前必须让 `gkd.json5` 的 `version` 与 `gkd.version.json5` 一致，且 **递增**。

## 两种运行模式（第一版禁止中途自动切换）

### 1. GKD 辅助模式

- 用户手动进入已支持页面。
- 仅启用本订阅中 **已验证且默认开启** 的规则组。
- AI/ADB **只观察、不代点领取**；不得宣称「已自动完成整条任务」。

### 2. 脚本任务模式（短期主基线）

- 先确认本订阅及其他订阅中 **重叠的拼多多自动点击规则已停用**（现场切换；不杜撰 GKD 私有 API、不改其数据库）。
- 脚本获得设备执行权，独立完成已批准任务；结束后提醒恢复先前订阅配置并回读。
- PC 进程锁 **不能** 当作与手机 GKD 的互斥证据。

## 本仓做什么 / 不做什么

- 做：少量拼多多领券/打卡专用规则 + 闭环脚本状态机。
- 不做：fork 大型广告订阅；商品搜索收藏；充值中心/淘宝/积分兑换（除非用户另行批准扩入）。
- 不做：把「点了」当成成功；无正向 UI 证据不得记 `verified`。

## 旧入口替换清单

| 旧入口 | 状态 | 替代 |
|---|---|---|
| `GkAndroidLab/configs/gkd/gkd.json5` / `pinduoduo_rules.json5` | 废止业务权威 | 本仓 `dist/gkd.json5` |
| Skill 中「必然领全 / 生产级闭环」表述 | 废止 | 以本仓 README 验证矩阵 + 脚本结果枚举为准 |
| `enter_coupon_venue.py` 固定坐标盲点兜底 | 废止 | 低置信度停机 / `needs_review` |
| `verify_pdd_coupon_venue.py` 把 XML 命中称作 GKD Rule 验证 | 废止口径 | 分开：页面探查 / 脚本闭环 / GKD 引擎验收 |
| `claim_all.py` / 淘宝全量调度作为本任务入口 | 不用于本仓窄任务 | `scripts/run_pdd_coupon_task.py`（脚本任务模式） |

## 结果枚举

`verified` | `already_claimed` | `unavailable` | `failed` | `needs_review`

前后证据对不上同一张券 → `needs_review`。UI 领取态 ≠ 服务器最终额度。

## 相关仓库

- [GkAndroidLab](https://github.com/MarsGao/GkAndroidLab) — ADB helper、设备适配、电商 Skill
- 审核 Plan：`docs/2026-09-13-pdd-automation-review-plan.md`
