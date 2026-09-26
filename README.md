# GKD订阅 · GKD规则 · MarsGao薅羊毛领券

**GKD 第三方订阅规则**（非官方）。给 [GKD](https://gkd.li) 用的远程订阅：拼多多领券、百亿补贴打卡、无门槛券。  
完整业务闭环以 **脚本任务模式** 为主基线；GKD 仅执行已验证的局部规则，并用 `order`/`excludeMatches` 做弱先后约束。

[![GKD](https://img.shields.io/badge/GKD-第三方订阅-blue.svg)](https://gkd.li/guide/subscription)
[![订阅ID](https://img.shields.io/badge/id-82640113-green.svg)](dist/gkd.json5)
[![version](https://img.shields.io/badge/version-v7-orange.svg)](dist/gkd.version.json5)
[![license](https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-lightgrey.svg)](LICENSE)

**唯一发布源**：[`dist/gkd.json5`](dist/gkd.json5)（勿把 `GkAndroidLab/configs/gkd` 当作本订阅权威）。  
代理约定见 [`AGENTS.md`](AGENTS.md)。  
同页先后顺序：[docs/2026-09-14-gkd-ordering.md](docs/2026-09-14-gkd-ordering.md) · 审核方案：[docs/2026-09-13-pdd-automation-review-plan.md](docs/2026-09-13-pdd-automation-review-plan.md)。

---

## 一键导入

GKD App → 订阅 →「+」→ 粘贴：

```text
https://raw.githubusercontent.com/MarsGao/GkAndroidLabGKDCoupon/main/dist/gkd.json5
```

jsDelivr：

```text
https://cdn.jsdelivr.net/gh/MarsGao/GkAndroidLabGKDCoupon@main/dist/gkd.json5
```

显示名：**MarsGao薅羊毛领券** · id：`82640113` · **version 7**

---

## 两种运行模式（勿中途自动切换）

| 模式 | 谁点击 | 说明 |
|---|---|---|
| **GKD 辅助** | 仅已启用且验证过的规则 | 用户先进页；AI/ADB 只观察，不宣称整条任务完成 |
| **脚本任务**（短期主基线） | 本仓 `scripts/` | 先停用重叠的拼多多自动点击规则（含 **key8**），再跑状态机 |

结果枚举：`verified` / `already_claimed` / `unavailable` / `failed` / `needs_review`  
无正向 UI 证据不得记成功；不承诺「必然领全」。

---

## 规则矩阵（拼多多 · v7）

| key | 名称 | 默认 | 状态 |
|---|---|---|---|
| 1 | 会员每日打卡（精确「打卡」） | 开 | 历史已验证；`resetMatch: app`≠自然日限额 |
| 2 | 等级礼包无门槛券（同卡关系） | 开 | 已收窄；待快照回归 |
| 3 | 已知诱导弹窗（不含开心收下/去使用） | 开 | 已收窄 |
| 4 | 进入百亿消费券会场 | **关** | 主会场常空树；用脚本进场 |
| 5 | 会场「立即领取」（单规则·遗留） | **关** | 避免与 key8 抢点 |
| 6 | 立即点亮（单规则·遗留） | **关** | 浏览计时由脚本负责 |
| 7 | 切换地区专享（单规则·遗留） | **关** | 已并入 key8 / 脚本 |
| 8 | **会场有序流水线**（切 Tab → 领取 → 无券才点亮） | 开 | `order`+`excludeMatches`；**脚本模式请关** |

GKD **不能**可靠完成「领完 → 点亮 → 浏览满 N 秒 → 核验已点亮」。完整闭环用脚本。

---

## 脚本入口

需本机 ADB、设备 `device` 状态；通用 helper 在 [GkAndroidLab](https://github.com/MarsGao/GkAndroidLab) `scripts/ecommerce/adb_ui_helper.py`。

```powershell
cd C:\GkDesktop\GitProjects\GkAndroidLabGKDCoupon
uv sync --extra dev
$env:ANDROID_SERIAL = "4236fdb8" # mi14Pro；仅连接一台 device 时也可省略

# 只观察
uv run python scripts/run_venue_pipeline.py --observe
uv run python scripts/claim_region_exclusive.py --observe

# 会场有序流水线单阶段验收——脚本模式请先关本订阅全部拼多多点击规则
uv run python scripts/run_venue_pipeline.py --confirm-gkd-off
# 或
$env:PDD_CONFIRM_GKD_OFF = "1"
uv run python scripts/run_pdd_coupon_task.py --stages region --confirm-gkd-off

# 页面探查（默认不点领取；不等于 GKD 引擎验收）
uv run python scripts/verify_pdd_coupon_venue.py
```

观察模式只采集页面和设备状态，不唤醒屏幕、不切 Tab、不滑动、不点击。多台设备同时在线时必须传 `--serial`。脚本任务模式会核对前台包名、GKD 无障碍服务未启用、本仓订阅版本，并要求人工确认本订阅全部拼多多自动点击规则及第三方订阅中重叠规则已关闭；条件不满足时拒绝动作。key1/key2 也与脚本打卡/等级券阶段重叠，不能只关 key5/key8。

项目 Skill 入口：`.agents/skills/gk-pdd-coupon/SKILL.md`。每日步骤、券盘点和购买建议以账号当天页面为准；不自动兑换积分、下单或付款。

已有人工作成的脱敏 JSON 时，可用 `uv run python scripts/build_daily_benefits_report.py <input.json>` 输出只读盘点；缺少真实字段时报告会明确标未知，不推测账号权益或节省金额。

历史红色像素定位不再作为默认进场方式；仅显式传入 `--allow-fallback-xy` 才进入兼容探查路径，仍需 Pillow/NumPy。日常运行不应使用历史坐标。

### mi14Pro 逐项实测（2026-09-26）

真机已经证实以下**人工监督 ADB 单步流程**可达：拼多多首页「百亿补贴」→ 频道右上「会员」→ 会员打卡/等级礼包；频道「百亿消费券 100 元券待领」标题→ 消费券会场。打卡从 489 到 504 积分且次日卡片显示待打卡；会员 150 元满 1500、60 元满 480 券已领；双重补贴点击首张后两张一起变「去使用」；广东地区六张券回卡为「去使用」；点亮任务回场显示「今日已点亮」。逐项记录在 [下一阶段 PLAN](docs/2026-09-25-mi14pro-pdd-coupon-next-plan.md)。这些是单日现场结果，不代表全链路脚本或 GKD 引擎已验收。

当前可重复的脚本入口要求先**人工进入相应目标页**，再用 `--stages member` 或 `--stages level` 运行单步；不要从首页直接运行单步，错误页面将返回 `needs_review`。动态消费券 H5 常使 `uiautomator dump` 返回 `could not get idle state`，所以会场领券脚本目前不能承诺无人值守成功；旧 `--open-subsidy` 深链加固定坐标已停用。下一步需基于新鲜截图的文字框和同券卡片身份实现视觉定位及回卡验证，失败时安全停机。默认不启用历史颜色/坐标猜测。

---

## 离线测试

```powershell
uv run pytest -q
```

---

## 版本

| 版本 | 日期 | 说明 |
|---|---|---|
| v7 | 2026-09-14 | key8 有序流水线；key5 默认关；脚本先领后点亮；顺序闸文档 |
| v6 | 2026-09-13 | 收窄规则；关 4/6/7；脚本状态机与结果枚举；文档对齐 |
| v5 | 2026-09 | 七组规则（含点亮/地区 Tab） |
| v2 | 2026-09-03 | 消费券会场相关 |
| v1 | 2026-09-03 | 打卡、等级礼包、弹窗 |

---

## 红线

不做：点「去使用」、裂变分享、下单支付；不存账号/Cookie/私信。  
不 fork 大型广告订阅。不把 Lab 旧 v1 配置回灌为发布源。

许可：[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)
