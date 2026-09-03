# MarsGao薅羊毛领券 · GKD第三方订阅规则

> 聚焦**领券 / 签到**功能类自动化，不做广告屏蔽大而全，只做刚需精准。  
> 基于 OnePlus 13 真机调试验证，规则经闭环状态确认后入库。

## 一键导入订阅

在 GKD App 中添加以下订阅地址：

```
https://raw.githubusercontent.com/MarsGao/GkAndroidLabGKDCoupon/main/dist/gkd.json5
```

## 当前规则列表

### 拼多多 `com.xunmeng.pinduoduo`

| # | 名称 | 说明 | 类别 |
|---|---|---|---|
| 1 | 百亿补贴会员每日打卡 | 进入会员页自动点「打卡」，每日最多1次 | 领券签到 |
| 2 | 会员等级礼包无门槛券领取 | 自动点「领取」，已领时文案变「去使用」规则自动失效，不进商品页 | 领券签到 |
| 3 | 关闭诱导弹窗 | 残忍拒绝 / 以后再说 / 我知道了 / 关闭按钮 | 弹窗处理 |
| 4 | 百亿补贴主会场立即领取 | 立即领取 / 一键全领 / 开心收下 | 领券签到 |

## 红线（不做的事）

- 不点「去使用」（防止跳进商品详情页）
- 不点「少拉1人」等裂变分享入口
- 不做价格谈判、下单、支付任何动作
- 不存储账号 / Cookie / 私信内容

## 版本历史

| 版本 | 日期 | 说明 |
|---|---|---|
| v1 | 2026-09-03 | 初始版本：拼多多打卡 + 等级礼包 + 弹窗 + 主会场领取 |

## 相关项目

- [GkAndroidLab](https://github.com/MarsGao/GkAndroidLab) — ADB 闭环自动化脚本（搜索/收藏/领券驱动层）
- [GKD 官方文档](https://gkd.li)
- [subscription-template](https://github.com/gkd-kit/subscription-template) — 订阅仓模板
