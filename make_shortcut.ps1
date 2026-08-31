# 在桌面建立「工地氣象監控」捷徑
#
# 會建立兩個：
#   工地氣象監控.url          一般瀏覽器開啟（可加到我的最愛、任何瀏覽器都能用）
#   工地氣象監控(全螢幕).lnk  Chrome 應用程式模式，沒有網址列與分頁，適合工地螢幕常駐
#
# 用法（在此資料夾按右鍵 →「在終端中開啟」後執行）：
#   powershell -ExecutionPolicy Bypass -File make_shortcut.ps1

$url     = "https://eason-237588.github.io/site-weather/"
$desktop = [Environment]::GetFolderPath("Desktop")
$chrome  = "C:\Program Files\Google\Chrome\Application\chrome.exe"

# --- 1) 一般網址捷徑 ---
$urlFile = Join-Path $desktop "工地氣象監控.url"
$content = @"
[InternetShortcut]
URL=$url
IconIndex=0
"@
Set-Content -Path $urlFile -Value $content -Encoding ASCII
Write-Output "已建立：$urlFile"

# --- 2) Chrome 全螢幕（應用程式模式）捷徑 ---
if (Test-Path $chrome) {
    $lnkFile = Join-Path $desktop "工地氣象監控(全螢幕).lnk"
    $shell = New-Object -ComObject WScript.Shell
    $sc = $shell.CreateShortcut($lnkFile)
    $sc.TargetPath       = $chrome
    $sc.Arguments        = "--app=$url --start-maximized"
    $sc.WorkingDirectory = Split-Path $chrome
    $sc.IconLocation     = "$chrome,0"
    $sc.Description      = "工地環境安全即時監控系統（無網址列）"
    $sc.Save()
    Write-Output "已建立：$lnkFile"
} else {
    Write-Output "找不到 Chrome，略過全螢幕捷徑：$chrome"
}

Write-Output ""
Write-Output "完成。要換網址時改本檔第 11 行的 `$url 再執行一次即可。"
