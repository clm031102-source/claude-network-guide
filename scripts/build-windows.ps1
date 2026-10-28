param(
    [Alias("PythonPath")][string]$Python = "python",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
if ($env:OS -ne "Windows_NT") { throw "Build this Windows package on Windows." }
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$venvDir = Join-Path $repoRoot ".venv/desktop"
$venvPython = Join-Path $venvDir "Scripts/python.exe"
$distDir = Join-Path $repoRoot "dist"
$workDir = Join-Path $repoRoot ".qa/windows-build"
$requirements = Join-Path $repoRoot "requirements-desktop.txt"

if (-not (Test-Path -LiteralPath $venvPython)) {
    & $Python -m venv $venvDir
    if ($LASTEXITCODE -ne 0) { throw "Could not create isolated desktop environment." }
}
if (-not $SkipInstall) {
    & $venvPython -m pip --disable-pip-version-check install --index-url https://pypi.org/simple -r $requirements
    if ($LASTEXITCODE -ne 0) { throw "Desktop dependency installation failed." }
}
& $venvPython -c "import platform,struct,sys; sys.exit(0 if struct.calcsize('P') == 8 and platform.machine().lower() in ('amd64', 'x86_64') else 1)"
if ($LASTEXITCODE -ne 0) { throw "Use 64-bit x86 Python to build the Windows x64 package." }
New-Item -ItemType Directory -Force -Path $distDir, $workDir | Out-Null
$buildArgs = @(
    "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed", "--noupx",
    "--name", "ClaudeNetworkGuide", "--distpath", $distDir,
    "--workpath", (Join-Path $workDir "work"), "--specpath", $workDir,
    "--add-data", ((Join-Path $repoRoot "app/web") + ";app/web"),
    "--hidden-import", "webview.platforms.edgechromium", "--hidden-import", "webview.platforms.winforms",
    "--hidden-import", "clr", "--collect-all", "pythonnet",
    "--recursive-copy-metadata", "pywebview",
    "--exclude-module", "PyQt5", "--exclude-module", "PyQt6",
    "--exclude-module", "PySide2", "--exclude-module", "PySide6",
    "--exclude-module", "cefpython3", "--exclude-module", "tkinter",
    (Join-Path $repoRoot "desktop_entry.py")
)
Push-Location $repoRoot
try {
    & $venvPython @buildArgs
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }
} finally { Pop-Location }

$packageDir = Join-Path $distDir "ClaudeNetworkGuide"
Copy-Item -LiteralPath (Join-Path $repoRoot "LICENSE") -Destination (Join-Path $packageDir "LICENSE.txt")
Copy-Item -LiteralPath $requirements -Destination (Join-Path $packageDir "requirements-desktop.txt")
$readme = @"
Claude 本机体检 — Windows x64 便携版

1. 完整解压 ZIP，再双击 ClaudeNetworkGuide.exe。不要单独移走 EXE 或 _internal 文件夹。
2. 无需安装 Python；打开独立窗口后自动执行一次只读体检。不会自动修改网络或登录账号。
3. 显示窗口需要 Microsoft Edge WebView2 Runtime 和 .NET Framework 4.6.2+（Windows 常见预装组件）。缺少时程序会提示。
   https://developer.microsoft.com/microsoft-edge/webview2/
4. 关闭窗口即停止本程序自己的本机服务。普通权限运行，不要求管理员权限。
5. 本程序未经代码签名。仅从自己的项目发行页下载并核对 SHA256；不要关闭系统安全防护。

使用说明与源码：https://github.com/clm031102-source/claude-network-guide
验证（不扫描外部网络）：ClaudeNetworkGuide.exe --self-test --self-test-output self-test.json
只读体检的脱敏报告：ClaudeNetworkGuide.exe --scan-report report.json

本包包含 Python、pywebview、pythonnet、WebView2 托管适配库及其依赖。
许可证位于 LICENSE.txt、PYTHON-LICENSE.txt 及 _internal 中各依赖的 dist-info / lib 目录。
"@
[IO.File]::WriteAllText((Join-Path $packageDir "使用说明.txt"), $readme, [Text.UTF8Encoding]::new($false))
# PyInstaller's runtime DLL is covered by the official Python distribution license.
$pythonLicense = & $venvPython -c "import pathlib,sys; print(pathlib.Path(sys.base_prefix) / 'LICENSE.txt')"
if (Test-Path -LiteralPath $pythonLicense) {
    Copy-Item -LiteralPath $pythonLicense -Destination (Join-Path $packageDir "PYTHON-LICENSE.txt")
}
$exe = Join-Path $packageDir "ClaudeNetworkGuide.exe"
$selfTest = Join-Path $workDir "self-test.json"
$testProcess = Start-Process -FilePath $exe -ArgumentList @("--self-test", "--self-test-output", ('"' + $selfTest + '"')) -WindowStyle Hidden -PassThru -Wait
if ($testProcess.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $selfTest)) { throw "Packaged executable self-test failed." }
$testResult = Get-Content -LiteralPath $selfTest -Raw | ConvertFrom-Json
if (-not $testResult.ok) { throw "Packaged resource/API verification failed." }
$zip = Join-Path $distDir "ClaudeNetworkGuide-Windows-x64.zip"
Compress-Archive -LiteralPath $packageDir -DestinationPath $zip -Force
$hash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
[IO.File]::WriteAllText(($zip + ".sha256"), ($hash + "  " + [IO.Path]::GetFileName($zip) + "`n"), [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText((Join-Path $distDir "SHA256SUMS.txt"), ($hash + "  " + [IO.Path]::GetFileName($zip) + "`n"), [Text.UTF8Encoding]::new($false))
Write-Output "Packaged executable self-test passed."
Write-Output $zip
