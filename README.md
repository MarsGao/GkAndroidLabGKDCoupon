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

## GKD 生态：谁维护规则？别人怎么搜到订阅？

### GKD 官方没有规则市场

GKD 本体由 [gkd-kit](https://github.com/gkd-kit) 维护，官网 [gkd.li](https://gkd.li)。[使用协议](https://gkd.li/guide/terms) 写明：

- 应用**默认不包含任何规则内容**
- 用户需自行编写，或通过 URL 导入第三方订阅
- 官方只提供 App、选择器语法与[订阅格式](https://gkd.li/guide/subscription)，**不运营官方规则商店 / 应用内推荐榜**

因此：在 GKD App 里搜不到「官方精选订阅」。别人要找到本仓库，只能靠 GitHub 搜索、社区目录，或互相转发导入链接。

### 社区公开目录：`GKD_THS_List` 是谁维护的？

[Adpro-Team/GKD_THS_List](https://github.com/Adpro-Team/GKD_THS_List) **不是 GKD 官方项目**，而是社区整理的「第三方订阅收录名单」。

| 项 | 事实 |
|---|---|
| 维护组织 | GitHub 组织 **Adpro-Team** |
| 主要维护者 | **Adpro**（联系邮箱 `adpro_qwq@qq.com` / `adpro@adproqwq.top`） |
| 仓库用途 | 只收录订阅名、作者、订阅 ID、导入 URL、维护状态；**不托管各家规则内容** |
| 收录方式 | Fork 后只改 `list.ts`，按 [CONTRIBUTING.md](https://github.com/Adpro-Team/GKD_THS_List/blob/main/CONTRIBUTING.md) 提 PR |
| 停更判定 | 超过 **1 个月没有任何 git 提交** 视为停止维护 |

2026-09 抽样（以该仓库 `list.ts` 为准）：仍在维护的有奥怪 `id=86`、甘霖 `233`、梦念逍遥 `1`、Mrlc `2`；Adpro 自己的订阅 `825`、AIsouler `666`、九千院 `717` 已标停止维护。本仓库订阅 ID **`82640113`** 与上述已收录 ID **不冲突**。

本项目定位与上述「广告拦截大而全」订阅不同：只做领券 / 签到 / 打卡。收录 PR 等规则稳定后再提，避免刚开仓就被标停更。

### 搜索本仓库时可用的关键词

GitHub 搜索示例：`GKD 领券`、`GKD 拼多多`、`GKD 订阅 MarsGao`、`topic:gkd-subscription`。

仓库 Topics 已打：`gkd`、`gkd-subscription`、`pinduoduo`、`coupon`、`android-automation`。

---

## 当前规则列表

### 拼多多 `com.xunmeng.pinduoduo`

| # | 规则名称 | 匹配场景与触发逻辑 | 类别 | 状态 |
|---|---|---|---|---|
| 1 | **百亿补贴会员每日打卡** | 进入「百亿补贴会员」页精确点击「打卡」按钮。每天最多触发 1 次，严格避开「打卡送积分」「待打卡」等静态标题。 | 领券签到 | ✅ 活跃 |
| 2 | **会员等级礼包无门槛券领取** | 在「百亿补贴会员等级中心」，自动点击等级礼包的「领取」按钮。领完后文案自动变为「去使用」，规则天然失效，绝不误触进商品页。 | 领券签到 | ✅ 活跃 |
| 3 | **关闭诱导弹窗** | 拦截并关闭「残忍拒绝 / 以后再说 / 我知道了 / 开心收下」以及弹窗右上角关闭按钮，杜绝流氓分享裂变。 | 弹窗处理 | ✅ 活跃 |
| 4 | **百亿补贴主会场/消费券立即领取** | 须先点「百亿消费券」进入专属会场，再点「立即领取 / 一键全领 / 立即点亮 / 开心收下」。严禁「去使用」「抽福袋」。 | 领券签到 | ⏳ 待真机验证（等手机连接） |

---

## 规则真机验证与闭环保证

拒绝「点了就算成功」。规则 1–3（会员打卡、等级礼包、关弹窗）已在 OnePlus 13 上走过闭环。**规则 4（百亿消费券会场立即领取）按用户要求暂缓**，等设备重新连接后再跑 ADB。

计划路径（未执行前不当作已验证）：

1. 进入百亿补贴频道 → **必须点击「百亿消费券」** 才能进入专属会场（不能只停在主会场）。
2. Dump UI，断言会场特征后，再匹配「立即领取 / 一键全领 / 开心收下 / 立即点亮」。
3. 脚本：[`scripts/verify_pdd_coupon_venue.py`](scripts/verify_pdd_coupon_venue.py)（设备离线时会直接退出）。

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
