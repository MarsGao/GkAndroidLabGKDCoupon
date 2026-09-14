# GKD 同页多动作先后顺序：能力边界与上线方案

日期：2026-09-14 · 订阅 **v7** · 针对「地区专享立即领取」与「立即点亮+下滑浏览」同页并存。

## 结论（先看这个）

| 诉求 | GKD 能否可靠完成 | 权威做法 |
|---|---|---|
| 同页两个按钮「尽量先点 A 再点 B」 | **部分可以**（`order` + `excludeMatches`） | GKD 辅助：key8 |
| 「A 全部领完之后才允许点 B」 | **不能严格保证**（`preKeys`≠领完） | 脚本顺序闸 |
| 「点亮后浏览 ≥10s 并核验已点亮」 | **不能**（无业务计时闭环） | `run_venue_pipeline.py` |

**上线基线**：脚本任务模式编排整条流水线；GKD 只做弱约束点击，且脚本模式必须关闭 key5/key8。

## GKD 三个相关字段分别做什么

1. **`order`（数字越小越优先）**  
   多条规则同时可匹配时，优先匹配小 `order`。适合「同屏更想先点领取」。

2. **`excludeMatches`**  
   当屏幕上仍存在某选择器（如 `[text="立即领取"]`）时，本规则不匹配。  
   这是实现「有券可领就不点亮」的正确手段。

3. **`preKeys`**  
   仅表示「同组内某条规则**刚刚执行过**」。  
   **不是**「领完所有券」「队列为空」。不要用它表达业务时序终点。

另外：GKD 虽有滑动能力，但「浏览满 N 秒 + 回会场看到今日已点亮」属于状态机，应放脚本。

## v7 订阅编排（key8）

同组规则顺序：

1. `order:10` 切「地区专享」  
2. `order:20` 「立即领取」  
3. `order:30` 「立即点亮/解锁点亮」，且 `excludeMatches: 立即领取`

key5/6/7 保留为遗留单规则，**默认关闭**，避免与 key8 抢点。

## 脚本权威流水线

```text
切地区专享（核验）
  → 逐张立即领取（每张重新 dump + 正向证据）
  → 确认本观察范围无新的立即领取
  → 立即点亮/解锁点亮
  → 去看看 + 浏览计时 + 轻滑
  → 回会场核验「今日已点亮/已点亮」
```

入口：

```powershell
$env:ANDROID_SERIAL = "3B159H003D600000"
$env:PDD_CONFIRM_GKD_OFF = "1"   # 或 --confirm-gkd-off
uv run python scripts/run_venue_pipeline.py --confirm-gkd-off
# 或完整状态机（region 已排在 light 之前）
uv run python scripts/run_pdd_coupon_task.py --from-stage region --confirm-gkd-off
```

## 模式互斥（上线必做）

| 模式 | GKD key8 | 脚本 |
|---|---|---|
| GKD 辅助 | 开（用户手动进会场） | 只观察，不代点 |
| 脚本任务 | **关**（含 key5） | 执行权在脚本 |

无法通过 API 读 GKD 开关；必须 `--confirm-gkd-off` / `PDD_CONFIRM_GKD_OFF=1` 人工确认。

## 验收清单

- [ ] 订阅更新到 version **7**
- [ ] 脚本模式：key5/key8 关闭后跑通 `run_venue_pipeline.py`
- [ ] 有「立即领取」时脚本拒绝点亮（顺序闸）
- [ ] 无「立即领取」且点亮成功后，出现「今日已点亮」或等价文案才记 `verified`
- [ ] 离线 `uv run pytest -q` 通过
