# Windows PowerShell 5.1 or PowerShell 7.
[CmdletBinding()]
param(
    [ValidateSet('check','setup','verify','connect','sftp','disconnect')][string]$Action='check',
    [string]$Bundle,
    [string]$Sha256,
    [string]$StateRoot,
    [switch]$InstallClients,
    [switch]$NoActivate
)
& (Join-Path $PSScriptRoot 'scripts/windows.ps1') @PSBoundParameters
exit $LASTEXITCODE
