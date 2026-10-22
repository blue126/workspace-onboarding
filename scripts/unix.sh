#!/bin/bash
# Native Bash 3.2. Configuration is parsed as data, never evaluated.
set -euo pipefail
umask 077
export LC_ALL=C
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
platform=unsupported
case "$(uname -s)" in Darwin) platform=macos ;; Linux) platform=linux ;; esac
action="${1:-check}"
[[ $# -eq 0 ]] || shift
bundle="$repo_dir/deployment/device-bundle.zip"
expected_sha=""
state_root=""
install_clients=false
no_activate=false
stage=""
package_verified=false
client_ready=false
handshake=unavailable
ssh_identity=pending
assigned_vm=pending
sudo_check=pending
cli_check=pending
sftp_check=pending
claude_auth=user_action_required
cleanup() { [[ -z "$stage" ]] || rm -rf -- "$stage"; }
trap cleanup EXIT
report() {
    printf '{"schema_version":1,"platform":"%s","code":"%s","package_verified":%s,"client_ready":%s,"tunnel_handshake":"%s","ssh_identity":"%s","assigned_vm":"%s","sudo":"%s","cli":"%s","sftp_roundtrip":"%s","claude_auth":"%s","real_task":"pending"}\n' \
        "$platform" "$1" "$package_verified" "$client_ready" "$handshake" "$ssh_identity" "$assigned_vm" "$sudo_check" "$cli_check" "$sftp_check" "$claude_auth"
}
fail() { printf '%s\n' "$2" >&2; report "$1"; exit "${3:-2}"; }
while [[ $# -gt 0 ]]; do
    case "$1" in
        --bundle|--sha256|--state-root)
            [[ $# -ge 2 ]] || fail INVALID_ARGUMENT "参数缺少值。"
            case "$1" in --bundle) bundle=$2 ;; --sha256) expected_sha=$2 ;; --state-root) state_root=$2 ;; esac
            shift 2 ;;
        --install-clients) install_clients=true; shift ;;
        --no-activate) no_activate=true; shift ;;
        *) fail INVALID_ARGUMENT "未知参数；请阅读 README。" ;;
    esac
done
case "$action" in check|setup|verify|connect|sftp|disconnect) ;; *) fail INVALID_ACTION "动作：check/setup/verify/connect/sftp/disconnect。" ;; esac
[[ "$platform" != unsupported ]] || fail UNSUPPORTED_PLATFORM "支持 macOS 和 Ubuntu/Debian。"
[[ "$(id -u)" != 0 ]] || fail RUN_AS_USER "请以本机普通用户运行；需要时脚本会调用 sudo。"
if [[ "$platform" == linux ]]; then
    [[ -r /etc/os-release ]] || fail UNSUPPORTED_PLATFORM "无法识别发行版。"
    distro="$(sed -n 's/^ID=//p' /etc/os-release | tr -d '"')"
    [[ "$distro" == ubuntu || "$distro" == debian ]] || fail UNSUPPORTED_PLATFORM "Linux 首版仅支持 Ubuntu/Debian。"
    if $install_clients; then
        [[ "$action" == setup ]] || fail INVALID_ARGUMENT "只有 setup 可以安装客户端。"
        missing=()
        if ! command -v wg >/dev/null || ! command -v wg-quick >/dev/null; then missing+=(wireguard-tools); fi
        if ! command -v ssh >/dev/null || ! command -v sftp >/dev/null || ! command -v ssh-keygen >/dev/null; then missing+=(openssh-client); fi
        command -v jq >/dev/null || missing+=(jq)
        command -v unzip >/dev/null || missing+=(unzip)
        command -v ip >/dev/null || missing+=(iproute2)
        if [[ ${#missing[@]} -gt 0 ]]; then
            sudo apt-get update >/dev/null 2>&1 &&
                sudo apt-get install -y "${missing[@]}" >/dev/null 2>&1 ||
                fail INSTALL_FAILED "客户端安装失败，请检查 sudo 授权和软件源。"
        fi
    fi
    command -v jq >/dev/null || fail DEPENDENCY_MISSING "缺少 jq；获得软件安装授权后运行 setup --install-clients。"
fi
for program in unzip ssh ssh-keygen sftp; do
    command -v "$program" >/dev/null || fail DEPENDENCY_MISSING "缺少 unzip/OpenSSH 客户端。"
done
hash_file() {
    if [[ "$platform" == macos ]]; then shasum -a 256 "$1" | awk '{print $1}'
    else sha256sum "$1" | awk '{print $1}'; fi
}
if [[ -z "$expected_sha" ]]; then
    [[ "$bundle" == "$repo_dir/deployment/device-bundle.zip" ]] || fail PACKAGE_HASH_REQUIRED "external package must provide --sha256."
    [[ -f "$bundle" && -f "$repo_dir/deployment/device-bundle.sha256" ]] || fail PACKAGE_MISSING "Public source has no employee bundle; get the complete ZIP from your administrator."
    expected_sha="$(tr -d '\r\n' < "$repo_dir/deployment/device-bundle.sha256")"
fi
[[ "$expected_sha" =~ ^[a-f0-9]{64}$ ]] || fail PACKAGE_HASH_INVALID "设备包摘要格式无效。"
[[ -f "$bundle" && ! -L "$bundle" ]] || fail PACKAGE_MISSING "找不到常规设备包文件。"
[[ "$(wc -c < "$bundle" | tr -d ' ')" -le 262144 ]] || fail PACKAGE_TOO_LARGE "设备包超出大小限制。"
[[ "$(hash_file "$bundle")" == "$expected_sha" ]] || fail PACKAGE_HASH_MISMATCH "设备包摘要不匹配；未导入配置。"
entries="$(unzip -Z -1 "$bundle" 2>/dev/null)" || fail PACKAGE_INVALID "无法读取设备包目录。"
[[ "$(printf '%s\n' "$entries" | sort)" == "$(printf '%s\n' client-key known_hosts manifest.json wg.key | sort)" ]] ||
    fail PACKAGE_UNSAFE "设备包仅允许四个指定数据文件，不允许路径、重复项或脚本。"
sizes="$(unzip -l "$bundle" | awk '$4 ~ /^(client-key|known_hosts|manifest.json|wg.key)$/ {s += $1; if ($1 > 65536) bad=1; n++} END {if(n!=4 || bad || s>131072) print "bad"; else print "ok"}')"
[[ "$sizes" == ok ]] || fail PACKAGE_TOO_LARGE "设备包解压大小超限。"
stage="$(mktemp -d "${TMPDIR:-/tmp}/workspace-onboarding.XXXXXXXX")"
unzip -qq "$bundle" -d "$stage" 2>/dev/null || fail PACKAGE_INVALID "设备包解压失败。"
for file in client-key known_hosts manifest.json wg.key; do
    [[ -f "$stage/$file" && ! -L "$stage/$file" ]] || fail PACKAGE_UNSAFE "设备包不允许链接或特殊文件。"
    chmod 600 "$stage/$file"
done
json_get() {
    if [[ "$platform" == macos ]]; then
        /usr/bin/plutil -extract "$1" raw -o - "$stage/manifest.json" 2>/dev/null
    else jq -er --arg key "$1" '.[$key] | if type=="string" or type=="number" then tostring else error("type") end' "$stage/manifest.json" 2>/dev/null; fi
}
schema="$(json_get schema_version)" || fail MANIFEST_INVALID "manifest 无效。"
tool_version="$(json_get tool_version)" || fail MANIFEST_INVALID "manifest 无效。"
device="$(json_get device_id)" || fail MANIFEST_INVALID "manifest 缺少 device_id。"
vm_hostname="$(json_get vm_hostname)" || fail MANIFEST_INVALID "manifest 缺少 VM。"
gateway="$(json_get ssh_gateway)" || fail MANIFEST_INVALID "manifest 缺少入口。"
address="$(json_get wireguard_address)" || fail MANIFEST_INVALID "manifest 缺少设备地址。"
peer="$(json_get wireguard_public_key)" || fail MANIFEST_INVALID "manifest 缺少服务端公钥。"
client_public="$(json_get client_wireguard_public_key)" || fail MANIFEST_INVALID "manifest 缺少设备公钥。"
endpoint="$(json_get wireguard_endpoint)" || fail MANIFEST_INVALID "manifest 缺少 Endpoint。"
tunnel="$(json_get tunnel_name)" || fail MANIFEST_INVALID "manifest 缺少隧道名。"
expected_fields="$(printf '%s\n' schema_version tool_version device_id vm_hostname ssh_gateway wireguard_address wireguard_public_key client_wireguard_public_key wireguard_endpoint tunnel_name | sort)"
if [[ "$platform" == macos ]]; then
    actual_fields="$(/usr/bin/plutil -convert xml1 -o - "$stage/manifest.json" 2>/dev/null | awk -F '[<>]' '/<key>/ {print $3}' | sort)"
else
    actual_fields="$(jq -r 'keys[]' "$stage/manifest.json" 2>/dev/null | sort)"
fi
[[ "$actual_fields" == "$expected_fields" ]] || fail MANIFEST_INVALID "Unexpected manifest fields."
[[ "$schema" == 1 && "$tool_version" == 1.0.0 ]] || fail PACKAGE_VERSION_UNSUPPORTED "设备包版本与工具不匹配。"
[[ "$device" =~ ^ed-[a-z0-9-]{1,25}$ && "$vm_hostname" =~ ^employee-[a-z0-9-]{1,40}$ &&
   "$tunnel" =~ ^ws-[a-f0-9]{8}$ && "$peer" =~ ^[A-Za-z0-9+/]{43}=$ &&
   "$client_public" =~ ^[A-Za-z0-9+/]{43}=$ ]] || fail MANIFEST_INVALID "设备或公钥格式无效。"
valid_ip() {
    local value="$1" part
    local parts
    IFS=. read -r -a parts <<< "$value"
    [[ ${#parts[@]} -eq 4 ]] || return 1
    for part in "${parts[@]}"; do
        [[ "$part" =~ ^(0|[1-9][0-9]{0,2})$ ]] && [[ "$part" -le 255 ]] || return 1
    done
}
valid_ip "$gateway" && valid_ip "$endpoint" && valid_ip "${address%/32}" &&
    [[ "$address" == "${address%/32}/32" && "${address%/32}" != "$gateway" ]] ||
    fail MANIFEST_INVALID "入口、Endpoint 或 /32 地址无效。"
[[ "$(awk -v gateway="$gateway" 'NF {if (NF!=3 || $1!=gateway || $2!="ssh-ed25519" || $3 !~ /^[A-Za-z0-9+\/=]+$/) bad=1; n++} END {print (!bad && n==1) ? "ok" : "bad"}' "$stage/known_hosts")" == ok ]] ||
    fail HOST_PIN_INVALID "入口主机身份文件无效。"
ssh-keygen -lf "$stage/known_hosts" >/dev/null 2>&1 &&
    ssh-keygen -y -P '' -f "$stage/client-key" >/dev/null 2>&1 ||
    fail KEY_INVALID "SSH 密钥或主机身份无法解析。"
wg_private="$(tr -d '\r\n' < "$stage/wg.key")"
[[ "$wg_private" =~ ^[A-Za-z0-9+/]{43}=$ ]] || fail KEY_INVALID "WireGuard 密钥格式无效。"
package_verified=true
if [[ -z "$state_root" ]]; then
    if [[ "$platform" == macos ]]; then state_root="$HOME/Library/Application Support/WorkspaceOnboarding"
    else state_root="$HOME/.local/share/workspace-onboarding"; fi
fi
[[ "$state_root" == /* && "$state_root" != *'"'* && "$state_root" != *'%'* &&
    "$state_root" != *$'\n'* && "$state_root" != *$'\r'* ]] ||
    fail STATE_PATH_UNSAFE "Invalid private state directory."
parent="$state_root"
suffix=""
while [[ ! -d "$parent" ]]; do
    suffix="/$(basename "$parent")$suffix"
    parent="$(dirname "$parent")"
done
state_root="$(cd "$parent" && pwd -P)$suffix"
state="$state_root/$device"
case "$state_root/" in "$repo_dir/"*) fail STATE_IN_REPOSITORY "Install state outside this repository." ;; esac
if [[ -d "$state_root" ]]; then
    [[ ! -L "$state_root" && "$(ls -nd "$state_root" | awk '{print $3}')" == "$(id -u)" ]] ||
        fail STATE_PATH_UNSAFE "State directory owner or type mismatch."
fi
if [[ "$platform" == macos ]]; then
    [[ -d /Applications/WireGuard.app ]] && client_ready=true
else
    if command -v wg >/dev/null && command -v wg-quick >/dev/null && command -v ip >/dev/null; then client_ready=true; fi
fi
write_configs() {
    cat > "$stage/$tunnel.conf" <<EOF
[Interface]
PrivateKey = $wg_private
Address = $address

[Peer]
PublicKey = $peer
Endpoint = $endpoint:51820
AllowedIPs = $gateway/32
PersistentKeepalive = 25
EOF
    cat > "$stage/ssh_config" <<EOF
Host workspace
    HostName $gateway
    User $device
    Port 22
    IdentityFile "$state/client-key"
    UserKnownHostsFile "$state/known_hosts"
    GlobalKnownHostsFile /dev/null
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
EOF
    printf '%s\n' "$expected_sha" > "$stage/bundle.sha256"
    chmod 600 "$stage/"*
}
write_configs
require_installed() {
    [[ -d "$state" && ! -L "$state" ]] || fail NOT_CONFIGURED "Run setup first."
    for file in client-key known_hosts manifest.json wg.key ssh_config "$tunnel.conf" bundle.sha256; do
        [[ -f "$state/$file" && ! -L "$state/$file" ]] &&
            cmp -s "$stage/$file" "$state/$file" || fail CONFIG_CONFLICT "Installed configuration differs; nothing overwritten."
    done
}
owned_tunnel() {
    local actual actual_peer allowed current_address
    actual="$(sudo wg show "$tunnel" public-key 2>/dev/null)" || return 1
    actual_peer="$(sudo wg show "$tunnel" peers 2>/dev/null)" || return 1
    allowed="$(sudo wg show "$tunnel" allowed-ips 2>/dev/null)" || return 1
    current_address="$(ip -o -4 addr show dev "$tunnel" 2>/dev/null | awk '{print $4}')"
    [[ "$actual" == "$client_public" && "$actual_peer" == "$peer" &&
       "$allowed" == "$peer"$'\t'"$gateway/32" && "$current_address" == "$address" ]]
}
case "$action" in
    check)
        if ! $client_ready; then report DEPENDENCY_MISSING; exit 3; fi
        if [[ -d "$state" ]]; then require_installed; fi
        report CHECKED ;;
    setup)
        if [[ -d "$state_root" && ! -f "$state_root/.workspace-onboarding" ]]; then
            [[ -z "$(ls -A "$state_root")" ]] || fail STATE_ROOT_CONFLICT "Existing directory is not managed by this project."
        fi
        if [[ -e "$state" ]]; then require_installed
        else
            mkdir -p "$state_root"
            [[ ! -L "$state_root" ]] || fail STATE_PATH_UNSAFE "Symlink state directory rejected."
            chmod 700 "$state_root"
            printf '1\n' > "$state_root/.workspace-onboarding"
            mkdir -m 700 "$state"
            for file in client-key known_hosts manifest.json wg.key ssh_config "$tunnel.conf" bundle.sha256; do
                cp "$stage/$file" "$state/$file"
                chmod 600 "$state/$file"
            done
        fi
        if $no_activate; then report CONFIGURED; exit 0; fi
        if [[ "$platform" == macos ]]; then
            printf 'Import %s in WireGuard, allow VPN permission, then activate it.\n' "$state/$tunnel.conf" >&2
            if ! $client_ready && $install_clients; then open 'macappstore://apps.apple.com/app/wireguard/id1451685025'; fi
            report NEEDS_VPN_PERMISSION; exit 3
        fi
        $client_ready || fail DEPENDENCY_MISSING "Run setup --install-clients after authorizing software installation."
        if sudo wg show interfaces 2>/dev/null | tr ' ' '\n' | awk -v tunnel="$tunnel" '$0==tunnel {found=1} END {exit !found}'; then
            owned_tunnel || fail TUNNEL_CONFLICT "Existing tunnel does not belong to this device."
        else
            conflicting="$(ip -4 route show match "$gateway" | awk -v tunnel="$tunnel" '$1!="default" {for(i=1;i<=NF;i++) if($i=="dev" && $(i+1)!=tunnel) bad=1} END {print bad+0}')"
            [[ "$conflicting" == 0 ]] || fail ROUTE_CONFLICT "An existing network route covers the workspace gateway."
            sudo wg-quick up "$state/$tunnel.conf" >/dev/null 2>&1 ||
                fail TUNNEL_START_FAILED "Tunnel startup failed; check system permission and networking."
            owned_tunnel || fail TUNNEL_CONFLICT "Started tunnel does not match the assigned identity."
        fi
        report CONFIGURED ;;
    disconnect)
        require_installed
        if [[ "$platform" == macos ]]; then
            printf 'Deactivate only %s in WireGuard.\n' "$tunnel" >&2
            report NEEDS_VPN_PERMISSION; exit 3
        fi
        if sudo wg show interfaces 2>/dev/null | tr ' ' '\n' | awk -v tunnel="$tunnel" '$0==tunnel {found=1} END {exit !found}'; then
            owned_tunnel || fail TUNNEL_CONFLICT "Tunnel ownership mismatch; nothing stopped."
            sudo wg-quick down "$state/$tunnel.conf" >/dev/null 2>&1 ||
                fail TUNNEL_STOP_FAILED "Tunnel did not stop."
        fi
        report DISCONNECTED ;;
    connect|sftp)
        require_installed
        cleanup
        stage=""
        if [[ "$action" == connect ]]; then exec ssh -F "$state/ssh_config" -tt workspace
        else exec sftp -F "$state/ssh_config" -s employee-sftp workspace; fi ;;
    verify)
        require_installed
        nonce="$(od -An -N12 -tx1 /dev/urandom | tr -d ' \n')"
        prefix="WS_${nonce}"
        # Force a PTY; do not append a remote command to SSH.
        cat > "$stage/verify-input" <<EOF
stty -echo
printf '\n${prefix}_BEGIN\n'
if [ "\$(id -un)" = employee ]; then printf '${prefix}_USER=passed\n'; else printf '${prefix}_USER=failed\n'; fi
if [ "\$(hostname)" = "$vm_hostname" ]; then printf '${prefix}_VM=passed\n'; else printf '${prefix}_VM=failed\n'; fi
if sudo -n true; then printf '${prefix}_SUDO=passed\n'; else printf '${prefix}_SUDO=failed\n'; fi
if command -v claude >/dev/null && workspace-login --check >/dev/null && command -v workspace-browser >/dev/null; then printf '${prefix}_CLI=passed\n'; else printf '${prefix}_CLI=failed\n'; fi
python3 -c 'import json,subprocess; r=subprocess.run(["claude","auth","status"],capture_output=True,text=True,timeout=20); d=json.loads(r.stdout); print("${prefix}_AUTH="+("passed" if d.get("loggedIn") is True and d.get("authMethod")=="claude.ai" else "user_action_required"))' 2>/dev/null
printf '${prefix}_END\n'
exit
EOF
        if ! ssh -F "$state/ssh_config" -tt workspace < "$stage/verify-input" > "$stage/ssh-output" 2> "$stage/ssh-error"; then
            if grep -Eq 'REMOTE HOST IDENTIFICATION HAS CHANGED|Host key verification failed' "$stage/ssh-error"; then
                fail SSH_HOST_KEY_MISMATCH "Host identity changed; do not disable host verification."
            fi
            fail SSH_CONNECTION_FAILED "Check WireGuard, device permission and networking."
        fi
        tr -d '\r' < "$stage/ssh-output" > "$stage/lines"
        grep -qx "${prefix}_END" "$stage/lines" || fail SSH_PROTOCOL_FAILED "Interactive verification did not finish."
        grep -qx "${prefix}_USER=passed" "$stage/lines" && ssh_identity=passed
        grep -qx "${prefix}_VM=passed" "$stage/lines" && assigned_vm=passed
        grep -qx "${prefix}_SUDO=passed" "$stage/lines" && sudo_check=passed
        grep -qx "${prefix}_CLI=passed" "$stage/lines" && cli_check=passed
        grep -qx "${prefix}_AUTH=passed" "$stage/lines" && claude_auth=passed
        [[ "$ssh_identity" == passed && "$assigned_vm" == passed ]] ||
            fail WORKSPACE_ID_MISMATCH "Wrong user or VM; file verification was not attempted."
        if [[ "$platform" == linux ]]; then
            owned_tunnel || fail TUNNEL_CONFLICT "Live tunnel identity or routing mismatch."
            timestamp="$(sudo wg show "$tunnel" latest-handshakes 2>/dev/null | awk -v peer="$peer" '$1==peer {print $2}')"
            now="$(date +%s)"
            if [[ "$timestamp" =~ ^[0-9]+$ && "$timestamp" -gt 0 && $((now-timestamp)) -ge 0 && $((now-timestamp)) -le 180 ]]; then handshake=passed
            else handshake=failed; fail NO_RECENT_HANDSHAKE "No recent WireGuard handshake."; fi
        fi
        printf 'workspace-onboarding-%s\n' "$nonce" > "$stage/probe.txt"
        remote_dir="/tmp/ws-onboarding-$nonce"
        cat > "$stage/sftp-batch" <<EOF
mkdir $remote_dir
put "$stage/probe.txt" $remote_dir/probe.txt
get $remote_dir/probe.txt "$stage/returned.txt"
EOF
        sftp -F "$state/ssh_config" -s employee-sftp -b "$stage/sftp-batch" workspace > "$stage/sftp-output" 2>&1 ||
            fail SFTP_ROUNDTRIP_FAILED "SFTP roundtrip failed; unverified remote content left untouched."
        cmp -s "$stage/probe.txt" "$stage/returned.txt" || fail SFTP_CONTENT_MISMATCH "SFTP content differs; test directory preserved."
        printf 'rm %s/probe.txt\nrmdir %s\n' "$remote_dir" "$remote_dir" > "$stage/sftp-cleanup"
        sftp -F "$state/ssh_config" -s employee-sftp -b "$stage/sftp-cleanup" workspace >/dev/null 2>&1 ||
            fail SFTP_CLEANUP_FAILED "Could not clean this test directory; project files untouched."
        sftp_check=passed
        [[ "$sudo_check" == passed && "$cli_check" == passed ]] || fail VM_BASELINE_FAILED "VM sudo or CLI checks failed."
        if [[ "$claude_auth" != passed ]]; then report CLAUDE_AUTH_USER_PENDING
        elif [[ "$handshake" == unavailable ]]; then report HANDSHAKE_INSPECTION_UNAVAILABLE
        else report CONNECTION_VERIFIED; fi ;;
esac
