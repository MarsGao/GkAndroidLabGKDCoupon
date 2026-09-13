# GKD订阅 · GKD规则 · MarsGao薅羊毛领券

**GKD 第三方订阅规则**（非官方）。给 [GKD](https://gkd.li) 用的远程订阅：拼多多领券、百亿补贴打卡、无门槛券。  
完整业务闭环以 **脚本任务模式** 为主基线；GKD 仅执行已验证的局部规则。

[![GKD](https://img.shields.io/badge/GKD-第三方订阅-blue.svg)](https://gkd.li/guide/subscription)
[![订阅ID](https://img.shields.io/badge/id-82640113-green.svg)](dist/gkd.json5)
[![version](https://img.shields.io/badge/version-v6-orange.svg)](dist/gkd.version.json5)
[![license](https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-lightgrey.svg)](LICENSE)

**唯一发布源**：[`dist/gkd.json5`](dist/gkd.json5)（勿把 `GkAndroidLab/configs/gkd` 当作本订阅权威）。  
代理约定见 [`AGENTS.md`](AGENTS.md)。审核方案：[`docs/2026-09-13-pdd-automation-review-plan.md`](docs/2026-09-13-pdd-automation-review-plan.md)。

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

显示名：**MarsGao薅羊毛领券** · id：`82640113` · **version 6**

---

## 两种运行模式（勿中途自动切换）

| 模式 | 谁点击 | 说明 |
|---|---|---|
| **GKD 辅助** | 仅已启用且验证过的规则 | 用户先进页；AI/ADB 只观察，不宣称整条任务完成 |
| **脚本任务**（短期主基线） | 本仓 `scripts/` | 先停用重叠的拼多多自动点击规则，再跑状态机 |

结果枚举：`verified` / `already_claimed` / `unavailable` / `failed` / `needs_review`  
无正向 UI 证据不得记成功；不承诺「必然领全」。

---

## 规则矩阵（拼多多 · v6）

| key | 名称 | 默认 | 状态 |
|---|---|---|---|
| 1 | 会员每日打卡（精确「打卡」） | 开 | 历史已验证；`resetMatch: app`≠自然日限额 |
| 2 | 等级礼包无门槛券（同卡关系） | 开 | 已收窄；待快照回归 |
| 3 | 已知诱导弹窗（不含开心收下/去使用） | 开 | 已收窄 |
| 4 | 进入百亿消费券会场 | **关** | 主会场常空树；用脚本进场 |
| 5 | 会场「立即领取」（消费券/双重补贴/地区专享锚点） | 开 | 已去掉「共/元券」模糊；**脚本模式请先关掉** |
| 6 | 立即点亮 | **关** | 浏览计时由脚本负责 |
| 7 | 切换地区专享 | **关** | 由脚本切 Tab 并核验 |

---

## 脚本入口

需本机 ADB、设备 `device` 状态；通用 helper 在 [GkAndroidLab](https://github.com/MarsGao/GkAndroidLab) `scripts/ecommerce/adb_ui_helper.py`。

```powershell
cd C:\GkDesktop\GitProjects\GkAndroidLabGKDCoupon
uv sync --extra dev
$env:ANDROID_SERIAL = "3B159H003D600000"

# 只观察
uv run python scripts/run_pdd_coupon_task.py --observe
uv run python scripts/claim_region_exclusive.py --observe

# 脚本任务（请先停用重叠 GKD 规则）
uv run python scripts/run_pdd_coupon_task.py --from-stage region
uv run python scripts/enter_coupon_venue.py
uv run python scripts/claim_region_exclusive.py

# 页面探查（默认不点领取；不等于 GKD 引擎验收）
uv run python scripts/verify_pdd_coupon_venue.py
```

进场图像定位需要 Pillow/NumPy；缺失时**明确失败**，不会静默改用固定坐标。仅当传入 `--allow-fallback-xy` 才允许历史坐标。

---

## 离线测试

```powershell
uv run pytest -q
```

---

## 版本

| 版本 | 日期 | 说明 |
|---|---|---|
| v6 | 2026-09-13 | 收窄规则；关 4/6/7；脚本状态机与结果枚举；文档对齐 |
| v5 | 2026-09 | 七组规则（含点亮/地区 Tab） |
| v2 | 2026-09-03 | 消费券会场相关 |
| v1 | 2026-09-03 | 打卡、等级礼包、弹窗 |

---

## 红线

不做：点「去使用」、裂变分享、下单支付；不存账号/Cookie/私信。  
不 fork 大型广告订阅。不把 Lab 旧 v1 配置回灌为发布源。

许可：[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)
