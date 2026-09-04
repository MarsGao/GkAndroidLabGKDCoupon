# GKD订阅 · GKD规则 · MarsGao薅羊毛领券

**GKD 第三方订阅规则**（非官方）。给 [GKD](https://gkd.li) 用的远程订阅：拼多多领券、百亿补贴打卡、无门槛券、自动签到。  
英文检索名：`GKD subscription` / `GKD rules` / `Pinduoduo coupon` / `GKD_THS_List`.

GKD App **没有官方规则市场**，默认不含规则。要找到本仓库，请用 GitHub 搜：`GKD订阅`、`GKD规则`、`GKD 领券`、`GKD 拼多多`、`MarsGao薅羊毛`。

[![GKD](https://img.shields.io/badge/GKD-第三方订阅-blue.svg)](https://gkd.li/guide/subscription)
[![订阅ID](https://img.shields.io/badge/id-82640113-green.svg)](dist/gkd.json5)
[![version](https://img.shields.io/badge/version-v2-orange.svg)](dist/gkd.version.json5)
[![license](https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-lightgrey.svg)](LICENSE)

---

## 一键导入 GKD 订阅

GKD App → 订阅 → 右上角「+」→ 粘贴下面任一 URL。

**GitHub Raw**

```text
https://raw.githubusercontent.com/MarsGao/GkAndroidLabGKDCoupon/main/dist/gkd.json5
```

**jsDelivr（国内常可用）**

```text
https://cdn.jsdelivr.net/gh/MarsGao/GkAndroidLabGKDCoupon@main/dist/gkd.json5
```

**加速镜像**

```text
https://ghfast.top/https://raw.githubusercontent.com/MarsGao/GkAndroidLabGKDCoupon/main/dist/gkd.json5
```

订阅显示名：**MarsGao薅羊毛领券** · 作者：**MarsGao** · 订阅标识：`82640113`  
规则文件：[`dist/gkd.json5`](dist/gkd.json5)

---

## 这是什么 / 不是什么

| 是 | 不是 |
|---|---|
| GKD 远程订阅、GKD 规则、第三方订阅 | GKD 官方规则、应用商店里的「精选」 |
| 拼多多领券、签到、打卡、关诱导弹窗 | 全网 App 广告拦截大全 |
| 个人维护（MarsGao） | 企业订阅、高昌机电官方规则 |

同类广告拦截订阅可看 [GKD_THS_List](https://github.com/Adpro-Team/GKD_THS_List)（社区目录，非 gkd-kit 官方）。本仓专注「薅羊毛领券」。

---

## 当前规则（拼多多 `com.xunmeng.pinduoduo`）

| # | GKD 规则 | 说明 | 状态 |
|---|---|---|---|
| 1 | 百亿补贴会员每日打卡 | 精确点「打卡」，避开「打卡送积分 / 待打卡」标题 | 已验证 |
| 2 | 等级礼包无门槛券 | 点「领取」；已领后变「去使用」，规则失效，不进商品页 | 已验证 |
| 3 | 关闭诱导弹窗 | 残忍拒绝 / 以后再说 / 我知道了 / 开心收下 / 关闭 | 已验证 |
| 4 | 百亿消费券立即领取 | 须先点「百亿消费券」进会场，再点立即领取 / 一键全领 | 待真机验证 |

---

## 在 GitHub 上怎么搜到本仓库

GitHub 搜索框可复制：

```text
GKD订阅
GKD规则
GKD 第三方订阅
GKD 领券
GKD 拼多多
GKD 百亿补贴
MarsGao薅羊毛领券
repo:MarsGao/GkAndroidLabGKDCoupon
topic:gkd-subscription
```

Topics：`gkd` `gkd-subscription` `gkd-kit` `gkd-rules` `pinduoduo` `pdd` `coupon` `android` `accessibility` `json5` `android-automation` `auto-click`

---

## GKD 官方与社区目录（避免找错地方）

- **官方** [gkd-kit](https://github.com/gkd-kit) / [gkd.li](https://gkd.li)：只有 App 和[订阅格式](https://gkd.li/guide/subscription)。[协议](https://gkd.li/guide/terms)写明默认不含规则。
- **社区名单** [Adpro-Team/GKD_THS_List](https://github.com/Adpro-Team/GKD_THS_List)：Adpro-Team / Adpro 整理的第三方订阅收录表，不是官方商店。本仓 ID `82640113` 与该表已有 ID 不冲突；规则稳定后再申请收录。

---

## 验证与红线

规则 1–3 已在 OnePlus 13 上做过闭环。规则 4 等手机连接后再用 [`scripts/verify_pdd_coupon_venue.py`](scripts/verify_pdd_coupon_venue.py) 验证（入口必须点「百亿消费券」）。

不做：点「去使用」、裂变分享、砍一刀、下单支付；不存账号 / Cookie / 私信。

---

## 版本

| 版本 | 日期 | 说明 |
|---|---|---|
| v2 | 2026-09-03 | 消费券会场「立即点亮」；检索说明 |
| v1 | 2026-09-03 | 打卡、等级礼包、弹窗、主会场领取 |

---

## 相关链接

- [GkAndroidLab](https://github.com/MarsGao/GkAndroidLab) — ADB 真机脚本
- [gkd-kit/subscription-template](https://github.com/gkd-kit/subscription-template) — 官方订阅模板
- [Adpro-Team/GKD_THS_List](https://github.com/Adpro-Team/GKD_THS_List) — 第三方订阅名单

许可：[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)
