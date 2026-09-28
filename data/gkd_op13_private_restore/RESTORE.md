# OnePlus 13 GKD 配置恢复记录（2026-09-28）

来源：[`data/gkd_mi14pro_20260928/SNAPSHOT.md`](../gkd_mi14pro_20260928/SNAPSHOT.md)
设备：OnePlus 13 `3B159H003D600000` · PJZ110 · GKD 1.12.1 · 1440×3168

## 结论

**已恢复并通过 UI 回读。** 真源在私有目录 `/data/data/li.songe.gkd/files/`，不是 `/sdcard/Android/data/...`（后者仅为旧残留/暴露副本）。

## 恢复前私有态（丢失证据）

- `subs_item` 仅 `-2` 本地订阅
- `category_config=0` · `subs_config=0`
- 私有 `subscription/` 仅 `-2.json`
- `store.enableMatch=true`

## 恢复后（UI + 私有库）

| 顺序 | 订阅 | 版本 | 总开关 |
|---:|---|---:|---|
| 1 | AIsouler `666` | 406 | 关 |
| 2 | 奥怪 `86` | 89 | 开 |
| 3 | 本地 `-2` | — | 关 |
| 4 | MarsGao `82640113` | 7 | 开 |

- UI：`规则匹配已禁用`
- `store.enableMatch=false`（对齐 mi14pro）
- `category_config=12` · `subs_config=41`（对齐 mi14pro）
- MarsGao `update_url` 使用 GitHub 正式源（不用 mi 本机 `127.0.0.1:38080`）

## 操作要点

1. `am force-stop li.songe.gkd`
2. 写入私有 `db/gkd.db`、`store/store.json`、`subscription/{ -2,666,86,82640113 }.json`
3. `chown` 为 GKD 应用 UID（本机曾为 `u0_a444`；KernelSU）
4. 启动 GKD → 订阅页 UI 回读

可复用脚本（需先准备 `subscription/*.json` 到本目录，或从发布源导入）：

- `_restore_private.py [serial] [app_uid]` — 由 mi14pro 导出 JSON 建库并 push
- `install_private.sh` — 设备端拷入私有目录

`--build-only` 仅生成本地 `gkd.db`/`store.json`，不改手机。

## 注意

- 系统无障碍：OP13 仍绑定 GKD SelectToSpeak；与 mi14pro（仅 Bitwarden）不同。当前全局匹配已关，不会自动点。若要对齐 mi 的「完全不跑引擎」，需再关系统无障碍。
- 未改动拼多多 App；未宣称领券成功。
