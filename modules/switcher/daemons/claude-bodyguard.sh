#!/bin/bash
# Claude 保镖 (参考模板) —— 安装程序会把 __HOME__ / __PROXY_MODE__ 替换为实际值后安装
# 作用: 代理(内核或TUN)离线时,自动关闭 Claude,杜绝裸连重试
LOG="__HOME__/Library/Logs/claude-bodyguard.log"
MODE="__PROXY_MODE__"

ok=1

# TUN 在线判定:存在 fake-ip 网段地址即视为 TUN 已接管
ifconfig 2>/dev/null | grep -q 'inet 198\.18\.' || ok=0

# 内核在线判定:按安装时识别的客户端分派
case "$MODE" in
    clash-verge)
        pgrep -f verge-mihomo >/dev/null 2>&1 || ok=0 ;;
    shadowrocket)
        # launchd 环境下 scutil 可能查不到 VPN 行,查不到时以 TUN 判定为准(避免误杀)
        nc=$(scutil --nc list 2>/dev/null)
        if echo "$nc" | grep -q 'com.liguangming.Shadowrocket'; then
            echo "$nc" | grep 'com.liguangming.Shadowrocket' | grep -q '(Connected)' || ok=0
        fi ;;
    sing-box)
        pgrep -f sing-box >/dev/null 2>&1 || ok=0 ;;
    clashx)
        { pgrep -x ClashX >/dev/null 2>&1 || pgrep -f clash >/dev/null 2>&1; } || ok=0 ;;
    surge)
        pgrep -f Surge >/dev/null 2>&1 || ok=0 ;;
    auto)
        : ;;  # auto 模式只查 TUN
    *)
        pgrep -f verge-mihomo >/dev/null 2>&1 || ok=0 ;;
esac

if [ "$ok" -eq 0 ]; then
    if pgrep -f '/Applications/Claude.app/Contents/MacOS/Claude' >/dev/null 2>&1; then
        pkill -f '/Applications/Claude.app/Contents/MacOS/Claude'
        echo "$(date '+%Y-%m-%d %H:%M:%S') 代理离线(内核或TUN丢失),已自动关闭 Claude" >>"$LOG"
    fi
fi
