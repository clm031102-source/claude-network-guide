# Claude 账号切换器 - Windows 界面 (WPF, Beta)
Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName WindowsBase

$BASE = "$env:USERPROFILE\.claude-switcher"
$CORE = "$BASE\claude-switch.ps1"

$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="Claude 账号切换器" Width="470" Height="820" ResizeMode="NoResize"
        WindowStartupLocation="CenterScreen" Background="#FF12141D" Foreground="White">
    <ScrollViewer VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled" Foreground="White">
    <Grid Margin="20">
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/><RowDefinition Height="Auto"/>
            <RowDefinition Height="Auto"/><RowDefinition Height="*"/>
        </Grid.RowDefinitions>

        <StackPanel Orientation="Horizontal" Grid.Row="0" Margin="0,0,0,14">
            <Border Width="44" Height="44" CornerRadius="12">
                <Border.Background>
                    <LinearGradientBrush StartPoint="0,0" EndPoint="1,1">
                        <GradientStop Color="#FF6366F1" Offset="0"/><GradientStop Color="#FF9333EA" Offset="1"/>
                    </LinearGradientBrush>
                </Border.Background>
                <TextBlock Text="盾" HorizontalAlignment="Center" VerticalAlignment="Center" FontSize="20" Foreground="White"/>
            </Border>
            <StackPanel Margin="12,0,0,0" VerticalAlignment="Center">
                <TextBlock Text="Claude 账号切换器" FontSize="18" FontWeight="Bold"/>
                <TextBlock Text="安全检查 · 切换 · 启动" FontSize="11" Foreground="#8AFFFFFF"/>
            </StackPanel>
            <Border x:Name="StatusPill" Margin="60,0,0,0" Padding="12,5" CornerRadius="12" Background="#2E22C55E" VerticalAlignment="Center">
                <TextBlock x:Name="StatusText" Text="检查中" FontSize="11" FontWeight="Bold" Foreground="#FFFB923C"/>
            </Border>
        </StackPanel>

        <Border Grid.Row="1" CornerRadius="12" Background="#0DFFFFFF" BorderBrush="#14FFFFFF" BorderThickness="1" Padding="4">
            <ListBox x:Name="CheckList" Background="Transparent" BorderThickness="0" Foreground="#E6FFFFFF" FontSize="13">
                <ListBox.ItemTemplate>
                    <DataTemplate>
                        <Grid Margin="6,6" Width="380">
                            <TextBlock Text="{Binding Name}" VerticalAlignment="Center"/>
                            <TextBlock Text="{Binding Detail}" HorizontalAlignment="Right" Margin="0,0,26,0" Foreground="#73FFFFFF" FontSize="11"/>
                            <TextBlock Text="{Binding Icon}" HorizontalAlignment="Right" Foreground="{Binding Color}" FontSize="14" FontWeight="Bold"/>
                        </Grid>
                    </DataTemplate>
                </ListBox.ItemTemplate>
            </ListBox>
        </Border>

        <StackPanel Grid.Row="2" Margin="0,14,0,0">
            <StackPanel Orientation="Horizontal" Margin="0,0,0,8">
                <TextBlock Text="当前账号" FontSize="11" Foreground="#80FFFFFF" VerticalAlignment="Center"/>
                <Border Margin="6,0,0,0" Padding="10,3" CornerRadius="10" Background="#4D6366F1">
                    <TextBlock x:Name="CurrentAccount" Text="?" FontSize="11" FontWeight="Bold" Foreground="#FFA5B4FC"/>
                </Border>
            </StackPanel>
            <Grid>
                <Grid.ColumnDefinitions><ColumnDefinition/><ColumnDefinition Width="10"/><ColumnDefinition/></Grid.ColumnDefinitions>
                <Button x:Name="BtnA" Grid.Column="0" Content="账号 A" Height="52" FontSize="15" FontWeight="Bold"
                        Foreground="White" Background="#7A6366F1" BorderThickness="0" Cursor="Hand"/>
                <Button x:Name="BtnB" Grid.Column="2" Content="账号 B" Height="52" FontSize="15" FontWeight="Bold"
                        Foreground="White" Background="#14FFFFFF" BorderBrush="#26FFFFFF" Cursor="Hand"/>
            </Grid>
            <TextBlock x:Name="ActionHint" Text="" FontSize="11" Foreground="#80FFFFFF" Margin="0,8,0,0" TextWrapping="Wrap"/>
        </StackPanel>

        <StackPanel Grid.Row="3">
            <Border x:Name="UpdateBar" Visibility="Collapsed" CornerRadius="10" Background="#1F6366F1" BorderBrush="#556366F1" BorderThickness="1" Padding="12,10" Margin="0,12,0,0">
                <Grid>
                    <Grid.ColumnDefinitions>
                        <ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/><ColumnDefinition Width="Auto"/>
                    </Grid.ColumnDefinitions>
                    <TextBlock x:Name="UpdateText" Grid.Column="0" Text="" FontSize="11" Foreground="#FFE0E7FF" TextWrapping="Wrap" VerticalAlignment="Center" Margin="0,0,8,0"/>
                    <Button x:Name="BtnUpdate" Grid.Column="1" Content="一键更新" Padding="10,5" Margin="0,0,6,0" FontSize="11" FontWeight="Bold" Foreground="White" Background="#FF6366F1" BorderThickness="0" Cursor="Hand"/>
                    <Button x:Name="BtnLater" Grid.Column="2" Content="稍后" Padding="10,5" FontSize="11" Foreground="#B3FFFFFF" Background="#14FFFFFF" BorderThickness="0" Cursor="Hand"/>
                </Grid>
            </Border>
            <TextBlock x:Name="Banner" Text="" FontSize="12" Foreground="#FFF87171" Margin="0,12,0,6" TextWrapping="Wrap"/>
            <StackPanel Orientation="Horizontal" HorizontalAlignment="Center">
                <Button x:Name="BtnFix" Content="一键修复" Padding="18,8" Margin="0,0,10,0" FontWeight="Bold" Foreground="White" BorderThickness="0" Cursor="Hand">
                    <Button.Background>
                        <LinearGradientBrush StartPoint="0,0" EndPoint="1,0">
                            <GradientStop Color="#FF6366F1" Offset="0"/><GradientStop Color="#FF9333EA" Offset="1"/>
                        </LinearGradientBrush>
                    </Button.Background>
                </Button>
                <Button x:Name="BtnRefresh" Content="重新检查" Padding="18,8" FontWeight="Bold" Foreground="White" Background="#1AFFFFFF" BorderThickness="0" Cursor="Hand"/>
                <Button x:Name="BtnCheckUpdate" Content="检查更新" Padding="18,8" Margin="10,0,0,0" FontWeight="Bold" Foreground="White" Background="#1AFFFFFF" BorderThickness="0" Cursor="Hand"/>
            </StackPanel>
            <TextBlock Text="任何一项检查不过，都不会启动 Claude" FontSize="10" Foreground="#59FFFFFF" HorizontalAlignment="Center" Margin="0,14,0,0"/>
        </StackPanel>
    </Grid>
    </ScrollViewer>
</Window>
"@

$reader = New-Object System.Xml.XmlNodeReader ([xml]$xaml)
$win = [Windows.Markup.XamlReader]::Load($reader)

$rows = New-Object System.Collections.ObjectModel.ObservableCollection[Object]
$win.FindName('CheckList').ItemsSource = $rows

$checkNames = @('代理内核','TUN网卡','出口IP','IP一致','时区','地区','IPv6','DNS','WebRTC','保镖','规则置顶','客户端语言','ASN属性','生态可达性')

function Set-Status($text, $color) {
    $win.FindName('StatusText').Text = $text
    $win.FindName('StatusText').Foreground = (New-Object System.Windows.Media.SolidColorBrush $color)
}

function Invoke-Core([string[]]$coreArgs) {
    # checkdetail/fix 改从落盘的 UTF-8 文件读取:子进程 stdout 经控制台代码页(如 GBK/936)转码会把中文弄乱
    if ($coreArgs[0] -eq 'checkdetail') {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $CORE @coreArgs 2>$null | Out-Null
        return ((Get-Content "$BASE\last-check.txt" -Encoding UTF8) -join "`n").Trim()
    }
    if ($coreArgs[0] -eq 'fix') {
        Remove-Item -LiteralPath "$BASE\last-fix.txt" -Force -ErrorAction SilentlyContinue
        & powershell -NoProfile -ExecutionPolicy Bypass -File $CORE @coreArgs 2>$null | Out-Null
        if (Test-Path -LiteralPath "$BASE\last-fix.txt") {
            return ((Get-Content "$BASE\last-fix.txt" -Encoding UTF8) -join "`n").Trim()
        }
        return ''
    }
    $out = & powershell -NoProfile -ExecutionPolicy Bypass -File $CORE @coreArgs 2>$null
    return ($out | Out-String).Trim()
}

function Refresh-Checks {
    $rows.Clear()
    foreach ($n in $checkNames) { $rows.Add([pscustomobject]@{ Name = $n; Detail = ''; Icon = '…'; Color = '#FF6B7280' }) }
    Set-Status '检查中' ([System.Windows.Media.Color]::FromRgb(0xFB,0x92,0x3C))
    $win.FindName('Banner').Text = ''

    $out = Invoke-Core @('checkdetail')
    $allOk = $true; $matched = 0
    foreach ($line in ($out -split "`n")) {
        $kv = $line -split '=', 2
        if ($kv.Count -ne 2) { continue }
        $st = $kv[1] -split ':', 2
        for ($i = 0; $i -lt $rows.Count; $i++) {
            if ($rows[$i].Name -eq $kv[0] -or ($kv[0] -eq 'TUN网卡' -and $rows[$i].Name -eq 'TUN网卡')) {
                $matched++
                $d = if ($st.Count -gt 1) { $st[1] } else { '' }
                switch ($st[0]) {
                    'ok'   { $rows[$i] = [pscustomobject]@{ Name = $rows[$i].Name; Detail = $d; Icon = '✓'; Color = '#FF22C55E' } }
                    'warn' { $rows[$i] = [pscustomobject]@{ Name = $rows[$i].Name; Detail = $d; Icon = '⚠'; Color = '#FFFACC15' } }
                    default { $rows[$i] = [pscustomobject]@{ Name = $rows[$i].Name; Detail = $d; Icon = '✗'; Color = '#FFF87171' }; $allOk = $false }
                }
                break
            }
        }
    }
    $st = Invoke-Core @('status')
    $win.FindName('CurrentAccount').Text = if ($st -match 'current=B') { 'B' } elseif ($st -match 'current=A') { 'A' } else { '未初始化' }
    if ($matched -lt $checkNames.Count) {
        Set-Status '检查未过' ([System.Windows.Media.Color]::FromRgb(0xF8,0x71,0x71))
        $win.FindName('Banner').Text = "检测输出不完整($matched/$($checkNames.Count))，请点重新检查"
    } elseif ($allOk) {
        Set-Status '环境安全' ([System.Windows.Media.Color]::FromRgb(0x22,0xC5,0x5E))
    } else {
        Set-Status '检查未过' ([System.Windows.Media.Color]::FromRgb(0xF8,0x71,0x71))
        $win.FindName('Banner').Text = '存在未通过项，可一键修复或手动处理后重试'
    }
}

function Switch-To($t) {
    Set-Status '切换中' ([System.Windows.Media.Color]::FromRgb(0x60,0xA5,0xFA))
    $win.FindName('Banner').Text = "正在切换到账号 $t…（归档约需几十秒）"
    $win.Dispatcher.Invoke([action]{}, 'Render')
    $r = Invoke-Core @('switch', $t)
    if ($r -match '^FAIL:') {
        Set-Status '检查未过' ([System.Windows.Media.Color]::FromRgb(0xF8,0x71,0x71))
        $win.FindName('Banner').Text = $r
    } else {
        $win.FindName('CurrentAccount').Text = $t
        Set-Status '完成' ([System.Windows.Media.Color]::FromRgb(0x22,0xC5,0x5E))
        $win.FindName('Banner').Foreground = (New-Object System.Windows.Media.SolidColorBrush ([System.Windows.Media.Color]::FromRgb(0x22,0xC5,0x5E)))
        $win.FindName('Banner').Text = "已切换到账号 $t，Claude 启动中。"
    }
}

$script:checkJob = $null
$script:checkTimer = $null
$script:checkManual = $false
$script:updateJob = $null
$script:updateTimer = $null
$script:updateRunning = $false
$script:latestVersion = ''

function Get-UiVersion {
    $vf = Join-Path $BASE 'version.txt'
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

function ConvertFrom-UpdateOutput([string]$text) {
    $map = @{}
    foreach ($line in ($text -split "`r?`n")) {
        $kv = $line -split '=', 2
        if ($kv.Count -eq 2) { $map[$kv[0].Trim()] = $kv[1].Trim() }
    }
    return $map
}

function Write-UpdateCache([string]$status, [string]$latest) {
    try {
        $obj = [pscustomobject]@{
            checkedAt = (Get-Date).ToString('o')
            latest = $latest
            status = $status
        }
        $p = Join-Path $BASE 'update-check.json'
        [System.IO.File]::WriteAllText($p, ($obj | ConvertTo-Json -Compress), (New-Object System.Text.UTF8Encoding($false)))
    } catch {}
}

function Read-UpdateCache {
    $p = Join-Path $BASE 'update-check.json'
    if (-not (Test-Path -LiteralPath $p)) { return $null }
    try { return (Get-Content -LiteralPath $p -Raw -Encoding UTF8 -ErrorAction Stop | ConvertFrom-Json) } catch { return $null }
}

function Test-UpdateCacheFresh($cache) {
    if (-not $cache -or -not $cache.checkedAt) { return $false }
    try {
        $checked = [DateTime]::Parse([string]$cache.checkedAt, [Globalization.CultureInfo]::InvariantCulture)
        $hours = ((Get-Date) - $checked).TotalHours
        return ($hours -ge 0 -and $hours -lt 24)
    } catch { return $false }
}

function Set-UpdateText([string]$text, [string]$hex) {
    $win.FindName('UpdateText').Text = $text
    $win.FindName('UpdateText').Foreground = (New-Object System.Windows.Media.BrushConverter).ConvertFromString($hex)
}

function Show-UpdateAvailable([string]$latest) {
    $script:latestVersion = $latest
    $current = Get-UiVersion
    Set-UpdateText "发现新版本 v$latest（当前 v$current）" '#FFE0E7FF'
    $win.FindName('BtnUpdate').Visibility = 'Visible'
    $win.FindName('BtnUpdate').IsEnabled = $true
    $win.FindName('BtnLater').Content = '稍后'
    $win.FindName('BtnLater').Visibility = 'Visible'
    $win.FindName('UpdateBar').Visibility = 'Visible'
}

function Show-UpdateNote([string]$text, [bool]$isError) {
    $script:latestVersion = ''
    if ($isError) { Set-UpdateText $text '#FFF87171' } else { Set-UpdateText $text '#FFE0E7FF' }
    $win.FindName('BtnUpdate').Visibility = 'Collapsed'
    $win.FindName('BtnLater').Content = '关闭'
    $win.FindName('BtnLater').Visibility = 'Visible'
    $win.FindName('UpdateBar').Visibility = 'Visible'
}

function Show-UpdateChecking {
    Set-UpdateText '正在检查更新…' '#FFE0E7FF'
    $win.FindName('BtnUpdate').Visibility = 'Collapsed'
    $win.FindName('BtnLater').Content = '关闭'
    $win.FindName('BtnLater').Visibility = 'Visible'
    $win.FindName('UpdateBar').Visibility = 'Visible'
}

function Start-UpdateCheck([bool]$manual) {
    if ($script:updateRunning) { return }
    if ($script:checkJob) {
        $s = $script:checkJob.State
        if ($s -eq 'Running' -or $s -eq 'NotStarted') {
            if ($manual) { $script:checkManual = $true; Show-UpdateChecking }
            return
        }
        Remove-Job $script:checkJob -Force -ErrorAction SilentlyContinue
        $script:checkJob = $null
    }

    if (-not $manual) {
        $cache = Read-UpdateCache
        if (Test-UpdateCacheFresh $cache) {
            if ($cache.status -eq 'update_available' -and $cache.latest) {
                Show-UpdateAvailable ([string]$cache.latest)
                return
            }
            if ($cache.status -eq 'dismissed') { return }
        }
    }

    if ($script:checkTimer) {
        $script:checkTimer.Stop()
        $script:checkTimer = $null
    }
    $script:checkManual = $manual
    if ($manual) { Show-UpdateChecking }

    try {
        $script:checkJob = Start-Job -ScriptBlock {
            param($core)
            & powershell -NoProfile -ExecutionPolicy Bypass -File $core check-update 2>$null
        } -ArgumentList $CORE
    } catch {
        $script:checkJob = $null
        if ($manual) { Show-UpdateNote ("检查更新失败：" + $_.Exception.Message) $true }
        return
    }

    $script:checkTimer = New-Object System.Windows.Threading.DispatcherTimer
    $script:checkTimer.Interval = [TimeSpan]::FromMilliseconds(500)
    $script:checkTimer.Add_Tick({
        if (-not $script:checkJob) { $script:checkTimer.Stop(); return }
        $st = $script:checkJob.State
        if ($st -ne 'Completed' -and $st -ne 'Failed' -and $st -ne 'Stopped') { return }
        $script:checkTimer.Stop()
        $out = (Receive-Job $script:checkJob -ErrorAction SilentlyContinue | Out-String)
        Remove-Job $script:checkJob -Force -ErrorAction SilentlyContinue
        $script:checkJob = $null
        $kv = ConvertFrom-UpdateOutput $out
        $manualNow = [bool]$script:checkManual
        if ($kv['STATUS'] -eq 'update_available' -and $kv['LATEST']) {
            Show-UpdateAvailable ([string]$kv['LATEST'])
            Write-UpdateCache 'update_available' ([string]$kv['LATEST'])
        } elseif ($kv['STATUS'] -eq 'unavailable') {
            if ($manualNow) { Show-UpdateNote ([string]$kv['MESSAGE']) $false }
            Write-UpdateCache 'unavailable' ''
        } elseif ($manualNow) {
            if ($kv['STATUS'] -eq 'latest') {
                Show-UpdateNote ("已是最新版本 v" + $kv['LATEST']) $false
                Write-UpdateCache 'latest' ([string]$kv['LATEST'])
            } else {
                $msg = if ($kv['MESSAGE']) { $kv['MESSAGE'] } else { '无法获取更新信息' }
                Show-UpdateNote ("检查更新失败：" + $msg) $true
            }
        } elseif ($kv['STATUS'] -eq 'latest') {
            Write-UpdateCache 'latest' ([string]$kv['LATEST'])
        }
    })
    $script:checkTimer.Start()
}

$win.FindName('BtnRefresh').Add_Click({ Refresh-Checks })
$win.FindName('BtnFix').Add_Click({
    Set-Status '修复中' ([System.Windows.Media.Color]::FromRgb(0xFB,0x92,0x3C))
    $win.FindName('Banner').Text = '正在修复…（会弹出管理员授权框）'
    $win.Dispatcher.Invoke([action]{}, 'Render')
    $fixOut = Invoke-Core @('fix')
    Refresh-Checks
    $ruleLine = $fixOut -split "`n" | Where-Object { $_ -match '^FIX:.*(FAIL|✗|无法|未恢复|未完全|未找到)' } | Select-Object -Last 1
    if (-not $ruleLine) {
        $ruleLine = $fixOut -split "`n" | Where-Object { $_ -match '^FIX:.*(模式|规则|TUN)' } | Select-Object -Last 1
    }
    if ($ruleLine) {
        $win.FindName('Banner').Text = $ruleLine.Trim()
        if ($ruleLine -match 'FAIL|✗|无法|未恢复|未完全|未找到') {
            $win.FindName('Banner').Foreground = (New-Object System.Windows.Media.SolidColorBrush ([System.Windows.Media.Color]::FromRgb(0xF8,0x71,0x71)))
        } else {
            $win.FindName('Banner').Foreground = (New-Object System.Windows.Media.SolidColorBrush ([System.Windows.Media.Color]::FromRgb(0x60,0xA5,0xFA)))
        }
    }
})
$win.FindName('BtnA').Add_Click({ Switch-To 'A' })
$win.FindName('BtnB').Add_Click({ Switch-To 'B' })

$win.FindName('BtnCheckUpdate').Add_Click({
    if ($script:updateRunning) { return }
    Remove-Item -LiteralPath (Join-Path $BASE 'update-check.json') -Force -ErrorAction SilentlyContinue
    Start-UpdateCheck $true
})

$win.FindName('BtnLater').Add_Click({
    if ($script:checkJob) {
        Stop-Job $script:checkJob -ErrorAction SilentlyContinue
        Remove-Job $script:checkJob -Force -ErrorAction SilentlyContinue
        $script:checkJob = $null
    }
    if ($script:checkTimer) { $script:checkTimer.Stop() }
    $win.FindName('UpdateBar').Visibility = 'Collapsed'
    $latest = if ($script:latestVersion) { [string]$script:latestVersion } else { '' }
    Write-UpdateCache 'dismissed' $latest
})

$win.FindName('BtnUpdate').Add_Click({
    if ($script:updateRunning) { return }
    $script:updateRunning = $true
    $btn = $win.FindName('BtnUpdate')
    $btn.IsEnabled = $false
    $win.FindName('BtnLater').IsEnabled = $false
    $win.FindName('BtnCheckUpdate').IsEnabled = $false
    if ($script:updateTimer) { $script:updateTimer.Stop(); $script:updateTimer = $null }
    Set-UpdateText '正在下载并校验…' '#FFE0E7FF'

    try {
        $script:updateJob = Start-Job -ScriptBlock {
            param($core)
            & powershell -NoProfile -ExecutionPolicy Bypass -File $core update-now 2>$null
        } -ArgumentList $CORE
    } catch {
        $script:updateRunning = $false
        $btn.IsEnabled = $true
        $win.FindName('BtnLater').IsEnabled = $true
        $win.FindName('BtnCheckUpdate').IsEnabled = $true
        Set-UpdateText ("更新失败：" + $_.Exception.Message) '#FFF87171'
        return
    }

    $script:updateTimer = New-Object System.Windows.Threading.DispatcherTimer
    $script:updateTimer.Interval = [TimeSpan]::FromMilliseconds(500)
    $script:updateTimer.Add_Tick({
        if (-not $script:updateJob) { $script:updateTimer.Stop(); return }
        $st = $script:updateJob.State
        if ($st -ne 'Completed' -and $st -ne 'Failed' -and $st -ne 'Stopped') { return }
        $script:updateTimer.Stop()
        $out = (Receive-Job $script:updateJob -ErrorAction SilentlyContinue | Out-String)
        Remove-Job $script:updateJob -Force -ErrorAction SilentlyContinue
        $script:updateJob = $null
        $script:updateRunning = $false
        $kv = ConvertFrom-UpdateOutput $out
        if ($kv['STATUS'] -eq 'updated') {
            Set-UpdateText '更新完成，正在重启界面' '#FF22C55E'
            Write-UpdateCache 'latest' ([string]$kv['LATEST'])
            if ($script:checkJob) {
                Stop-Job $script:checkJob -ErrorAction SilentlyContinue
                Remove-Job $script:checkJob -Force -ErrorAction SilentlyContinue
                $script:checkJob = $null
            }
            $uiScript = "$BASE\SwitcherUI.ps1"
            Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',('"' + $uiScript + '"')
            $win.Close()
        } elseif ($kv['STATUS'] -eq 'latest') {
            $win.FindName('BtnUpdate').IsEnabled = $true
            $win.FindName('BtnLater').IsEnabled = $true
            $win.FindName('BtnCheckUpdate').IsEnabled = $true
            Show-UpdateNote '已是最新版本' $false
            Write-UpdateCache 'latest' ([string]$kv['LATEST'])
        } elseif ($kv['STATUS'] -eq 'unavailable') {
            $win.FindName('BtnUpdate').IsEnabled = $false
            $win.FindName('BtnLater').IsEnabled = $true
            $win.FindName('BtnCheckUpdate').IsEnabled = $true
            Show-UpdateNote ([string]$kv['MESSAGE']) $false
            Write-UpdateCache 'unavailable' ''
        } else {
            $msg = if ($kv['MESSAGE']) { $kv['MESSAGE'] } else { '更新失败，请稍后重试' }
            Set-UpdateText ("更新失败：" + $msg) '#FFF87171'
            $win.FindName('BtnUpdate').IsEnabled = $true
            $win.FindName('BtnLater').IsEnabled = $true
            $win.FindName('BtnCheckUpdate').IsEnabled = $true
        }
    })
    $script:updateTimer.Start()
})

$win.Add_ContentRendered({
    Start-UpdateCheck $false
    Refresh-Checks
})
$win.Add_Closed({
    if ($script:checkTimer) { $script:checkTimer.Stop() }
    if ($script:updateTimer) { $script:updateTimer.Stop() }
    foreach ($j in @($script:checkJob, $script:updateJob)) {
        if ($j) {
            Stop-Job $j -ErrorAction SilentlyContinue
            Remove-Job $j -Force -ErrorAction SilentlyContinue
        }
    }
})
[void]$win.ShowDialog()
