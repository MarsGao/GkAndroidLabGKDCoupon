# MarsGao薅羊毛领券 · GKD 第三方订阅规则

[![GKD Subscription](https://img.shields.io/badge/GKD-Subscription-blue.svg)](https://gkd.li)
[![Subscription ID](https://img.shields.io/badge/Subscription%20ID-82640113-green.svg)](dist/gkd.json5)
[![Version](https://img.shields.io/badge/version-v2-orange.svg)](dist/gkd.version.json5)
[![Tested Device](https://img.shields.io/badge/Verified%20On-OnePlus%2013-red.svg)](https://github.com/MarsGao/GkAndroidLab)
[![License](https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-lightgrey.svg)](LICENSE)

> 💡 **定位声明**：聚焦**领券 / 签到 / 每日打卡**等刚需功能自动化，不做大而全的广告拦截，专精电商高频羊毛。  
> 📱 **真机验证**：基于 OnePlus 13（ColorOS / Android 16 / 1440×3168 高清屏）真机 ADB + Accessibility 双重闭环验证后入库。

---

## 一键导入订阅

在 **GKD App** 中点击「订阅」-> 右上角「+」添加以下订阅地址之一：

### 1. 官方推荐源 (GitHub Raw)
```text
https://raw.githubusercontent.com/MarsGao/GkAndroidLabGKDCoupon/main/dist/gkd.json5
```

### 2. 国内 CDN 加速源 (jsDelivr)
```text
https://cdn.jsdelivr.net/gh/MarsGao/GkAndroidLabGKDCoupon@main/dist/gkd.json5
```

### 3. 国内代理加速源 (ghproxy)
```text
https://ghfast.top/https://raw.githubusercontent.com/MarsGao/GkAndroidLabGKDCoupon/main/dist/gkd.json5
```

---

## GKD 生态与第三方订阅说明

### GKD 官方是否有公开规则市场？
**没有**。出于法律合规、平台政策及广告对抗风险考量，GKD 官方 (`gkd-kit`) 仅提供软件框架与格式规范（[gkd.li](https://gkd.li)），**刻意不维护任何官方集中式规则市场**。

### 社区如何发现与收录规则？
目前 GKD 社区主要依赖第三方自治列表进行收录与索引，其中最主流的公共目录是由社区维护的：
- [Adpro-Team/GKD_THS_List](https://github.com/Adpro-Team/GKD_THS_List)（Adpro-Team 整理的 GKD 第三方订阅列表）。
- 该列表收录符合开源规范、一个月内有活跃提交且无违规行为的订阅仓库。
- 本项目遵循 GKD 官方订阅规范标准（订阅标识 `82640113`），已符合收录要求。

---

## 当前规则列表

### 拼多多 `com.xunmeng.pinduoduo`

| # | 规则名称 | 匹配场景与触发逻辑 | 类别 | 状态 |
|---|---|---|---|---|
| 1 | **百亿补贴会员每日打卡** | 进入「百亿补贴会员」页精确点击「打卡」按钮。每天最多触发 1 次，严格避开「打卡送积分」「待打卡」等静态标题。 | 领券签到 | ✅ 活跃 |
| 2 | **会员等级礼包无门槛券领取** | 在「百亿补贴会员等级中心」，自动点击等级礼包的「领取」按钮。领完后文案自动变为「去使用」，规则天然失效，绝不误触进商品页。 | 领券签到 | ✅ 活跃 |
| 3 | **关闭诱导弹窗** | 拦截并关闭「残忍拒绝 / 以后再说 / 我知道了 / 开心收下」以及弹窗右上角关闭按钮，杜绝流氓分享裂变。 | 弹窗处理 | ✅ 活跃 |
| 4 | **百亿补贴主会场/消费券立即领取** | 在百亿补贴主会场与「百亿消费券」专属会场，自动点击「立即领取 / 一键全领 / 立即点亮 / 开心收下」。严禁点击「去使用」与「抽福袋」。 | 领券签到 | ✅ 活跃 |

---

## 规则真机验证与闭环保证

本项目所有规则均拒绝「开环盲点」（点了就算成功），坚持「状态机闭环确认」：

1. **会场准入路径验证**：
   - 首页 -> 百亿补贴频道 -> 点击 **「百亿消费券」** 入口卡片 -> 直达 **消费券专属会场**（`com.xunmeng.pinduoduo.activity.NewPageActivity`）。
2. **节点特征断言**：
   - 经真机 dump 验证，消费券会场内 3 张优惠券对应 `TextView` 控件，文案均为 `立即领取`（坐标区间：`[154,1267]`、`[619,1267]`、`[1085,1267]`）。
   - 顶部 8 天连续打卡福利对应 `TextView` 文案为 `立即点亮`（坐标区间：`[1046,521]`），同样纳入自动化覆盖。
3. **自动化测试套件**：
   - 本项目内置自动化验证脚本：[`scripts/verify_pdd_coupon_venue.py`](scripts/verify_pdd_coupon_venue.py)，可通过 ADB 自动化驱动导航、入场点击与节点断言。

---

## 严格红线（坚决不做的事）

- 🚫 **绝不点击「去使用」**：防止脚本跳进商品详情页造成不可逆的状态流转。
- 🚫 **绝不点击「抽福袋 / 邀请好友 / 砍一刀」**：严格避开裂变、微信分享、抽奖福袋等骚扰逻辑。
- 🚫 **绝不触碰支付流程**：不做任何议价、下单、付款动作。
- 🚫 **零隐私收集**：不读取、不存储任何用户账号凭据、Cookie 或聊天私信。

---

## 版本历史

| 版本 | 日期 | 更新内容 |
|---|---|---|
| **v2** | 2026-09-03 | 增强百亿补贴主会场/百亿消费券会场规则，新增「立即点亮」签到覆盖；补充真机验证工具与 SEO 索引。 |
| **v1** | 2026-09-03 | 初始版本：拼多多百亿补贴会员打卡 + 等级礼包无门槛券 + 弹窗处理 + 主会场领取。 |

---

## 关键词 / SEO Tags

`GKD` `GKD订阅` `GKD规则` `GKD第三方规则` `GKD领券` `拼多多领券` `百亿补贴打卡` `百亿消费券` `无门槛券` `自动签到` `薅羊毛` `Android自动化` `OnePlus 13` `GKD_subscription` `GKD_THS_List`

---

## 相关项目

- [GkAndroidLab](https://github.com/MarsGao/GkAndroidLab) — ADB 驱动层与真机自动化实验室
- [GKD 官方网站与文档](https://gkd.li)
- [Adpro-Team/GKD_THS_List](https://github.com/Adpro-Team/GKD_THS_List) — 社区第三方订阅汇总
- [subscription-template](https://github.com/gkd-kit/subscription-template) — GKD 官方订阅模板仓
