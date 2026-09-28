#!/system/bin/sh
# 将 staging 写入 GKD 私有目录。APP_UID 由调用方 sed 注入或手动改。
set -e
PKG=li.songe.gkd
PRIV=/data/data/$PKG/files
STAGE=/sdcard/Download/gkd_restore_stage
APP_UID=u0_a444

am force-stop $PKG
rm -f $PRIV/db/gkd.db-wal $PRIV/db/gkd.db-shm
cp $STAGE/gkd.db $PRIV/db/gkd.db
cp $STAGE/store.json $PRIV/store/store.json
mkdir -p $PRIV/subscription
for f in -2.json 666.json 86.json 82640113.json; do
  if [ -f "$STAGE/subscription/$f" ]; then
    cp "$STAGE/subscription/$f" "$PRIV/subscription/$f"
  fi
done
chown -R $APP_UID:$APP_UID $PRIV/db $PRIV/store $PRIV/subscription
chmod 660 $PRIV/db/gkd.db $PRIV/store/store.json
chmod 600 $PRIV/subscription/*.json 2>/dev/null || true
echo OK_DB
ls -la $PRIV/db
echo OK_STORE
ls -la $PRIV/store
echo OK_SUBS
ls -la $PRIV/subscription
