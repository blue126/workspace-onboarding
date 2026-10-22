[CmdletBinding()]
param(
    [ValidateSet('check','setup','verify','connect','sftp','disconnect')][string]$Action='check',
    [string]$Bundle,
    [string]$Sha256,
    [string]$StateRoot,
    [switch]$InstallClients,
    [switch]$NoActivate
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$repoDir=Split-Path $PSScriptRoot -Parent
$result=[ordered]@{schema_version=1;platform='windows';code='STARTING';package_verified=$false;client_ready=$false;tunnel_handshake='unavailable';ssh_identity='pending';assigned_vm='pending';sudo='pending';cli='pending';sftp_roundtrip='pending';claude_auth='user_action_required';real_task='pending'}
$stage=$null
function Report([string]$Code) { $result.code=$Code; $result | ConvertTo-Json -Compress }
function Stop-Setup([string]$Code,[string]$Message) { [Console]::Error.WriteLine($Message); Report $Code; exit 2 }
function Write-Utf8([string]$Path,[string]$Content) {
    [IO.File]::WriteAllText($Path,$Content,(New-Object Text.UTF8Encoding($false)))
}
function Hash-File([string]$Path) {
    $stream=[IO.File]::OpenRead($Path)
    $algorithm=[Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-','').ToLowerInvariant() }
    finally { $stream.Dispose(); $algorithm.Dispose() }
}
function Private-Acl([string]$Path) {
    $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User
    $acl=Get-Acl -LiteralPath $Path
    $acl.SetAccessRuleProtection($true,$false)
    $acl.SetOwner($sid)
    $inherit=[Security.AccessControl.InheritanceFlags]::None
    if(Test-Path -LiteralPath $Path -PathType Container) {
        $inherit=[Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit'
    }
    $rule=New-Object Security.AccessControl.FileSystemAccessRule($sid,'FullControl',$inherit,'None','Allow')
    $acl.AddAccessRule($rule)
    Set-Acl -LiteralPath $Path -AclObject $acl
}
function Assert-Regular([string]$Path) {
    $item=Get-Item -LiteralPath $Path -Force
    if($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { Stop-Setup 'PACKAGE_UNSAFE' 'Links are not accepted.' }
    if($item.PSIsContainer) { Stop-Setup 'PACKAGE_UNSAFE' 'Expected a regular data file.' }
}
function Valid-Ip([string]$Value) {
    $parsed=$null
    return [Net.IPAddress]::TryParse($Value,[ref]$parsed) -and
        $parsed.AddressFamily -eq [Net.Sockets.AddressFamily]::InterNetwork -and $parsed.ToString() -ceq $Value
}
function Admin() {
    $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
    $principal=New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}
function Native([string]$Exe,[string[]]$Arguments,[string]$InputText='',[int]$TimeoutMilliseconds=90000) {
    # All caller-controlled paths reject quotes/newlines; forward slashes avoid
    # Windows trailing-backslash quoting ambiguity. No secret values in arguments.
    $quoted=@()
    foreach($value in $Arguments) {
        if($value -match '["\r\n]') { throw 'Unsafe native argument.' }
        $quoted+=('"'+$value+'"')
    }
    $info=New-Object Diagnostics.ProcessStartInfo
    $info.FileName=$Exe
    $info.Arguments=$quoted -join ' '
    $info.UseShellExecute=$false
    $info.CreateNoWindow=$true
    $info.RedirectStandardInput=$true
    $info.RedirectStandardOutput=$true
    $info.RedirectStandardError=$true
    $proc=New-Object Diagnostics.Process
    $proc.StartInfo=$info
    [void]$proc.Start()
    $outTask=$proc.StandardOutput.ReadToEndAsync()
    $errTask=$proc.StandardError.ReadToEndAsync()
    if($InputText) { $proc.StandardInput.Write($InputText.Replace("`r`n","`n")) }
    $proc.StandardInput.Close()
    if(!$proc.WaitForExit($TimeoutMilliseconds)) {
        & (Join-Path $env:WINDIR 'System32/taskkill.exe') /PID $proc.Id /T /F 2>$null | Out-Null
        if(!$proc.WaitForExit(1000)) { $proc.Kill(); $proc.WaitForExit() }
        $nativeResult=@{ExitCode=124;Out='';Err='';TimedOut=$true}
    } else { $nativeResult=@{ExitCode=$proc.ExitCode;Out=$outTask.Result;Err=$errTask.Result;TimedOut=$false} }
    $proc.Dispose()
    return $nativeResult
}
function Require-Installed() {
    if(!(Test-Path -LiteralPath $state -PathType Container)) { Stop-Setup 'NOT_CONFIGURED' 'Run setup first.' }
    if((Get-Item -LiteralPath $state).Attributes -band [IO.FileAttributes]::ReparsePoint) { Stop-Setup 'STATE_PATH_UNSAFE' 'State directory is a link.' }
    foreach($name in $installedFiles) {
        $existing=Join-Path $state $name
        if(!(Test-Path -LiteralPath $existing -PathType Leaf)) { Stop-Setup 'CONFIG_CONFLICT' 'Installed configuration is incomplete.' }
        Assert-Regular $existing
        if((Hash-File $existing) -cne (Hash-File (Join-Path $stage $name))) {
            Stop-Setup 'CONFIG_CONFLICT' 'Installed configuration differs; nothing overwritten.'
        }
    }
}
function Require-OwnedService($Service) {
    $cim=Get-CimInstance Win32_Service -Filter ("Name='"+$serviceName+"'")
    $configPath=Join-Path $state ($manifest.tunnel_name+'.conf')
    if(!$cim -or $cim.PathName -notmatch ('(?i)(?:^|\s|")'+[regex]::Escape($configPath)+'(?:$|\s|")')) {
        Stop-Setup 'TUNNEL_CONFLICT' 'Existing service configuration path does not match this device.'
    }
}
try {
    if($PSVersionTable.PSVersion.Major -eq 5) {
        # Agent shells may pass PS7-only module paths into a PS5.1 child process.
        # Rebuild only this process's search path from native/system/user defaults.
        $machineModules=[Environment]::GetEnvironmentVariable('PSModulePath','Machine')
        $userModules=[Environment]::GetEnvironmentVariable('PSModulePath','User')
        $env:PSModulePath=[Environment]::ExpandEnvironmentVariables("$PSHOME\Modules;$machineModules;$userModules")
        Import-Module "$PSHOME\Modules\Microsoft.PowerShell.Security\Microsoft.PowerShell.Security.psd1" -ErrorAction Stop
    }
    if($env:OS -ne 'Windows_NT') { Stop-Setup 'UNSUPPORTED_PLATFORM' 'Use bootstrap.sh on macOS/Linux.' }
    if($InstallClients -and $Action -ne 'setup') { Stop-Setup 'INVALID_ARGUMENT' 'Only setup can install clients.' }
    $wireguard=Join-Path $env:ProgramFiles 'WireGuard/wireguard.exe'
    if($InstallClients) {
        if(!(Admin)) { Stop-Setup 'NEEDS_ADMIN' 'Open an elevated PowerShell with employee approval, then rerun setup -InstallClients.' }
        if(!(Get-Command ssh.exe -ErrorAction SilentlyContinue)) {
            Add-WindowsCapability -Online -Name 'OpenSSH.Client~~~~0.0.1.0' | Out-Null
        }
        if(!(Test-Path -LiteralPath $wireguard)) {
            $architecture=[Environment]::GetEnvironmentVariable('PROCESSOR_ARCHITEW6432')
            if(!$architecture) { $architecture=$env:PROCESSOR_ARCHITECTURE }
            $architecture=switch($architecture) { 'AMD64' { 'amd64' } 'ARM64' { 'arm64' } 'x86' { 'x86' } default { Stop-Setup 'UNSUPPORTED_PLATFORM' 'Unsupported Windows processor architecture.' } }
            $installer=Join-Path ([IO.Path]::GetTempPath()) ('wireguard-'+[Guid]::NewGuid().ToString('N')+'.msi')
            Invoke-WebRequest ('https://download.wireguard.com/windows-client/wireguard-'+$architecture+'-1.1.1.msi') -OutFile $installer -UseBasicParsing
            $signature=Get-AuthenticodeSignature -FilePath $installer
            if($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'CN=WireGuard LLC(?:,|$)') {
                Stop-Setup 'INSTALLER_SIGNATURE_INVALID' 'WireGuard installer signature validation failed.'
            }
            $install=Start-Process -FilePath (Join-Path $env:WINDIR 'System32/msiexec.exe') -ArgumentList @('/i',('"'+$installer+'"'),'/qn','/norestart','DO_NOT_LAUNCH=1') -Wait -PassThru
            if($install.ExitCode -notin @(0,3010)) { Stop-Setup 'INSTALL_FAILED' 'WireGuard installation did not complete.' }
        }
    }
    $sshCommand=Get-Command ssh.exe -ErrorAction SilentlyContinue
    $sftpCommand=Get-Command sftp.exe -ErrorAction SilentlyContinue
    $keygenCommand=Get-Command ssh-keygen.exe -ErrorAction SilentlyContinue
    if(!$sshCommand -or !$sftpCommand -or !$keygenCommand) { Stop-Setup 'DEPENDENCY_MISSING' 'OpenSSH client is missing; authorize setup -InstallClients.' }
    $result.client_ready=Test-Path -LiteralPath $wireguard
    $bundleDir=$null
    if(!$Bundle) {
        $profileDir=$env:USERPROFILE
        if(!$profileDir) { $profileDir=[Environment]::GetFolderPath('UserProfile') }
        $primaryDir=Join-Path $profileDir 'Downloads/employee-workspace'
        $fallbackDir=Join-Path $repoDir 'deployment'
        $bundleDir=$primaryDir
        $primarySeen=$false
        foreach($name in @('device-bundle.zip','device-bundle.sha256','README.md')) {
            if(Test-Path -LiteralPath (Join-Path $primaryDir $name)) { $primarySeen=$true }
        }
        if(!$primarySeen) {
            foreach($name in @('device-bundle.zip','device-bundle.sha256','README.md')) {
                if(Test-Path -LiteralPath (Join-Path $fallbackDir $name)) { $bundleDir=$fallbackDir; break }
            }
        }
        $Bundle=Join-Path $bundleDir 'device-bundle.zip'
    }
    if(!$Sha256) {
        if(!$bundleDir) { Stop-Setup 'PACKAGE_HASH_REQUIRED' 'External device bundles require -Sha256.' }
        $digestPath=Join-Path $bundleDir 'device-bundle.sha256'
        if(!(Test-Path -LiteralPath $Bundle -PathType Leaf) -or !(Test-Path -LiteralPath $digestPath -PathType Leaf)) {
            Stop-Setup 'PACKAGE_MISSING' 'Download the three device files from OneDrive to %USERPROFILE%/Downloads/employee-workspace; project deployment/ is the fallback.'
        }
        Assert-Regular $digestPath
        $Sha256=[IO.File]::ReadAllText($digestPath).Trim()
    }
    if($Sha256 -cnotmatch '^[a-f0-9]{64}$') { Stop-Setup 'PACKAGE_HASH_INVALID' 'Invalid SHA256 format.' }
    Assert-Regular $Bundle
    if((Get-Item -LiteralPath $Bundle).Length -gt 262144) { Stop-Setup 'PACKAGE_TOO_LARGE' 'Bundle is too large.' }
    if((Hash-File $Bundle) -cne $Sha256) {
        Stop-Setup 'PACKAGE_HASH_MISMATCH' 'Bundle hash differs; configuration not imported.'
    }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip=[IO.Compression.ZipFile]::OpenRead($Bundle)
    $allowed=@('client-key','known_hosts','manifest.json','wg.key')
    $stage=Join-Path ([IO.Path]::GetTempPath()) ('workspace-onboarding-'+[Guid]::NewGuid().ToString('N'))
    [void](New-Item -ItemType Directory -Path $stage)
    Private-Acl $stage
    try {
        if($zip.Entries.Count -ne 4) { Stop-Setup 'PACKAGE_UNSAFE' 'Exactly four bundle data files are required.' }
        $seen=@{}
        foreach($entry in $zip.Entries) {
            if($allowed -cnotcontains $entry.FullName -or $seen.ContainsKey($entry.FullName) -or $entry.Length -gt 65536 -or
                (($entry.ExternalAttributes -shr 16) -band 61440) -eq 40960) { Stop-Setup 'PACKAGE_UNSAFE' 'Unknown, duplicate, linked or oversized bundle entry.' }
            $seen[$entry.FullName]=$true
            $source=$entry.Open()
            $target=[IO.File]::Open((Join-Path $stage $entry.FullName),[IO.FileMode]::CreateNew)
            try {
                $buffer=New-Object byte[] 4096
                $total=0
                while(($read=$source.Read($buffer,0,$buffer.Length)) -gt 0) {
                    $total+=$read
                    if($total -gt 65536) { Stop-Setup 'PACKAGE_TOO_LARGE' 'Expanded entry is too large.' }
                    $target.Write($buffer,0,$read)
                }
            } finally { $source.Dispose(); $target.Dispose() }
            Private-Acl (Join-Path $stage $entry.FullName)
        }
    } finally { $zip.Dispose() }
    $manifest=Get-Content -LiteralPath (Join-Path $stage 'manifest.json') -Raw | ConvertFrom-Json
    $fields=@('schema_version','tool_version','device_id','vm_hostname','ssh_gateway','wireguard_address','wireguard_public_key','client_wireguard_public_key','wireguard_endpoint','tunnel_name')
    if(@($manifest.PSObject.Properties).Count -ne $fields.Count) { Stop-Setup 'MANIFEST_INVALID' 'Unexpected manifest properties.' }
    foreach($field in $fields) {
        if(!$manifest.PSObject.Properties[$field] -or [string]$manifest.$field -match '[\r\n]') { Stop-Setup 'MANIFEST_INVALID' 'Missing or invalid manifest field.' }
    }
    if($manifest.schema_version -ne 1 -or $manifest.tool_version -cne '1.0.0') { Stop-Setup 'PACKAGE_VERSION_UNSUPPORTED' 'Unsupported bundle version.' }
    if($manifest.device_id -cnotmatch '^[a-z][a-z0-9-]{0,27}$' -or $manifest.vm_hostname -cnotmatch '^employee-[a-z0-9-]{1,40}$' -or
       $manifest.tunnel_name -cnotmatch '^ws-[a-f0-9]{8}$' -or $manifest.wireguard_address -cnotmatch '/32$' -or
       !(Valid-Ip $manifest.ssh_gateway) -or !(Valid-Ip $manifest.wireguard_endpoint) -or
       !(Valid-Ip ($manifest.wireguard_address -replace '/32$','')) -or
       ($manifest.wireguard_address -replace '/32$','') -ceq $manifest.ssh_gateway) { Stop-Setup 'MANIFEST_INVALID' 'Invalid device identity or IPv4 addressing.' }
    foreach($keyValue in @($manifest.wireguard_public_key,$manifest.client_wireguard_public_key)) {
        if($keyValue -cnotmatch '^[A-Za-z0-9+/]{43}=$' -or [Convert]::FromBase64String($keyValue).Length -ne 32) { Stop-Setup 'KEY_INVALID' 'Invalid WireGuard public key.' }
    }
    $wgPrivate=[IO.File]::ReadAllText((Join-Path $stage 'wg.key')).Trim()
    if($wgPrivate -cnotmatch '^[A-Za-z0-9+/]{43}=$' -or [Convert]::FromBase64String($wgPrivate).Length -ne 32) { Stop-Setup 'KEY_INVALID' 'Invalid WireGuard private key.' }
    $pin=[IO.File]::ReadAllText((Join-Path $stage 'known_hosts')).Trim()
    if($pin -cnotmatch ('^'+[regex]::Escape($manifest.ssh_gateway)+' ssh-ed25519 [A-Za-z0-9+/=]+$')) { Stop-Setup 'HOST_PIN_INVALID' 'Invalid gateway host pin.' }
    $keyCheck=Native $keygenCommand.Source @('-y','-P','','-f',(Join-Path $stage 'client-key'))
    $pinCheck=Native $keygenCommand.Source @('-lf',(Join-Path $stage 'known_hosts'))
    if($keyCheck.ExitCode -ne 0 -or $pinCheck.ExitCode -ne 0) { Stop-Setup 'KEY_INVALID' 'OpenSSH could not parse credentials.' }
    $result.package_verified=$true
    if(!$StateRoot) { $StateRoot=Join-Path $env:USERPROFILE 'EmployeeWorkspace\devices' }
    $StateRoot=[IO.Path]::GetFullPath($StateRoot)
    if($StateRoot -match '["%\r\n]' -or ($StateRoot+'\').StartsWith($repoDir+'\',[StringComparison]::OrdinalIgnoreCase)) {
        Stop-Setup 'STATE_PATH_UNSAFE' 'Private client state must be outside the repository.'
    }
    if((Test-Path -LiteralPath $StateRoot) -and ((Get-Item -LiteralPath $StateRoot).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        Stop-Setup 'STATE_PATH_UNSAFE' 'Linked state root is not accepted.'
    }
    $state=Join-Path $StateRoot $manifest.device_id
    $stateSsh=$state.Replace('\','/')
    $config=Join-Path $state 'ssh_config'
    $serviceName='WireGuardTunnel$'+$manifest.tunnel_name
    $wgConf="[Interface]`nPrivateKey = $wgPrivate`nAddress = $($manifest.wireguard_address)`n`n[Peer]`nPublicKey = $($manifest.wireguard_public_key)`nEndpoint = $($manifest.wireguard_endpoint):51820`nAllowedIPs = $($manifest.ssh_gateway)/32`nPersistentKeepalive = 25`n"
    Write-Utf8 (Join-Path $stage ($manifest.tunnel_name+'.conf')) $wgConf
    $sshConf=@"
Host workspace
    HostName $($manifest.ssh_gateway)
    User $($manifest.device_id)
    Port 22
    IdentityFile "$stateSsh/client-key"
    UserKnownHostsFile "$stateSsh/known_hosts"
    GlobalKnownHostsFile NUL
    StrictHostKeyChecking yes
    HostKeyAlgorithms ssh-ed25519
    UpdateHostKeys no
    IdentitiesOnly yes
    IdentityAgent none
    BatchMode yes
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    ForwardAgent no
    ClearAllForwardings yes
    ProxyCommand none
    ProxyJump none
    PermitLocalCommand no
    EscapeChar none
    ConnectTimeout 10
    ServerAliveInterval 15
    ServerAliveCountMax 3
"@
    Write-Utf8 (Join-Path $stage 'ssh_config') ($sshConf.Replace("`r`n","`n")+"`n")
    Write-Utf8 (Join-Path $stage 'bundle.sha256') ($Sha256+"`n")
    $installedFiles=@('client-key','known_hosts','manifest.json','wg.key','ssh_config',($manifest.tunnel_name+'.conf'),'bundle.sha256')
    switch($Action) {
        'check' {
            if(Test-Path -LiteralPath $state) { Require-Installed }
            if(!$result.client_ready) { Report 'DEPENDENCY_MISSING'; exit 3 }
            Report 'CHECKED'
        }
        'setup' {
            if(Test-Path -LiteralPath $state) { Require-Installed }
            else {
                if((Test-Path -LiteralPath $StateRoot) -and !(Test-Path -LiteralPath (Join-Path $StateRoot '.workspace-onboarding')) -and @(Get-ChildItem -LiteralPath $StateRoot -Force).Count -gt 0) {
                    Stop-Setup 'STATE_ROOT_CONFLICT' 'Existing directory is not managed by this project.'
                }
                [void](New-Item -ItemType Directory -Path $StateRoot -Force)
                Private-Acl $StateRoot
                Write-Utf8 (Join-Path $StateRoot '.workspace-onboarding') "1"

                [void](New-Item -ItemType Directory -Path $state)
                Private-Acl $state
                foreach($name in $installedFiles) { Copy-Item -LiteralPath (Join-Path $stage $name) -Destination (Join-Path $state $name); Private-Acl (Join-Path $state $name) }
            }
            if($NoActivate) { Report 'CONFIGURED'; exit 0 }
            if(!(Admin)) { Stop-Setup 'NEEDS_ADMIN' 'Configuration prepared; rerun setup in elevated PowerShell to activate the tunnel.' }
            if(!$result.client_ready) { Stop-Setup 'DEPENDENCY_MISSING' 'Authorize setup -InstallClients to install WireGuard.' }
            $service=Get-Service -Name $serviceName -ErrorAction SilentlyContinue
            if($service) { Require-OwnedService $service; Start-Service -Name $serviceName }
            else {
                $route=Get-NetRoute -AddressFamily IPv4 -DestinationPrefix ($manifest.ssh_gateway+'/32') -ErrorAction SilentlyContinue
                if($route) { Stop-Setup 'ROUTE_CONFLICT' 'An existing route covers the workspace gateway; existing VPN left unchanged.' }
                $installTunnel=Native $wireguard @('/installtunnelservice',(Join-Path $state ($manifest.tunnel_name+'.conf')))
                if($installTunnel.ExitCode -ne 0) { Stop-Setup 'TUNNEL_START_FAILED' 'WireGuard tunnel service installation failed.' }
            }
            Report 'CONFIGURED'
        }
        'disconnect' {
            Require-Installed
            if(!(Admin)) { Stop-Setup 'NEEDS_ADMIN' 'Elevated PowerShell is needed to stop this tunnel.' }
            $service=Get-Service -Name $serviceName -ErrorAction SilentlyContinue
            if($service) { Require-OwnedService $service; Stop-Service -Name $serviceName }
            Report 'DISCONNECTED'
        }
        'connect' { Require-Installed; & $sshCommand.Source -F $config -tt workspace; exit $LASTEXITCODE }
        'sftp' { Require-Installed; & $sftpCommand.Source -F $config workspace; exit $LASTEXITCODE }
        'verify' {
            Require-Installed
            if(!(Admin)) { Stop-Setup 'NEEDS_ADMIN' 'Run the same verify command in an employee-approved elevated PowerShell.' }
            if(!(Test-Path -LiteralPath (Join-Path $env:ProgramFiles 'WireGuard/wg.exe'))) { Stop-Setup 'DEPENDENCY_MISSING' 'WireGuard CLI is missing.' }
            $nonce=[Guid]::NewGuid().ToString('N')
            $prefix='WS_'+$nonce
            $source=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'verify-session.py')).Replace('__PREFIX__',$prefix).Replace('__VM__',$manifest.vm_hostname)
            $payload=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($source))
            if($payload.Length -ge 3500) { Stop-Setup 'SSH_PROTOCOL_FAILED' 'Verification payload exceeds the PTY line limit.' }
            $remote="stty -echo; exec python3 -c 'import base64;exec(base64.b64decode(`"$payload`"))' </dev/null`n"
            $connection=Native $sshCommand.Source @('-F',$config,'-tt','workspace') $remote 60000
            if($connection.TimedOut) { Stop-Setup 'VERIFY_TIMEOUT' 'SSH verification exceeded 60 seconds; stop and report this code.' }
            if($connection.ExitCode -ne 0) {
                if($connection.Err -match 'Host key verification failed|REMOTE HOST IDENTIFICATION HAS CHANGED') { Stop-Setup 'SSH_HOST_KEY_MISMATCH' 'Host pin verification failed.' }
                Stop-Setup 'SSH_CONNECTION_FAILED' 'Check WireGuard, network and device permission.'
            }
            $clean=[regex]::Replace($connection.Out,'\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)','')
            $clean=[regex]::Replace($clean,'\x1b\[[0-?]*[ -/]*[@-~]','')
            $lines=$clean.Replace("`r",'').Split("`n")
            foreach($marker in @('BEGIN','END')) {
                if(@($lines | Where-Object { $_ -ceq ($prefix+'_'+$marker) }).Count -ne 1) { Stop-Setup 'SSH_PROTOCOL_FAILED' 'Verification frame is missing or duplicated.' }
            }
            foreach($field in @('USER','VM','SUDO','CLI')) {
                if(@($lines | Where-Object { $_ -cmatch ('^'+$prefix+'_'+$field+'=(passed|failed)$') }).Count -ne 1) { Stop-Setup 'SSH_PROTOCOL_FAILED' 'Verification field is missing or duplicated.' }
            }
            if(@($lines | Where-Object { $_ -cmatch ('^'+$prefix+'_AUTH=(passed|user_action_required|unavailable)$') }).Count -ne 1) { Stop-Setup 'SSH_PROTOCOL_FAILED' 'Authentication field is missing or duplicated.' }
            foreach($pair in @(@('USER','ssh_identity'),@('VM','assigned_vm'),@('SUDO','sudo'),@('CLI','cli'))) {
                if($lines -ccontains ($prefix+'_'+$pair[0]+'=passed')) { $result[$pair[1]]='passed' }
            }
            $result.claude_auth='unavailable'
            if($lines -ccontains ($prefix+'_AUTH=passed')) { $result.claude_auth='passed' }
            elseif($lines -ccontains ($prefix+'_AUTH=user_action_required')) { $result.claude_auth='user_action_required' }
            if($result.ssh_identity -ne 'passed' -or $result.assigned_vm -ne 'passed') { Stop-Setup 'WORKSPACE_ID_MISMATCH' 'Unexpected user or workspace VM.' }
            $wgTool=Join-Path $env:ProgramFiles 'WireGuard/wg.exe'
            if((Test-Path $wgTool) -and (Admin)) {
                $handshakes=Native $wgTool @('show',$manifest.tunnel_name,'latest-handshakes')
                if($handshakes.ExitCode -ne 0) { Stop-Setup 'NO_RECENT_HANDSHAKE' 'Cannot inspect this tunnel handshake.' }
                $found=$false
                foreach($line in $handshakes.Out.Split("`n")) {
                    $parts=$line.Trim() -split '\s+'
                    if($parts.Count -eq 2 -and $parts[0] -ceq $manifest.wireguard_public_key -and $parts[1] -match '^[0-9]+$') {
                        $age=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()-[long]$parts[1]
                        if([long]$parts[1] -gt 0 -and $age -ge 0 -and $age -le 180) { $found=$true }
                    }
                }
                if(!$found) { Stop-Setup 'NO_RECENT_HANDSHAKE' 'No recent WireGuard handshake.' }
                $result.tunnel_handshake='passed'
            }
            $probe=Join-Path $stage 'probe.txt'
            $returned=Join-Path $stage 'returned.txt'
            Write-Utf8 $probe ('workspace-onboarding-'+$nonce+"`n")
            $remoteDir='/tmp/ws-onboarding-'+$nonce
            $batch=Join-Path $stage 'batch.txt'
            Write-Utf8 $batch ("mkdir $remoteDir`nput `"$($probe.Replace('\','/'))`" $remoteDir/probe.txt`nget $remoteDir/probe.txt `"$($returned.Replace('\','/'))`"`n")
            $transfer=Native $sftpCommand.Source @('-F',$config,'-b',$batch,'workspace') '' 30000
            if($transfer.TimedOut) { Stop-Setup 'VERIFY_TIMEOUT' 'SFTP verification exceeded 30 seconds; stop and report this code.' }
            if($transfer.ExitCode -ne 0) { Stop-Setup 'SFTP_ROUNDTRIP_FAILED' 'SFTP roundtrip failed; unverified files left untouched.' }
            if((Hash-File $probe) -cne (Hash-File $returned)) { Stop-Setup 'SFTP_CONTENT_MISMATCH' 'SFTP content mismatch; test directory preserved.' }
            Write-Utf8 $batch ("rm $remoteDir/probe.txt`nrmdir $remoteDir`n")
            $cleanup=Native $sftpCommand.Source @('-F',$config,'-b',$batch,'workspace') '' 30000
            if($cleanup.TimedOut) { Stop-Setup 'VERIFY_TIMEOUT' 'SFTP cleanup exceeded 30 seconds; stop and report this code.' }
            if($cleanup.ExitCode -ne 0) { Stop-Setup 'SFTP_CLEANUP_FAILED' 'This test directory could not be cleaned.' }
            $result.sftp_roundtrip='passed'
            if($result.sudo -ne 'passed' -or $result.cli -ne 'passed') { Stop-Setup 'VM_BASELINE_FAILED' 'VM sudo or base CLI check failed.' }
            if($result.claude_auth -eq 'unavailable') { Stop-Setup 'CLAUDE_AUTH_CHECK_FAILED' 'Claude status could not be checked; do not treat this as logged out.' }
            if($result.claude_auth -ne 'passed') { Report 'CLAUDE_AUTH_USER_PENDING' }
            elseif($result.tunnel_handshake -eq 'unavailable') { Report 'HANDSHAKE_INSPECTION_UNAVAILABLE' }
            else { Report 'CONNECTION_VERIFIED' }
        }
    }
} catch {
    # Do not forward exceptions that may include private configuration or URLs.
    [Console]::Error.WriteLine('Operation failed. Use the documented recovery steps; do not print credentials.')
    [Console]::Error.WriteLine(('Failure type: {0}; script line: {1}' -f $_.Exception.GetType().Name,$_.InvocationInfo.ScriptLineNumber))
    Report 'OPERATION_FAILED'
    exit 2
} finally {
    if($stage -and (Test-Path -LiteralPath $stage)) { Remove-Item -LiteralPath $stage -Recurse -Force }
}
exit 0
