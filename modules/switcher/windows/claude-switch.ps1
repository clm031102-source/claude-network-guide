# Claude 账号切换器 - Windows 核心脚本
# 用法: powershell -NoProfile -File claude-switch.ps1 check|status|switch A|B|checkdetail|fix|check-update|update-now
$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}

# ============ 安装时可配置项(安装器自动改写) ============
$PROXY_MODE = "clash-verge"            # 代理客户端: clash-verge|sing-box|clashx|surge|wireguard|other|auto
$COUNTRY_TARGET = "US"                 # 目标出口国家(安装时按出口自动识别)
$TZ_TARGET = "Eastern Standard Time"   # Windows 时区ID
$PROXY_GROUP = "GLOBAL"                # Clash 代理组名
# =======================================================

$BASE = Join-Path $env:USERPROFILE ".claude-switcher"
$DATA = Join-Path $env:APPDATA "Claude"
$LOG  = Join-Path $BASE "claude-switch.log"
$CLASH_DIR = @(
    (Join-Path $env:APPDATA "io.github.clash-verge-rev.clash-verge-rev"),
    (Join-Path $env:LOCALAPPDATA "io.github.clash-verge-rev.clash-verge-rev")
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $CLASH_DIR) { $CLASH_DIR = Join-Path $env:APPDATA "io.github.clash-verge-rev.clash-verge-rev" }
# check-update 必须只读:不在检查路径上创建任何目录
if ($args.Count -eq 0 -or $args[0] -ne 'check-update') {
    New-Item -ItemType Directory -Force -Path "$BASE\accounts" | Out-Null
}

function Log($m) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m" | Out-File -Append -Encoding utf8 $LOG }

# 当前安装版本(安装器/更新器写入 version.txt,缺失视为 unknown)
function Get-AppVersion {
    $vf = Join-Path $BASE "version.txt"
    if (Test-Path -LiteralPath $vf) {
        try {
            $raw = Get-Content -LiteralPath $vf -Raw -Encoding UTF8 -ErrorAction Stop
            if ($null -ne $raw) {
                $v = ([string]$raw).Trim()
                if ($v) { return $v }
            }
        } catch {}
    }
    return 'unknown'
}

# 版本号按 . 分段比较,每段只取前导数字(忽略 -beta 等后缀);unknown 视为最旧
function ConvertTo-VersionParts([string]$v) {
    if ([string]::IsNullOrWhiteSpace($v)) { return @() }
    $clean = $v.Trim().TrimStart('v', 'V')
    if ($clean -eq 'unknown') { return @() }
    return @($clean.Split('.'))
}

function Compare-Version([string]$a, [string]$b) {
    $pa = @(ConvertTo-VersionParts $a)
    $pb = @(ConvertTo-VersionParts $b)
    $ua = ($pa.Count -eq 0)
    $ub = ($pb.Count -eq 0)
    if ($ua -and $ub) { return 0 }
    if ($ua) { return -1 }
    if ($ub) { return 1 }
    $n = [Math]::Max($pa.Count, $pb.Count)
    for ($i = 0; $i -lt $n; $i++) {
        $na = 0; $nb = 0
        if ($i -lt $pa.Count) {
            $m = [regex]::Match([string]$pa[$i], '^\d+')
            if ($m.Success) { $na = [int64]$m.Value }
        }
        if ($i -lt $pb.Count) {
            $m = [regex]::Match([string]$pb[$i], '^\d+')
            if ($m.Success) { $nb = [int64]$m.Value }
        }
        if ($na -lt $nb) { return -1 }
        if ($na -gt $nb) { return 1 }
    }
    return 0
}

# 只允许从 GitHub 官方域名下载更新资产
function Test-GitHubDownloadUrl([string]$url) {
    if ([string]::IsNullOrWhiteSpace($url)) { return $false }
    try { $u = [Uri]$url } catch { return $false }
    if ($u.Scheme -ne 'https') { return $false }
    $allowed = @('github.com', 'api.github.com', 'objects.githubusercontent.com',
                 'github-releases.githubusercontent.com', 'codeload.github.com')
    return ($allowed -contains $u.Host.ToLowerInvariant())
}

function Get-ScriptConfigValue([string]$text, [string]$name) {
    $m = [regex]::Match($text, '(?m)^[ \t]*\$' + [regex]::Escape($name) + '[ \t]*=[ \t]*"([^"]*)"')
    if ($m.Success) { return $m.Groups[1].Value }
    return $null
}

function Set-ScriptConfigValue([string]$text, [string]$name, [string]$value) {
    $pattern = '(?m)^([ \t]*\$' + [regex]::Escape($name) + '[ \t]*=[ \t]*")[^"]*(")'
    $replacement = '${1}' + $value.Replace('$', '$$') + '${2}'
    return [regex]::Replace($text, $pattern, $replacement)
}

# 代理客户端显示名(供检查细节输出)
function Get-ProxyName {
    switch ($PROXY_MODE) {
        'clash-verge' { return 'Clash Verge' }
        'sing-box'    { return 'sing-box' }
        'clashx'      { return 'ClashX' }
        'surge'       { return 'Surge' }
        'wireguard'   { return 'WireGuard' }
        'other'       { return '其他代理客户端' }
        'auto'        { return '代理客户端(auto)' }
        default       { return $PROXY_MODE }
    }
}

# 代理客户端在线判定:按安装时识别的客户端分派;auto 任一命中即活,other 只依赖 TUN
function Test-ProxyAlive {
    switch ($PROXY_MODE) {
        'clash-verge' { return [bool](Get-Process -Name 'verge-mihomo' -ErrorAction SilentlyContinue) }
        'sing-box'    { return [bool](Get-Process -Name 'sing-box' -ErrorAction SilentlyContinue) }
        'clashx'      { return [bool](Get-Process -Name 'ClashX' -ErrorAction SilentlyContinue) }
        'surge'       { return [bool](Get-Process -Name 'Surge' -ErrorAction SilentlyContinue) }
        'wireguard'   { return [bool](Get-Service -Name 'WireGuardTunnel*' -ErrorAction SilentlyContinue | Where-Object Status -eq 'Running') }
        'other'       { return $true }
        'auto' {
            if (Get-Process -Name 'verge-mihomo','sing-box','ClashX','Surge' -ErrorAction SilentlyContinue) { return $true }
            return [bool](Get-Service -Name 'WireGuardTunnel*' -ErrorAction SilentlyContinue | Where-Object Status -eq 'Running')
        }
        default { return [bool](Get-Process -Name 'verge-mihomo' -ErrorAction SilentlyContinue) }
    }
}

# TUN 在线判定:198.18 假IP段优先,否则回退到任意 Up 状态的虚拟网卡(兼容 Astrill/WireGuard/OpenVPN 等)
function Get-TunStatus {
    if (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -like '198.18.*' }) {
        return @{ up = $true; detail = '198.18 假IP段' }
    }
    $nic = Get-NetAdapter -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq 'Up' -and ($_.InterfaceDescription -match 'TAP|TUN|WireGuard|Wintun|VPN|Tailscale') }
    if ($nic) { return @{ up = $true; detail = '通用虚拟网卡' } }
    return @{ up = $false; detail = '不在线' }
}
function Test-TunUp {
    $t = Get-TunStatus
    return [bool]$t.up
}

function Get-Egress {
    $trace = & curl.exe -s --max-time 8 "https://www.cloudflare.com/cdn-cgi/trace" 2>$null
    $ip  = (($trace -split "`n" | Where-Object { $_ -like 'ip=*' })  -replace 'ip=','').Trim()
    $loc = (($trace -split "`n" | Where-Object { $_ -like 'loc=*' }) -replace 'loc=','').Trim()
    return @{ ip = $ip; loc = $loc }
}

# STUN 探针(纯 .NET UDP,手工构造 RFC5389 报文)
function Get-StunPublicIP([string]$server, [int]$port, [int]$timeoutMs = 2000) {
    try { $addr = ([System.Net.Dns]::GetHostAddresses($server) | Where-Object { $_.AddressFamily -eq 'InterNetwork' } | Select-Object -First 1) } catch { return $null }
    if (-not $addr) { return $null }
    $udp = New-Object System.Net.Sockets.UdpClient
    $udp.Client.ReceiveTimeout = $timeoutMs
    try {
        $txn = New-Object byte[] 12; (New-Object Random).NextBytes($txn)
        $req = [byte[]](0x00, 0x01, 0x00, 0x00) + [byte[]](0x21, 0x12, 0xA4, 0x42) + $txn
        $udp.Connect($addr, $port)
        [void]$udp.Send($req, $req.Length)
        $remote = New-Object System.Net.IPEndPoint([System.Net.IPAddress]::Any, 0)
        $resp = $udp.Receive([ref]$remote)
        $pos = 20
        while ($pos + 4 -le $resp.Length) {
            $atype = ([int]$resp[$pos] -shl 8) -bor $resp[$pos + 1]
            $alen  = ([int]$resp[$pos + 2] -shl 8) -bor $resp[$pos + 3]
            if (($atype -eq 0x20 -or $atype -eq 0x01) -and $alen -ge 8 -and $resp[$pos + 5] -eq 0x01) {
                $ipBytes = @($resp[$pos + 8], $resp[$pos + 9], $resp[$pos + 10], $resp[$pos + 11])
                if ($atype -eq 0x20) {
                    $cookie = [byte[]](0x21, 0x12, 0xA4, 0x42)
                    for ($i = 0; $i -lt 4; $i++) { $ipBytes[$i] = $ipBytes[$i] -bxor $cookie[$i] }
                }
                return ($ipBytes -join '.')
            }
            $pos += 4 + $alen + ((4 - ($alen % 4)) % 4)
        }
    } catch { return $null } finally { $udp.Close() }
    return $null
}

function Test-WebRTC($exitIp) {
    $servers = @(@("stun.miwifi.com", 3478), @("stun.chat.bilibili.com", 3478), @("stun.l.google.com", 19302), @("stun.cloudflare.com", 3478))
    $found = @()
    foreach ($s in $servers) {
        $r = Get-StunPublicIP $s[0] $s[1]
        if ($r -and ($found -notcontains $r)) { $found += $r }
    }
    if ($found.Count -eq 0) { return @{ code = 'ok'; detail = 'UDP不出网,零暴露' } }
    $leak = $found | Where-Object { $_ -ne $exitIp }
    if ($leak) { return @{ code = 'fail'; detail = "暴露非代理IP: $($leak -join ',')" } }
    return @{ code = 'ok'; detail = '仅暴露代理IP' }
}

function Find-ClashVerge {
    # 优先取正在运行进程的真实路径(最可靠),再回退到常见安装目录
    $running = Get-Process -Name 'clash-verge','Clash Verge' -ErrorAction SilentlyContinue |
        Where-Object { $_.Path } | Select-Object -First 1
    if ($running) { return $running.Path }
    $roots = @("$env:LOCALAPPDATA\Programs", $env:ProgramFiles,
               [Environment]::GetEnvironmentVariable('ProgramFiles(x86)'))
    foreach ($root in $roots) {
        if (-not $root) { continue }
        $hit = Get-ChildItem $root -Recurse -Filter "Clash Verge*.exe" -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($hit) { return $hit.FullName }
    }
    return $null
}

# 切换器管理的 13 个 Claude 域名 + 3 个 STUN 端口
$CLAUDE_DOMAINS = @(
    'claude.ai', 'claude.com', 'anthropic.com', 'claudeusercontent.com',
    'challenges.cloudflare.com', 'datadoghq.com', 'segment.io', 'stripe.com',
    'stripe.network', 'stripecdn.com', 'intercom.io', 'intercomcdn.com', 'intercomassets.com'
)
$CLAUDE_PORTS = @('3478', '5349', '19302')

# 读取 YAML 中第一个 key: value 标量(只用于 clash-verge.yaml / verge.yaml 的顶层字段)
function Get-YamlScalar([string]$path, [string]$key) {
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    try {
        foreach ($line in Get-Content -LiteralPath $path -Encoding UTF8 -ErrorAction Stop) {
            if ($line -match ('^\s*' + [regex]::Escape($key) + '\s*:\s*(.*?)\s*$')) {
                $v = $Matches[1].Trim()
                $v = $v -replace '\s+#.*$', ''
                $v = $v.Trim('"').Trim("'")
                return $v
            }
        }
    } catch {}
    return $null
}

# 解析 Clash 控制接口;Windows 版不使用 unix socket
function Get-ClashApi {
    foreach ($name in @('clash-verge.yaml', 'config.yaml')) {
        $yaml = Join-Path $CLASH_DIR $name
        $addr = Get-YamlScalar $yaml 'external-controller'
        if ([string]::IsNullOrWhiteSpace($addr)) { continue }
        if ($addr -match '^unix://' -or $addr -match '^/') { continue }
        $addr = $addr -replace '^0\.0\.0\.0:', '127.0.0.1:'
        $addr = $addr -replace '^:', '127.0.0.1:'
        if ($addr -notmatch '^https?://') { $addr = 'http://' + $addr }
        $base = $addr.TrimEnd('/')
        $secret = Get-YamlScalar $yaml 'secret'
        $headers = @{}
        if (-not [string]::IsNullOrWhiteSpace($secret)) { $headers['Authorization'] = 'Bearer ' + $secret }
        return @{ base = $base; headers = $headers }
    }
    return $null
}

# 返回 global|rule|direct|unknown;API 优先,失败再读 YAML
function Get-ClashMode {
    try {
        $api = Get-ClashApi
        if ($api) {
            try {
                $params = @{ Uri = ($api.base + '/configs'); TimeoutSec = 3; ErrorAction = 'Stop' }
                if ($api.headers.Count -gt 0) { $params['Headers'] = $api.headers }
                $resp = Invoke-RestMethod @params
                $m = ([string]$resp.mode).Trim().ToLowerInvariant()
                if ($m -eq 'global' -or $m -eq 'rule' -or $m -eq 'direct') { return $m }
            } catch {}
        }
        foreach ($name in @('clash-verge.yaml', 'verge.yaml')) {
            $p = Join-Path $CLASH_DIR $name
            if (-not (Test-Path -LiteralPath $p)) { continue }
            foreach ($line in Get-Content -LiteralPath $p -Encoding UTF8 -ErrorAction SilentlyContinue) {
                if ($line -match '(?m)^mode:\s*[''"]?(\w+)') {
                    $m = $Matches[1].ToLowerInvariant()
                    if ($m -eq 'global' -or $m -eq 'rule' -or $m -eq 'direct') { return $m }
                }
            }
        }
    } catch {}
    return 'unknown'
}

function Get-ClashRules {
    try {
        $api = Get-ClashApi
        if (-not $api) { return @{ available = $false; rules = @() } }
        $params = @{ Uri = ($api.base + '/rules'); TimeoutSec = 3; ErrorAction = 'Stop' }
        if ($api.headers.Count -gt 0) { $params['Headers'] = $api.headers }
        $resp = Invoke-RestMethod @params
        return @{ available = $true; rules = @($resp.rules) }
    } catch {
        return @{ available = $false; rules = @() }
    }
}

# 内核前 16 条必须包含 13 个域名 + 3 个端口;兼容 DOMAIN-SUFFIX/DomainSuffix 与 AND(...DST-PORT...) 形式
function Test-PinnedRules($rules) {
    $head = @($rules | Select-Object -First 16)
    if ($head.Count -lt 16) { return $false }
    $domainHits = @($head | Where-Object {
        (([string]$_.type).ToLowerInvariant() -replace '[-_]', '') -eq 'domainsuffix' -and
        ($CLAUDE_DOMAINS -contains [string]$_.payload)
    } | ForEach-Object { ([string]$_.payload).ToLowerInvariant() } | Sort-Object -Unique).Count
    $portHits = @($head | ForEach-Object {
        $type = ([string]$_.type).ToLowerInvariant() -replace '[-_]', ''
        $payload = [string]$_.payload
        if ($type -eq 'dstport' -and ($CLAUDE_PORTS -contains $payload)) { $payload }
        elseif ($payload -match ('DST-PORT,(' + ($CLAUDE_PORTS -join '|') + ')(?:[,)]|$)')) {
            foreach ($p in $CLAUDE_PORTS) {
                if ($payload -match ('DST-PORT,' + [regex]::Escape($p) + '(?:[,)]|$)')) { $p }
            }
        }
    } | Sort-Object -Unique).Count
    return ($domainHits -eq $CLAUDE_DOMAINS.Count -and $portHits -eq $CLAUDE_PORTS.Count)
}

# 规则模式只写 profiles\Script.js 托管块,不再碰 Merge.yaml
function Write-ClashScriptRules {
    $result = @{ ok = $false; changed = $false; existed = $false; backup = ''; message = '' }
    $scriptPath = Join-Path $CLASH_DIR 'profiles\Script.js'
    $backup = ''
    $existed = Test-Path -LiteralPath $scriptPath
    $result.existed = $existed
    try {
        if ([string]::IsNullOrWhiteSpace($PROXY_GROUP) -or $PROXY_GROUP -match '[,\r\n]') {
            $result.message = '代理组名为空或包含逗号/换行'
            return $result
        }
        $rules = @()
        foreach ($d in $CLAUDE_DOMAINS) { $rules += "DOMAIN-SUFFIX,$d,$PROXY_GROUP" }
        foreach ($p in $CLAUDE_PORTS) { $rules += "DST-PORT,$p,$PROXY_GROUP" }
        $json = ConvertTo-Json -InputObject @($rules) -Compress
        $managed = "// >>> claude-switcher managed rules >>>`r`n" +
            "  const pinnedRules = $json;`r`n" +
            "  config.rules = pinnedRules.concat((config.rules||[]).filter(r=>!pinnedRules.includes(r)));`r`n" +
            "// <<< claude-switcher managed rules <<<"

        if (-not $existed) {
            $dir = Split-Path -Parent $scriptPath
            New-Item -ItemType Directory -Force -Path $dir -ErrorAction Stop | Out-Null
            $content = "function main(config) {`r`n" + $managed + "`r`n  return config;`r`n}`r`n"
            [System.IO.File]::WriteAllText($scriptPath, $content, (New-Object System.Text.UTF8Encoding($false)))
            $result.ok = $true
            $result.changed = $true
            $result.message = '已创建 Script.js'
            return $result
        }

        $existing = [System.IO.File]::ReadAllText($scriptPath)
        if ($existing -notmatch 'function\s+main\s*\(') {
            $result.message = 'Script.js 已存在但没有 function main(...),未改写,请手动合并'
            return $result
        }
        if ($existing -match '// >>> claude-switcher managed rules >>>') {
            $pattern = '(?s)// >>> claude-switcher managed rules >>>.*?// <<< claude-switcher managed rules <<<'
            $replacement = $managed.Replace('$', '$$')
            $updated = [regex]::Replace($existing, $pattern, $replacement)
        } else {
            $fn = [regex]::Match($existing, 'function\s+main\s*\(')
            $braceMatch = [regex]::Match($existing, 'function\s+main\s*\([^)]*\)\s*\{')
            if ($braceMatch.Success) {
                $brace = $braceMatch.Index + $braceMatch.Length - 1
            } else {
                $brace = $existing.IndexOf('{', $fn.Index + $fn.Length)
            }
            if ($brace -lt 0) {
                $result.message = 'Script.js 的 function main 缺少函数体,未改写'
                return $result
            }
            $updated = $existing.Substring(0, $brace + 1) + "`r`n" + $managed + "`r`n" + $existing.Substring($brace + 1)
        }
        if ($updated -ceq $existing) {
            $result.ok = $true
            $result.changed = $false
            $result.message = '规则已是当前版本'
            return $result
        }
        $backup = "$scriptPath.bak.$((Get-Date).ToString('yyyyMMddHHmmss'))"
        Copy-Item -LiteralPath $scriptPath -Destination $backup -Force -ErrorAction Stop
        [System.IO.File]::WriteAllText($scriptPath, $updated, (New-Object System.Text.UTF8Encoding($false)))
        $result.ok = $true
        $result.changed = $true
        $result.backup = $backup
        $result.message = '规则已写入 Script.js'
        return $result
    } catch {
        $result.ok = $false
        $result.message = $_.Exception.Message
        if ($backup -and (Test-Path -LiteralPath $backup)) {
            Copy-Item -LiteralPath $backup -Destination $scriptPath -Force -ErrorAction SilentlyContinue
        } elseif (-not $existed) {
            Remove-Item -LiteralPath $scriptPath -Force -ErrorAction SilentlyContinue
        }
        return $result
    }
}

# 清理旧版写进 Merge.yaml 的规则、多文档分隔符和重复顶层键
function Remove-LegacyMergeRules {
    $result = @{ changed = $false; backup = ''; removedRules = 0; removedDocs = 0; removedDupes = 0; message = '' }
    $mergePath = Join-Path $CLASH_DIR 'profiles\Merge.yaml'
    if (-not (Test-Path -LiteralPath $mergePath)) { return $result }
    $backup = ''
    try {
        $lines = @(Get-Content -LiteralPath $mergePath -Encoding UTF8 -ErrorAction Stop)
        $text = $lines -join "`n"
        $domainAlt = ($CLAUDE_DOMAINS | ForEach-Object { [regex]::Escape($_) }) -join '|'
        $portAlt = ($CLAUDE_PORTS | ForEach-Object { [regex]::Escape($_) }) -join '|'
        $ruleRe = '(?m)^\s*-\s*((DOMAIN-SUFFIX,(' + $domainAlt + '),)|(DST-PORT,(' + $portAlt + '),))'
        $hasRules = $text -match $ruleRe
        $hasDocs = [bool](@($lines | Where-Object { $_ -match '^\s*---\s*(#.*)?$' }).Count)
        $topKeys = @($lines | Where-Object { $_ -match '^[A-Za-z0-9_.-]+:' } | ForEach-Object { ($_ -split ':', 2)[0] })
        $hasDupes = [bool](@($topKeys | Group-Object | Where-Object { $_.Count -gt 1 }).Count)
        # 用户可能已经手动删了规则行但留下空的 prepend-rules:,同样需要清理
        $hasEmptyPrepend = $false
        for ($i = 0; $i -lt $lines.Count; $i++) {
            if ($lines[$i] -match '^\s*prepend-rules:\s*(#.*)?$') {
                $hasItem = $false
                for ($j = $i + 1; $j -lt $lines.Count; $j++) {
                    $next = [string]$lines[$j]
                    if ($next -match '^\s*$') { continue }
                    if ($next -match '^\s*#') { continue }
                    if ($next -match '^\s*-\s+') { $hasItem = $true }
                    break
                }
                if (-not $hasItem) { $hasEmptyPrepend = $true; break }
            }
        }
        if (-not $hasRules -and -not $hasDocs -and -not $hasDupes -and -not $hasEmptyPrepend) { return $result }

        $backup = "$mergePath.bak.$((Get-Date).ToString('yyyyMMddHHmmss'))"
        Copy-Item -LiteralPath $mergePath -Destination $backup -Force -ErrorAction Stop

        $out = @()
        $removedRules = 0
        $removedDocs = 0
        foreach ($line in $lines) {
            if ($line -match '^\s*---\s*(#.*)?$') { $removedDocs++; continue }
            if ($line -match $ruleRe) { $removedRules++; continue }
            $out += $line
        }

        $cleaned = @()
        for ($i = 0; $i -lt $out.Count; $i++) {
            $line = $out[$i]
            if ($line -match '^\s*prepend-rules:\s*(#.*)?$') {
                $hasItem = $false
                for ($j = $i + 1; $j -lt $out.Count; $j++) {
                    $next = [string]$out[$j]
                    if ($next -match '^\s*$') { continue }
                    if ($next -match '^\s*#') { continue }
                    if ($next -match '^\s*-\s+') { $hasItem = $true }
                    break
                }
                if (-not $hasItem) { continue }
            }
            $cleaned += $line
        }

        $final = @()
        $seen = @{}
        $skip = $false
        $removedDupes = 0
        foreach ($line in $cleaned) {
            if ($line -match '^([A-Za-z0-9_.-]+):') {
                $key = $Matches[1]
                if ($seen.ContainsKey($key)) {
                    $skip = $true
                    $removedDupes++
                    continue
                }
                $seen[$key] = $true
                $skip = $false
                $final += $line
                continue
            }
            if ($skip) { continue }
            $final += $line
        }

        $before = ($lines -join "`n")
        $after = ($final -join "`n")
        if ($after -ceq $before) {
            Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue
            return $result
        }

        if ([string]::IsNullOrWhiteSpace($after)) {
            Remove-Item -LiteralPath $mergePath -Force -ErrorAction Stop
        } else {
            [System.IO.File]::WriteAllText($mergePath, ($final -join "`r`n") + "`r`n", (New-Object System.Text.UTF8Encoding($false)))
        }
        $result.changed = $true
        $result.backup = $backup
        $result.removedRules = $removedRules
        $result.removedDocs = $removedDocs
        $result.removedDupes = $removedDupes
        $result.message = '已清理历史遗留 Merge 规则'
        return $result
    } catch {
        $result.message = $_.Exception.Message
        if ($backup -and (Test-Path -LiteralPath $backup)) {
            Copy-Item -LiteralPath $backup -Destination $mergePath -Force -ErrorAction SilentlyContinue
        }
        return $result
    }
}

function Restart-ClashVerge {
    $cv = Find-ClashVerge
    if (-not $cv) { return $false }
    Get-Process -Name 'clash-verge','Clash Verge' -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep 2
    try { Start-Process $cv } catch { return $false }
    return $true
}

function Wait-Tun([int]$seconds) {
    for ($i = 0; $i -lt $seconds; $i++) {
        if (Test-TunUp) { return $true }
        Start-Sleep 1
    }
    return [bool](Test-TunUp)
}

function Wait-ClashRules([int]$seconds) {
    $last = @{ available = $false; rules = @() }
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        $last = Get-ClashRules
        if ($last.available -and (Test-PinnedRules $last.rules)) { return $last }
        Start-Sleep 1
    }
    return $last
}

function Restore-ClashScriptChange($write) {
    if (-not $write.changed) { return }
    $scriptPath = Join-Path $CLASH_DIR 'profiles\Script.js'
    if ($write.backup -and (Test-Path -LiteralPath $write.backup)) {
        Copy-Item -LiteralPath $write.backup -Destination $scriptPath -Force -ErrorAction SilentlyContinue
    } elseif (-not $write.existed) {
        Remove-Item -LiteralPath $scriptPath -Force -ErrorAction SilentlyContinue
    }
}

function Test-ClashScriptManaged {
    $p = Join-Path $CLASH_DIR 'profiles\Script.js'
    if (-not (Test-Path -LiteralPath $p)) { return $false }
    try { return ([System.IO.File]::ReadAllText($p)) -match '// >>> claude-switcher managed rules >>>' } catch { return $false }
}

function Get-RulesStatus {
    $mode = Get-ClashMode
    if ($mode -eq 'global') { return '规则置顶=ok:全局模式(规则不适用)' }
    if ($mode -eq 'direct') { return '规则置顶=ok:直连模式(规则不适用)' }
    if ($mode -eq 'unknown') { return '规则置顶=warn:无法确认 Clash 模式,未检查规则' }
    $rulesInfo = Get-ClashRules
    if ($rulesInfo.available) {
        if (Test-PinnedRules $rulesInfo.rules) { return '规则置顶=ok' }
        return '规则置顶=fail:内核未加载置顶规则'
    }
    if (Test-ClashScriptManaged) { return '规则置顶=warn:规则已写入但无法验证内核加载' }
    return '规则置顶=fail:未配置'
}

function Invoke-CheckDetail {
    $pname = Get-ProxyName
    if (Test-ProxyAlive) {
        if ($PROXY_MODE -eq 'other') { "代理内核=ok:$pname(仅校验TUN)" }
        else { "代理内核=ok:$pname 运行中" }
    } else { "代理内核=fail:$pname 未运行" }

    $tun = Get-TunStatus
    if ($tun.up) {
        if ($tun.detail -eq '198.18 假IP段') { "TUN网卡=ok" }
        else { "TUN网卡=ok:$($tun.detail)" }
    } else { "TUN网卡=fail:不在线" }

    $e = Get-Egress
    if ($e.loc -eq $COUNTRY_TARGET) { "出口IP=ok:$($e.ip)" } else { "出口IP=fail:$($e.ip)/$($e.loc)(期望$COUNTRY_TARGET)" }

    $lastipFile = "$BASE\lastip.txt"
    $lastip = if (Test-Path $lastipFile) { (Get-Content $lastipFile -Raw).Trim() } else { '' }
    if (-not $e.ip) { "IP一致=fail:未获取到出口IP" }
    elseif (-not $lastip) { "IP一致=ok:首次记录" }
    elseif ($e.ip -eq $lastip) { "IP一致=ok" }
    else { "IP一致=warn:$lastip → $($e.ip)" }
    if ($e.ip) { $e.ip | Out-File -Encoding ascii -NoNewline $lastipFile }

    $tz = (Get-TimeZone).Id
    if ($tz -eq $TZ_TARGET) { "时区=ok" } else { "时区=fail:$tz" }

    $cult = (Get-Culture).Name
    if ($cult -eq 'en-US') { "地区=ok" } else { "地区=fail:$cult" }

    $v6off = [bool](Get-NetAdapterBinding -ComponentID ms_tcpip6 -ErrorAction SilentlyContinue | Where-Object { $_.Enabled -eq $true })
    if (-not $v6off) { "IPv6=ok:已关闭" } else { "IPv6=fail:未关闭" }

    $dns = (Resolve-DnsName claude.ai -Type A -ErrorAction SilentlyContinue | Select-Object -First 1).IPAddress
    if ($dns -like '198.18.*') { "DNS=ok:走隧道" } else { "DNS=fail:未走隧道($dns)" }

    $w = Test-WebRTC $e.ip
    "WebRTC=$($w.code):$($w.detail)"

    $bg = Get-ScheduledTask -TaskName 'ClaudeBodyguard' -ErrorAction SilentlyContinue
    if ($bg) { "保镖=ok" } else { "保镖=fail:未安装" }

    Get-RulesStatus

    # 客户端语言: Windows 端 Claude 跟随系统区域格式,地区检查已覆盖
    "客户端语言=ok:跟随系统"

    $org = ''
    try { $org = ((& curl.exe -s --max-time 6 "https://ipinfo.io/json" 2>$null) | ConvertFrom-Json).org } catch {}
    if (-not $org) { "ASN属性=warn:未获取" }
    elseif ($org -match 'Comcast|AT&T|Verizon|Spectrum|Charter|Cox|T-Mobile|Cable|esidential') { "ASN属性=ok:$org" }
    else { "ASN属性=warn:疑似机房($org)" }

    $r1 = & curl.exe -s --max-time 8 -o NUL -w '%{http_code}' "https://claude.ai/" 2>$null
    $r2 = & curl.exe -s --max-time 8 -o NUL -w '%{http_code}' "https://api.anthropic.com/v1/models" 2>$null
    if ($r1 -ne '000' -and $r2 -ne '000') { "生态可达性=ok:claude.ai:$r1 api:$r2" } else { "生态可达性=fail:claude.ai:$r1 api:$r2" }
}

function Invoke-Fix {
    "FIX:开始一键修复"

    # A. 拉起代理客户端并等待内核+TUN(仅 Clash Verge 可自动拉起)
    if ($PROXY_MODE -eq 'clash-verge') {
        if (-not (Test-ProxyAlive)) {
            "FIX:正在启动 Clash Verge..."
            $cv = Find-ClashVerge
            if ($cv) { Start-Process $cv } else { "FIX:未找到 Clash Verge 可执行文件,请手动启动" }
        }
        $ok = $false
        for ($i = 0; $i -lt 40; $i++) { if ((Test-ProxyAlive) -and (Test-TunUp)) { $ok = $true; break }; Start-Sleep 1 }
        if ($ok) { "FIX:代理内核+TUN ✓" } else { "FIX:代理内核/TUN ✗(请打开 Clash Verge 检查节点/线路及 TUN 开关)" }
    } else {
        $pname = Get-ProxyName
        if ((Test-ProxyAlive) -and (Test-TunUp)) { "FIX:代理客户端($pname)+TUN ✓" }
        elseif (-not (Test-ProxyAlive)) { "FIX:代理客户端($pname)未运行,请手动启动并开启 TUN 模式" }
        else { "FIX:TUN 未在线($pname),请检查客户端 TUN 开关" }
    }

    # B. 时区/IPv6/DNS/保镖(需管理员:通过 UAC 弹一次)
    $adminScript = @()
    if ((Get-TimeZone).Id -ne $TZ_TARGET) { $adminScript += "Set-TimeZone -Id '$TZ_TARGET'" }
    if (Get-NetAdapterBinding -ComponentID ms_tcpip6 -ErrorAction SilentlyContinue | Where-Object { $_.Enabled }) { $adminScript += "Get-NetAdapterBinding -ComponentID ms_tcpip6 | Disable-NetAdapterBinding -Confirm:`$false" }
    $adminScript += "Clear-DnsClientCache"
    if (-not (Get-ScheduledTask -TaskName 'ClaudeBodyguard' -ErrorAction SilentlyContinue)) {
        $adminScript += "`$a = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$BASE\claude-bodyguard.ps1`"'; `$t = New-ScheduledTaskTrigger -AtLogOn; Register-ScheduledTask -TaskName 'ClaudeBodyguard' -Action `$a -Trigger `$t -Force | Out-Null; Start-ScheduledTask -TaskName 'ClaudeBodyguard'"
    }
    if ($adminScript.Count -gt 0) {
        "FIX:修复时区/IPv6/DNS/保镖(需要管理员授权)..."
        $tmp = "$env:TEMP\claude-fix-$([guid]::NewGuid().Guid).ps1"
        ($adminScript -join "`n") | Out-File -Encoding utf8 $tmp
        try { Start-Process powershell -Verb RunAs -Wait -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$tmp`"" } catch { "FIX:管理员授权被取消" }
        Remove-Item $tmp -ErrorAction SilentlyContinue
        "FIX:时区/IPv6/DNS/保镖 ✓"
    } else {
        "FIX:时区/IPv6/保镖 无需修复 ✓"
    }

    # B2. 置顶规则:先识别 Clash 模式,绝不盲目写 Merge.yaml
    if ($PROXY_MODE -ne 'clash-verge') {
        "FIX:请在 $(Get-ProxyName) 中自行添加 Claude 域名置顶/直连规则"
    } else {
        $clashMode = Get-ClashMode
        if ($clashMode -eq 'unknown') {
            "FIX:无法确认 Clash 模式，已跳过规则修改"
        } elseif ($clashMode -eq 'global' -or $clashMode -eq 'direct') {
            $modeLabel = if ($clashMode -eq 'global') { '全局模式' } else { '直连模式' }
            "FIX:Clash 模式=$clashMode"
            $legacy = Remove-LegacyMergeRules
            if ($legacy.message -and -not $legacy.changed) {
                "FIX:Merge.yaml 清理提示: $($legacy.message)"
            }
            if ($legacy.changed) {
                "FIX:发现历史遗留 Merge 规则,已清理并备份: $($legacy.backup)"
                if (Restart-ClashVerge) {
                    "FIX:已重启 Clash Verge 以重新加载配置"
                    if ($clashMode -eq 'global') {
                        $tunOk = Wait-Tun 40
                        if ((Test-ProxyAlive) -and $tunOk) { "FIX:代理/TUN 已恢复 ✓" } else { "FIX:代理/TUN 未完全恢复,请手动检查 Clash 和 TUN 开关" }
                    }
                } else {
                    "FIX:未找到 Clash Verge 可执行文件,请手动重启以完成清理"
                }
                "FIX:$modeLabel,规则不适用,未写入任何规则,已清理历史遗留配置 ✓"
            } else {
                "FIX:$modeLabel,规则不适用,未改动任何配置 ✓"
            }
        } else {
            "FIX:Clash 模式=rule"
            $legacy = Remove-LegacyMergeRules
            if ($legacy.message -and -not $legacy.changed) {
                "FIX:Merge.yaml 清理提示: $($legacy.message)"
            }
            if ($legacy.changed) {
                "FIX:已清理历史遗留 Merge 规则并备份: $($legacy.backup)"
            }

            $write = Write-ClashScriptRules
            if (-not $write.ok) {
                "FIX:置顶规则 FAIL: $($write.message)"
                if ($legacy.changed) {
                    if (Restart-ClashVerge) {
                        Wait-Tun 20 | Out-Null
                        "FIX:已重启 Clash Verge 应用 Merge 清理"
                    } else {
                        "FIX:请手动重启 Clash Verge 应用 Merge 清理"
                    }
                }
            } else {
                $current = Get-ClashRules
                $alreadyOk = $current.available -and (Test-PinnedRules $current.rules)
                if (-not $write.changed -and -not $legacy.changed -and $alreadyOk) {
                    "FIX:置顶规则已是当前版本,内核已加载 ✓"
                } else {
                    if ($write.changed) {
                        "FIX:已写入 Script.js 规则并备份: $($write.backup)"
                    }
                    if (Restart-ClashVerge) {
                        $rulesInfo = Wait-ClashRules 40
                        if (-not $rulesInfo.available) {
                            "FIX:规则已写入但无法验证内核加载(控制接口不可用)"
                        } elseif (Test-PinnedRules $rulesInfo.rules) {
                            "FIX:置顶规则 ✓"
                            Wait-Tun 20 | Out-Null
                        } else {
                            "FIX:置顶规则验证失败,正在回滚 Script.js..."
                            Restore-ClashScriptChange $write
                            Restart-ClashVerge | Out-Null
                            Wait-Tun 20 | Out-Null
                            "FIX:置顶规则 FAIL: 验证失败,已回滚 Script.js,请确认 Clash Verge 已启用全局扩展脚本"
                        }
                    } else {
                        "FIX:规则已写入但未找到 Clash Verge 可执行文件,请手动重启后验证"
                    }
                }
            }
        }
    }

    # C. 出口IP最终验证
    Start-Sleep 2
    $e = Get-Egress
    if ($e.loc -eq $COUNTRY_TARGET) { "FIX:出口IP ✓ ($($e.ip))" } else { "FIX:出口IP ✗ ($($e.ip)/$($e.loc),期望$COUNTRY_TARGET) — 请换节点/线路" }
    "FIX:修复流程结束"
}

function Invoke-Status {
    $cur = if (Test-Path "$BASE\current.txt") { (Get-Content "$BASE\current.txt" -Raw).Trim() } else { 'none' }
    $hasA = if (Test-Path "$BASE\accounts\A") { 1 } else { 0 }
    $hasB = if (Test-Path "$BASE\accounts\B") { 1 } else { 0 }
    "current=$cur hasA=$hasA hasB=$hasB"
}

function Stop-ClaudeApp {
    $p = Get-Process -Name 'Claude' -ErrorAction SilentlyContinue
    if (-not $p) { return $true }
    $p | Stop-Process -Force
    for ($i = 0; $i -lt 15; $i++) { if (-not (Get-Process -Name 'Claude' -ErrorAction SilentlyContinue)) { return $true }; Start-Sleep 1 }
    return $false
}

function Save-Account($name) {
    robocopy "$DATA" "$BASE\accounts\$name" /MIR /NFL /NDL /NJH /NJS | Out-Null
    Log "已存档账号$name"
}

function Start-ClaudeApp {
    $exe = @("$env:LOCALAPPDATA\AnthropicClaude\Claude.exe", "$env:LOCALAPPDATA\Programs\Claude\Claude.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($exe) { Start-Process $exe } else { Start-Process "shell:AppsFolder" -ErrorAction SilentlyContinue }
}

function Invoke-Switch($target) {
    $cur = if (Test-Path "$BASE\current.txt") { (Get-Content "$BASE\current.txt" -Raw).Trim() } else { 'none' }

    # 首次运行:收编当前登录为账号A
    if ($cur -eq 'none' -and (Test-Path $DATA) -and (Get-ChildItem $DATA -ErrorAction SilentlyContinue)) {
        if (-not (Stop-ClaudeApp)) { "FAIL:Claude 未能退出，请手动退出后重试"; return }
        Save-Account A
        $cur = 'A'; 'A' | Out-File -Encoding ascii -NoNewline "$BASE\current.txt"
        Log "首次运行:当前登录状态已收编为账号A"
        "NOTE:已将当前登录收编为账号A"
    }

    if ($cur -eq $target) { Start-ClaudeApp; "INFO:当前已是账号$target"; return }

    if (-not (Stop-ClaudeApp)) { "FAIL:Claude 未能退出，请手动退出后重试"; return }

    if ($cur -ne 'none' -and (Test-Path $DATA)) { Save-Account $cur }

    if (Test-Path "$BASE\accounts\$target") {
        Remove-Item $DATA -Recurse -Force -ErrorAction SilentlyContinue
        robocopy "$BASE\accounts\$target" "$DATA" /E /NFL /NDL /NJH /NJS | Out-Null
        Log "已载入账号$target 存档"
    } else {
        Remove-Item $DATA -Recurse -Force -ErrorAction SilentlyContinue
        New-Item -ItemType Directory -Force -Path $DATA | Out-Null
        Log "账号$target 无存档，将以全新状态初始化"
    }
    $target | Out-File -Encoding ascii -NoNewline "$BASE\current.txt"
    Start-ClaudeApp
    Log "已切换到账号$target 并启动"
    "OK:已切换到账号$target"
}

function Get-ReleaseInfo {
    $current = Get-AppVersion
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        # GitHub 要求 User-Agent;PowerShell 5.1 的 -Headers 不允许改它,-UserAgent 等价写入请求头
        $rel = Invoke-RestMethod -Uri 'https://api.github.com/repos/clm031102-source/claude-network-guide/releases/latest' -UserAgent 'ClaudeSwitcher' -TimeoutSec 8
        $latest = ([string]$rel.tag_name).Trim() -replace '^[vV]', ''
        if (-not $latest) { throw '无法解析最新版本号' }

        $zip = @($rel.assets) | Where-Object { $_ -and $_.name -like '*-windows.zip' } | Select-Object -First 1
        $sums = @($rel.assets) | Where-Object { $_ -and $_.name -eq 'SHA256SUMS-release.txt' } | Select-Object -First 1
        $zipUrl = if ($zip) { [string]$zip.browser_download_url } else { '' }
        $sumsUrl = if ($sums) { [string]$sums.browser_download_url } else { '' }
        $pageUrl = [string]$rel.html_url
        $status = if ((Compare-Version $latest $current) -gt 0) { 'update_available' } else { 'latest' }

        if ($status -eq 'update_available' -and (-not (Test-GitHubDownloadUrl $zipUrl) -or -not (Test-GitHubDownloadUrl $sumsUrl))) {
            return @{ status = 'error'; current = $current; latest = $latest; zip = ''; sums = ''; page = ''; message = '更新资产缺失或下载地址不是 GitHub 官方域名' }
        }
        return @{ status = $status; current = $current; latest = $latest; zip = $zipUrl; sums = $sumsUrl; page = $pageUrl; message = '' }
    } catch {
        $httpStatus = 0
        if ($_.Exception.Response) {
            try { $httpStatus = [int]$_.Exception.Response.StatusCode } catch { }
        }
        if ($httpStatus -eq 404) {
            return @{ status = 'unavailable'; current = $current; latest = ''; zip = ''; sums = ''; page = ''; message = '暂无可用原生更新：本仓库尚未发布此组件的安装包，请使用源码版本。' }
        }
        $msg = ([string]$_.Exception.Message) -replace '\r?\n', ' '
        if ($msg -match 'rate limit|API rate|403') { $msg = 'GitHub 接口限流，请稍后再试' }
        return @{ status = 'error'; current = $current; latest = ''; zip = ''; sums = ''; page = ''; message = $msg }
    }
}

function Write-ReleaseInfo($info) {
    switch ($info.status) {
        'unavailable' {
            "STATUS=unavailable"
            "MESSAGE=$(([string]$info.message) -replace '\r?\n', ' ')"
        }
        'update_available' {
            "STATUS=update_available"
            "CURRENT=$($info.current)"
            "LATEST=$($info.latest)"
            "ZIP_URL=$($info.zip)"
            "SUMS_URL=$($info.sums)"
            "PAGE_URL=$($info.page)"
        }
        'latest' {
            "STATUS=latest"
            "CURRENT=$($info.current)"
            "LATEST=$($info.latest)"
        }
        default {
            "STATUS=error"
            "MESSAGE=$(([string]$info.message) -replace '\r?\n', ' ')"
        }
    }
}

function Invoke-CheckUpdate {
    Write-ReleaseInfo (Get-ReleaseInfo)
}

function Invoke-UpdateNow {
    $info = Get-ReleaseInfo
    if ($info.status -ne 'update_available') { Write-ReleaseInfo $info; return }

    $previous = $info.current
    $tmp = Join-Path $env:TEMP ("claude-switcher-update-" + [guid]::NewGuid().ToString('N'))
    $files = @('claude-switch.ps1', 'claude-bodyguard.ps1', 'SwitcherUI.ps1')
    $backupDir = $null
    $backedUp = @{}
    $task = Get-ScheduledTask -TaskName 'ClaudeBodyguard' -ErrorAction SilentlyContinue
    $versionPath = Join-Path $BASE 'version.txt'
    $versionExisted = Test-Path -LiteralPath $versionPath
    $versionRaw = $null
    if ($versionExisted) {
        try { $versionRaw = [System.IO.File]::ReadAllText($versionPath) } catch { $versionExisted = $false }
    }

    try {
        New-Item -ItemType Directory -Force -Path $tmp -ErrorAction Stop | Out-Null

        $zipUrl = [string]$info.zip
        $sumsUrl = [string]$info.sums
        if (-not (Test-GitHubDownloadUrl $zipUrl)) { throw '更新包下载地址不是 GitHub 官方域名' }
        if (-not (Test-GitHubDownloadUrl $sumsUrl)) { throw '校验文件下载地址不是 GitHub 官方域名' }

        $zipName = [System.IO.Path]::GetFileName(([Uri]$zipUrl).AbsolutePath)
        if ([string]::IsNullOrWhiteSpace($zipName)) { $zipName = 'windows-update.zip' }
        $zipPath = Join-Path $tmp $zipName
        $sumsPath = Join-Path $tmp 'SHA256SUMS-release.txt'
        Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing -TimeoutSec 60 -ErrorAction Stop
        Invoke-WebRequest -Uri $sumsUrl -OutFile $sumsPath -UseBasicParsing -TimeoutSec 60 -ErrorAction Stop

        $expected = $null
        foreach ($line in Get-Content -LiteralPath $sumsPath -ErrorAction Stop) {
            if ($line -match '^([0-9A-Fa-f]{64})\s+\*?(.+?)\s*$') {
                $name = [System.IO.Path]::GetFileName($Matches[2].Trim())
                if ($name -eq $zipName) { $expected = $Matches[1].ToUpperInvariant(); break }
            }
        }
        if (-not $expected) { throw 'SHA256SUMS 中未找到更新包哈希' }
        $actual = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256 -ErrorAction Stop).Hash.ToUpperInvariant()
        if ($actual -ne $expected) { throw '校验失败' }

        $extract = Join-Path $tmp 'extract'
        Expand-Archive -LiteralPath $zipPath -DestinationPath $extract -Force -ErrorAction Stop
        $newCore = Get-ChildItem -LiteralPath $extract -Recurse -Filter 'claude-switch.ps1' -File -ErrorAction Stop | Select-Object -First 1
        if (-not $newCore) { throw '更新包中未找到 claude-switch.ps1' }
        $pkgDir = $newCore.Directory.FullName
        foreach ($fn in $files) {
            if (-not (Test-Path -LiteralPath (Join-Path $pkgDir $fn))) { throw "更新包缺少 $fn" }
        }

        # 保留当前安装的 4 项用户配置
        $currentText = [System.IO.File]::ReadAllText((Join-Path $BASE 'claude-switch.ps1'))
        $newText = [System.IO.File]::ReadAllText($newCore.FullName)
        foreach ($name in @('PROXY_MODE', 'COUNTRY_TARGET', 'TZ_TARGET', 'PROXY_GROUP')) {
            $value = Get-ScriptConfigValue $currentText $name
            if ($null -ne $value) { $newText = Set-ScriptConfigValue $newText $name ([string]$value) }
        }

        $safeVersion = if ($previous) { $previous -replace '[^0-9A-Za-z._-]', '_' } else { 'unknown' }
        $backupDir = Join-Path $BASE ("backup-" + $safeVersion + "-" + (Get-Date -Format 'yyyyMMddHHmmss'))
        New-Item -ItemType Directory -Force -Path $backupDir -ErrorAction Stop | Out-Null
        foreach ($fn in $files) {
            $src = Join-Path $BASE $fn
            if (Test-Path -LiteralPath $src) {
                Copy-Item -LiteralPath $src -Destination (Join-Path $backupDir $fn) -Force -ErrorAction Stop
                $backedUp[$fn] = $true
            } else {
                $backedUp[$fn] = $false
            }
        }

        if ($task) { Stop-ScheduledTask -TaskName 'ClaudeBodyguard' -ErrorAction SilentlyContinue }

        $stagedCore = Join-Path $tmp 'claude-switch.new.ps1'
        [System.IO.File]::WriteAllText($stagedCore, $newText, (New-Object System.Text.UTF8Encoding($true)))
        Copy-Item -LiteralPath $stagedCore -Destination (Join-Path $BASE 'claude-switch.ps1') -Force -ErrorAction Stop
        foreach ($fn in @('claude-bodyguard.ps1', 'SwitcherUI.ps1')) {
            Copy-Item -LiteralPath (Join-Path $pkgDir $fn) -Destination (Join-Path $BASE $fn) -Force -ErrorAction Stop
        }
        [System.IO.File]::WriteAllText($versionPath, [string]$info.latest, (New-Object System.Text.UTF8Encoding($false)))
        if ($task) { Start-ScheduledTask -TaskName 'ClaudeBodyguard' -ErrorAction Stop }

        "STATUS=updated"
        "LATEST=$($info.latest)"
        "PREVIOUS=$previous"
        "MESSAGE=更新完成"
    } catch {
        $reason = ([string]$_.Exception.Message) -replace '\r?\n', ' '
        if ($backupDir -and (Test-Path -LiteralPath $backupDir)) {
            foreach ($fn in $files) {
                $dst = Join-Path $BASE $fn
                $bak = Join-Path $backupDir $fn
                if ($backedUp[$fn] -and (Test-Path -LiteralPath $bak)) {
                    Copy-Item -LiteralPath $bak -Destination $dst -Force -ErrorAction SilentlyContinue
                } elseif ($backedUp.ContainsKey($fn) -and -not $backedUp[$fn]) {
                    Remove-Item -LiteralPath $dst -Force -ErrorAction SilentlyContinue
                }
            }
            try {
                if ($versionExisted -and $null -ne $versionRaw) {
                    [System.IO.File]::WriteAllText($versionPath, $versionRaw, (New-Object System.Text.UTF8Encoding($false)))
                } else {
                    Remove-Item -LiteralPath $versionPath -Force -ErrorAction SilentlyContinue
                }
            } catch {}
        }
        if ($task) {
            try { Start-ScheduledTask -TaskName 'ClaudeBodyguard' -ErrorAction SilentlyContinue } catch {}
        }
        "STATUS=error"
        "MESSAGE=$reason"
    } finally {
        Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
    }
}

switch ($args[0]) {
    'checkdetail' {
        $r = Invoke-CheckDetail
        $r | Out-File -Encoding utf8 "$BASE\last-check.txt"
        $r
    }
    'status'       { Invoke-Status }
    'fix' {
        $r = @(Invoke-Fix)
        $r | Out-File -Encoding utf8 "$BASE\last-fix.txt"
        $r
    }
    'switch'       { Invoke-Switch $args[1] }
    'check-update' { Invoke-CheckUpdate }
    'update-now'   { Invoke-UpdateNow }
    default        { "用法: claude-switch.ps1 checkdetail|status|fix|switch A|B|check-update|update-now" }
}
