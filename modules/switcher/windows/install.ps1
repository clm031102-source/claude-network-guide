# Claude 网络指南 账号工具 Windows 版 - 安装器
# 右键 -> 使用 PowerShell 以管理员身份运行(或在管理员 PowerShell 里执行)
$ErrorActionPreference = 'Stop'
$BASE = "$env:USERPROFILE\.claude-switcher"
$CLASH_DIR = @(
    "$env:APPDATA\io.github.clash-verge-rev.clash-verge-rev",
    "$env:LOCALAPPDATA\io.github.clash-verge-rev.clash-verge-rev"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "  Claude 账号切换器 · Windows 安装" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# ---- 0. 前置检查 + 代理客户端探测 ----
$PROXY_MODE = $null
if ($CLASH_DIR) {
    $PROXY_MODE = 'clash-verge'
} elseif (Get-Process -Name 'sing-box' -ErrorAction SilentlyContinue) {
    $PROXY_MODE = 'sing-box'
} elseif (Get-Process -Name 'ClashX' -ErrorAction SilentlyContinue) {
    $PROXY_MODE = 'clashx'
} elseif (Get-Process -Name 'Surge' -ErrorAction SilentlyContinue) {
    $PROXY_MODE = 'surge'
} elseif (Get-Service -Name 'WireGuardTunnel*' -ErrorAction SilentlyContinue | Where-Object Status -eq 'Running') {
    $PROXY_MODE = 'wireguard'
}
if (-not $PROXY_MODE) {
    Write-Host "未自动识别到代理客户端,请选择:" -ForegroundColor Yellow
    Write-Host "  1) clash-verge  2) sing-box  3) clashx  4) surge"
    Write-Host "  5) wireguard    6) other(仅TUN)  7) auto(任一命中即活)"
    $pick = Read-Host "请输入序号或名称(直接回车=auto)"
    switch ($pick) {
        '1' { $PROXY_MODE = 'clash-verge' }
        '2' { $PROXY_MODE = 'sing-box' }
        '3' { $PROXY_MODE = 'clashx' }
        '4' { $PROXY_MODE = 'surge' }
        '5' { $PROXY_MODE = 'wireguard' }
        '6' { $PROXY_MODE = 'other' }
        '7' { $PROXY_MODE = 'auto' }
        'clash-verge' { $PROXY_MODE = 'clash-verge' }
        'sing-box'    { $PROXY_MODE = 'sing-box' }
        'clashx'      { $PROXY_MODE = 'clashx' }
        'surge'       { $PROXY_MODE = 'surge' }
        'wireguard'   { $PROXY_MODE = 'wireguard' }
        'other'       { $PROXY_MODE = 'other' }
        'auto'        { $PROXY_MODE = 'auto' }
        default       { $PROXY_MODE = 'auto' }
    }
}
Write-Host "[OK] 代理客户端: $PROXY_MODE" -ForegroundColor Green
Write-Host "[OK] 前置检查通过" -ForegroundColor Green

# ---- 1. 出口国家探测(多源兜底;不能是 CN,否则时区会锁错) ----
$countryTz = @{
    'US' = 'America/New_York'; 'JP' = 'Asia/Tokyo'; 'TW' = 'Asia/Taipei'
    'HK' = 'Asia/Hong_Kong'; 'SG' = 'Asia/Singapore'; 'GB' = 'Europe/London'
    'DE' = 'Europe/Berlin'; 'FR' = 'Europe/Paris'; 'KR' = 'Asia/Seoul'
    'AU' = 'Australia/Sydney'; 'CA' = 'America/Toronto'
}

function Get-GeoInfo {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $headers = @{ 'User-Agent' = 'claude-switcher-installer/1.0' }
    $diag = New-Object System.Collections.Generic.List[string]
    $first = $null
    $sources = @(
        @{ Name = 'ipinfo'; Url = 'https://ipinfo.io/json'; Country = 'country'; Timezone = 'timezone' },
        @{ Name = 'ipapi'; Url = 'https://ipapi.co/json/'; Country = 'country_code'; Timezone = 'timezone' },
        @{ Name = 'ifconfig'; Url = 'https://ifconfig.co/json'; Country = 'country_iso'; Timezone = 'timezone' }
    )
    foreach ($src in $sources) {
        try {
            $data = Invoke-RestMethod -Uri $src.Url -Headers $headers -TimeoutSec 8 -ErrorAction Stop
        } catch {
            $reason = '超时/连接失败'
            try {
                if ($_.Exception.Response) { $reason = 'HTTP ' + [int]$_.Exception.Response.StatusCode }
            } catch {}
            $diag.Add("$($src.Name) $reason")
            continue
        }
        $ccField = $src.Country
        $tzField = $src.Timezone
        $cc = [string]$data.$ccField
        $tz = [string]$data.$tzField
        if ($cc -notmatch '^[A-Z]{2}$') { $diag.Add("$($src.Name) 国家字段无效"); continue }
        if ($tz -notmatch '^[A-Za-z_]+/[A-Za-z_]+(/[A-Za-z_]+)?$') { $tz = $countryTz[$cc] }
        if (-not $tz) { $tz = 'America/New_York' }
        if (-not $first) {
            $first = [pscustomobject]@{ Country = $cc; Timezone = $tz; Source = $src.Name; Ip = [string]$data.ip }
        } elseif ($cc -ne $first.Country) {
            Write-Host "[WARN] 出口国家不一致($($first.Source)=$($first.Country) $($src.Name)=$cc),采用优先级更高的 $($first.Source)" -ForegroundColor Yellow
        }
    }
    # Cloudflare trace 兜底(无时区,按国家默认)
    try {
        $trace = Invoke-WebRequest -Uri 'https://www.cloudflare.com/cdn-cgi/trace' -Headers $headers -TimeoutSec 8 -UseBasicParsing -ErrorAction Stop
        $loc = $null; $tip = ''
        foreach ($line in ($trace.Content -split "`r?`n")) {
            if ($line -match '^loc=([A-Za-z]{2})$') { $loc = $Matches[1].ToUpper() }
            if ($line -match '^ip=(\S+)$') { $tip = $Matches[1] }
        }
        if ($loc -and $loc -match '^[A-Z]{2}$') {
            $tz = $countryTz[$loc]
            if (-not $tz) { $tz = 'America/New_York' }
            if (-not $first) {
                $first = [pscustomobject]@{ Country = $loc; Timezone = $tz; Source = 'cloudflare'; Ip = $tip }
            } elseif ($loc -ne $first.Country) {
                Write-Host "[WARN] 出口国家不一致($($first.Source)=$($first.Country) cloudflare=$loc),采用优先级更高的 $($first.Source)" -ForegroundColor Yellow
            }
        } else {
            $diag.Add('cloudflare loc 无效')
        }
    } catch {
        $reason = '超时/连接失败'
        try {
            if ($_.Exception.Response) { $reason = 'HTTP ' + [int]$_.Exception.Response.StatusCode }
        } catch {}
        $diag.Add("cloudflare $reason")
    }
    $outCountry = ''; $outTz = ''; $outSource = ''; $outIp = '未知'
    if ($first) {
        $outCountry = $first.Country
        $outTz = $first.Timezone
        $outSource = $first.Source
        if ($first.Ip) { $outIp = $first.Ip }
    }
    return [pscustomobject]@{
        Country = $outCountry
        Timezone = $outTz
        Source = $outSource
        Ip = $outIp
        Diagnostics = ($diag -join '; ')
    }
}

$geo = Get-GeoInfo
$country = $geo.Country
$ianaTz = $geo.Timezone
$geoSource = $geo.Source
$ip = $geo.Ip
$FORCE = $env:FORCE
if (-not $country) {
    Write-Host "[WARN] 未能识别出口国家,各源探测结果:" -ForegroundColor Yellow
    Write-Host "   $($geo.Diagnostics)" -ForegroundColor DarkGray
    if ($FORCE) {
        $country = 'US'; $ianaTz = 'America/New_York'; $geoSource = 'force'
        Write-Host "   FORCE=1,按 US / America/New_York 继续" -ForegroundColor Yellow
    } else {
        Write-Host ""
        Write-Host "请手动选择当前出口所在地区:" -ForegroundColor Yellow
        Write-Host "  1) US   2) JP   3) TW   4) HK   5) SG   6) GB"
        Write-Host "  7) DE   8) FR   9) KR  10) AU  11) CA"
        $choices = @('US', 'JP', 'TW', 'HK', 'SG', 'GB', 'DE', 'FR', 'KR', 'AU', 'CA')
        while ($true) {
            $pick = Read-Host "请输入序号"
            if ($pick -match '^\d+$' -and [int]$pick -ge 1 -and [int]$pick -le $choices.Count) {
                $country = $choices[[int]$pick - 1]; break
            }
            if ($pick -match '^[A-Za-z]{2}$' -and ($choices -contains $pick.ToUpper())) {
                $country = $pick.ToUpper(); break
            }
            Write-Host "未识别的选择,请重试" -ForegroundColor Yellow
        }
        $ianaTz = $countryTz[$country]
        $geoSource = 'manual'
    }
}
if ($country -eq 'CN' -and -not $FORCE) {
    Write-Host "X 当前出口在国内(CN),请先开启代理(TUN模式)并确认节点可用再运行" -ForegroundColor Red
    pause; exit 1
}
if ($country -eq 'CN') {
    $country = 'US'; $ianaTz = 'America/New_York'; $geoSource = 'force'
}
if (-not $ianaTz) { $ianaTz = 'America/New_York' }
$COUNTRY_TARGET = $country
Write-Host "[OK] 地区识别: 国家=$COUNTRY_TARGET 时区=$ianaTz 来源=$geoSource" -ForegroundColor Green
Write-Host "[OK] 出口: $ip ($COUNTRY_TARGET)" -ForegroundColor Green

# ---- 2. 自动识别代理组名(仅 Clash Verge) ----
$grp = 'GLOBAL'
if ($PROXY_MODE -eq 'clash-verge' -and $CLASH_DIR) {
    $grp = $null
    $inGroups = $false; $name = $null
    foreach ($line in Get-Content "$CLASH_DIR\clash-verge.yaml" -Encoding UTF8 -ErrorAction SilentlyContinue) {
        if ($line -match '^proxy-groups:') { $inGroups = $true; continue }
        if ($inGroups -and $line -match '^[a-zA-Z]') { $inGroups = $false }
        if ($inGroups -and $line -match '- name:\s*(.+)') { $name = $Matches[1].Trim('"',"'",' ') }
        if ($inGroups -and $line -match 'type:\s*select') { $grp = $name; break }
    }
    if (-not $grp) { $grp = Read-Host "未能自动识别代理组名,请打开 Clash Verge 查看后输入" }
    if (-not $grp) { $grp = 'GLOBAL' }
    Write-Host "[OK] 代理组: $grp" -ForegroundColor Green
    if ($grp -match '[,\r\n]') {
        Write-Host "[WARN] 代理组名包含逗号或换行,规则模式可能无法写入;请改名后重跑安装器" -ForegroundColor Yellow
    }
}

# ---- 3. IANA 时区 -> Windows 时区ID ----
$tzMap = @{
    'America/New_York'    = 'Eastern Standard Time'
    'America/Chicago'     = 'Central Standard Time'
    'America/Denver'      = 'Mountain Standard Time'
    'America/Los_Angeles' = 'Pacific Standard Time'
    'America/Toronto'     = 'Eastern Standard Time'
    'America/Vancouver'   = 'Pacific Standard Time'
    'Asia/Singapore'      = 'Singapore Standard Time'
    'Asia/Tokyo'          = 'Tokyo Standard Time'
    'Asia/Seoul'          = 'Korea Standard Time'
    'Asia/Taipei'         = 'Taipei Standard Time'
    'Asia/Hong_Kong'      = 'China Standard Time'
    'Europe/London'       = 'GMT Standard Time'
    'Europe/Berlin'       = 'W. Europe Standard Time'
    'Europe/Paris'        = 'Romance Standard Time'
    'Australia/Sydney'    = 'AUS Eastern Standard Time'
    'Australia/Melbourne' = 'AUS Eastern Standard Time'
}
$tzId = $tzMap[$ianaTz]
if (-not $tzId) {
    Write-Host "[WARN] 时区 $ianaTz 无 Windows 映射,回退 Eastern Standard Time" -ForegroundColor Yellow
    $tzId = 'Eastern Standard Time'
}
$TZ_TARGET = $tzId
Write-Host "[OK] 锁定时区: $TZ_TARGET (按出口IP识别)" -ForegroundColor Green

# ---- 4. 安装文件 ----
New-Item -ItemType Directory -Force -Path $BASE | Out-Null
Copy-Item "$PSScriptRoot\claude-switch.ps1"   "$BASE\claude-switch.ps1" -Force
Copy-Item "$PSScriptRoot\SwitcherUI.ps1"      "$BASE\SwitcherUI.ps1" -Force
Copy-Item "$PSScriptRoot\claude-bodyguard.ps1" "$BASE\claude-bodyguard.ps1" -Force

# 写入探测到的客户端模式/代理组名/国家/时区(替换串里的 $ 用 $$ 转义,避免被当作捕获组)
$core = Get-Content "$BASE\claude-switch.ps1" -Raw
$modeEsc = $PROXY_MODE.Replace('$', '$$')
$countryEsc = $COUNTRY_TARGET.Replace('$', '$$')
$tzEsc = $TZ_TARGET.Replace('$', '$$')
$grpEsc = $grp.Replace('$', '$$')
$core = $core -replace '\$PROXY_MODE = "[^"]*"', ('$$PROXY_MODE = "' + $modeEsc + '"')
$core = $core -replace '\$COUNTRY_TARGET = "[^"]*"', ('$$COUNTRY_TARGET = "' + $countryEsc + '"')
$core = $core -replace '\$TZ_TARGET = "[^"]*"', ('$$TZ_TARGET = "' + $tzEsc + '"')
$core = $core -replace '\$PROXY_GROUP = "[^"]*"', ('$$PROXY_GROUP = "' + $grpEsc + '"')
# 强制写回 UTF-8 BOM:计划任务用 powershell.exe 5.1 读取,无 BOM 会把中文读成乱码
$utf8Bom = New-Object System.Text.UTF8Encoding -ArgumentList $true
[System.IO.File]::WriteAllText("$BASE\claude-switch.ps1", $core, $utf8Bom)
$PROXY_MODE | Out-File -Encoding ascii -NoNewline "$BASE\proxy-mode.txt"

# 版本号由 release 打包时写入 zip 根的 VERSION;开发目录没有该文件则记为 unknown
$versionSrc = Join-Path $PSScriptRoot '..\VERSION'
if (-not (Test-Path -LiteralPath $versionSrc)) { $versionSrc = Join-Path $PSScriptRoot 'VERSION' }
$appVersion = 'unknown'
if (Test-Path -LiteralPath $versionSrc) {
    $rawVersion = Get-Content -LiteralPath $versionSrc -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    if ($null -ne $rawVersion -and ([string]$rawVersion).Trim()) { $appVersion = ([string]$rawVersion).Trim() }
}
[System.IO.File]::WriteAllText((Join-Path $BASE 'version.txt'), $appVersion, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "[OK] 版本: $appVersion" -ForegroundColor Green
Write-Host "[OK] 核心文件已安装到 $BASE (代理模式: $PROXY_MODE)" -ForegroundColor Green

# ---- 5. 桌面快捷方式 ----
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut("$env:USERPROFILE\Desktop\Claude网络指南账号工具.lnk")
$sc.TargetPath = "powershell.exe"
$sc.Arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$BASE\SwitcherUI.ps1`""
$sc.WorkingDirectory = $BASE
$sc.Save()
Write-Host "[OK] 桌面快捷方式已创建" -ForegroundColor Green

# ---- 6. 置顶规则:安装阶段不再写 Merge.yaml/Script.js ----
if ($PROXY_MODE -eq 'clash-verge') {
    Write-Host "[OK] 未改动 Clash 规则;请安装后打开切换器点一次「一键修复」完成规则配置" -ForegroundColor Yellow
    Write-Host "     修复会先识别 Clash 模式:全局/直连模式跳过规则,规则模式写入 profiles\Script.js" -ForegroundColor Yellow
} else {
    Write-Host "[OK] 非 Clash Verge:请在你的代理客户端中为 Claude 域名添加置顶/直连规则" -ForegroundColor Yellow
}

# ---- 7. 系统级配置 ----
Set-TimeZone -Id $TZ_TARGET
Get-NetAdapterBinding -ComponentID ms_tcpip6 -ErrorAction SilentlyContinue | Where-Object { $_.Enabled } | Disable-NetAdapterBinding -Confirm:$false
Clear-DnsClientCache
Write-Host "[OK] 时区已锁定 / IPv6 已关闭 / DNS 缓存已刷新" -ForegroundColor Green

# ---- 8. 注册保镖计划任务 ----
$action  = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$BASE\claude-bodyguard.ps1`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName 'ClaudeBodyguard' -Action $action -Trigger $trigger -Force | Out-Null
Stop-ScheduledTask -TaskName 'ClaudeBodyguard' -ErrorAction SilentlyContinue
Start-ScheduledTask -TaskName 'ClaudeBodyguard'
Write-Host "[OK] 保镖已注册并启动(计划任务,登录自动运行)" -ForegroundColor Green

# ---- 9. 重启 Clash 使规则生效(仅 Clash Verge) ----
if ($PROXY_MODE -eq 'clash-verge') {
    Get-Process -Name 'clash-verge','Clash Verge' -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep 2
    $cv = Get-ChildItem "$env:LOCALAPPDATA\Programs" -Recurse -Filter 'Clash Verge*.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cv) { Start-Process $cv.FullName }
}

Write-Host ""
Write-Host "==================================" -ForegroundColor Green
Write-Host "  安装完成! 双击桌面「Claude网络指南账号工具」使用" -ForegroundColor Green
Write-Host "  首次使用: 打开后选账号A(自动收编当前登录)" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green
pause
