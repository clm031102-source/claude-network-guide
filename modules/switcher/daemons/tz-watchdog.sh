#!/bin/bash
# 时区看门狗 (参考模板) —— 安装程序会把 __TZ_TARGET__ 和 __HOME__ 替换后安装
# 作用: 系统时区偏离目标值时自动改回,并记录日志
TARGET="__TZ_TARGET__"
LOG="__HOME__/Library/Logs/tz-watchdog.log"

current=$(readlink /etc/localtime 2>/dev/null)
if [ "$current" != "/var/db/timezone/zoneinfo/$TARGET" ]; then
    /usr/sbin/systemsetup -settimezone "$TARGET" >>"$LOG" 2>&1
    echo "$(date '+%Y-%m-%d %H:%M:%S %Z') 时区异常: [$current] 已自动恢复为 $TARGET" >>"$LOG"
fi
