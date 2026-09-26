---
name: gk-pdd-coupon
description: Use for the personal MarsGao Pinduoduo coupon and Billion Subsidy member check-in workflow in GkAndroidLabGKDCoupon. Uses this repository's scripts and GKD subscription as the sole business authority; does not place orders or promise every coupon can be claimed.
---

# 拼多多百亿补贴会员每日权益

## 先判断请求

- “今天做什么 / 每日领取”：按会员打卡、等级礼包、双重补贴、地区专享、点亮浏览顺序处理；积分只盘点，不自动兑换。
- “看看有什么券 / 是否值得买”：只读盘点券名称、门槛、范围、有效期和积分；没有具体商品时给一般决策原则，不推测账号权益。
- “测试某一步”：只执行用户点名的一步；不要顺手展开其他活动。
- “购买/下单”：本 Skill 只分析结算金额和优惠，停止在支付前，不提交订单。

## 唯一入口和执行器

仓库：`C:\GkDesktop\GitProjects\GkAndroidLabGKDCoupon`  
GKD 发布权威：`dist/gkd.json5` + `dist/gkd.version.json5`  
脚本状态机：`scripts/run_pdd_coupon_task.py`  
会场专用流程：`scripts/run_venue_pipeline.py`

每次先确认设备及前台页面，再选择且只选择一个执行器：

1. **GKD 辅助模式**：用户手动进入目标页，GKD 仅运行已验收的规则；ADB 只读观察，不点击。
2. **脚本任务模式**：先由用户在 GKD 界面关闭本订阅全部拼多多自动点击规则（打卡/等级券 key1/key2、会场 key5/key8 等）和其他订阅中所有重叠点击规则，再运行脚本并传 `--confirm-gkd-off`。运行后由用户恢复原开关并回读。

PC 进程锁不能证明手机 GKD 已停止。无法确认开关时，不开始脚本点击。

默认设备只在恰有一个 ADB `device` 时自动选取；多设备必须显式使用 `--serial`。不得沿用其他手机的硬编码序列号。

## 执行顺序与结果

按个人 App 当日页面执行：

1. 每日打卡领积分。
2. 领取明确可识别的等级礼包券。
3. 检查双重补贴券。
4. 检查地区专享券。
5. 有明确奖励且无需分享/拉人/视频的情况下处理点亮浏览任务。
6. 只读盘点积分兑券、有效期与适用范围；仅在存在购买计划时提出兑换建议。

结果只能使用 `verified`、`already_claimed`、`unavailable`、`failed`、`needs_review`。只读模式发现可领取/可点亮候选不代表任务完成，应标 `needs_review`；`verified` 需要同一权益的正向 UI 状态或券包记录。ADB 命令成功、节点消失、点击后页面改变、仅按钮同坐标都不够。

页面改版、空 UI 树、多个候选、未知弹窗、商品页特征、裂变文案或执行器冲突时立刻停止并报告 `needs_review`。不要继续试点。

## 购买分析边界

对比同规格商品的可信到手价，核实券的商品/地区/店铺范围、门槛、有效期、售后与保修。按真实净节省提出建议，不能为凑券门槛建议多买。自动化不得点击商品购买、提交订单或付款。

## 禁止扩展

不调用 GkAndroidLab 旧 `claim_all.py`、淘宝调度、充值中心、积分自动兑换、搜索收藏、视频流、抽福袋、分享助力或砍价流程；除非用户重新明确批准范围。
