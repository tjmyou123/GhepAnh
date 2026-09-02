# Ky so dist\GhepAnh.exe + dist\ghep.exe bang chung chi tu ky "CN=Prodat09".
# Chay rieng:  powershell -NoProfile -ExecutionPolicy Bypass -File packaging\sign_exe.ps1
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$exes = @("$root\dist\GhepAnh.exe", "$root\dist\ghep.exe") | Where-Object { Test-Path $_ }
if (-not $exes) {
    Write-Error "Khong tim thay exe trong dist\ - hay build truoc (build_exe.bat)."
}

# 1) Tim chung chi ky code CN=Prodat09 trong kho ca nhan; chua co thi tao (han 5 nam)
$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
    Where-Object { $_.Subject -eq "CN=Prodat09" -and $_.NotAfter -gt (Get-Date) } |
    Sort-Object NotAfter -Descending | Select-Object -First 1
if (-not $cert) {
    Write-Host "Dang tao chung chi tu ky CN=Prodat09..."
    $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=Prodat09" `
        -FriendlyName "Prodat09 Code Signing" -CertStoreLocation Cert:\CurrentUser\My `
        -HashAlgorithm SHA256 -NotAfter (Get-Date).AddYears(5)
}

# 2) Xuat phan cong khai de cai len may khac (Trusted Root + Trusted Publishers)
Export-Certificate -Cert $cert -FilePath "$PSScriptRoot\Prodat09.cer" -Force | Out-Null

# 3) Ky tung exe, kem dong dau thoi gian (khong co mang thi ky khong timestamp)
foreach ($exe in $exes) {
    try {
        $r = Set-AuthenticodeSignature -FilePath $exe -Certificate $cert `
            -HashAlgorithm SHA256 -TimestampServer "http://timestamp.digicert.com"
    } catch {
        $r = Set-AuthenticodeSignature -FilePath $exe -Certificate $cert -HashAlgorithm SHA256
    }
    Write-Host ("  Da ky {0}  (trang thai: {1})" -f (Split-Path $exe -Leaf), $r.Status)
}
Write-Host "Luu y: chung chi TU KY nen may chua cai Prodat09.cer se bao 'UnknownError'/SmartScreen."
