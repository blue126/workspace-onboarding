#!/bin/bash
# Native Bash 3.2. Configuration is parsed as data, never evaluated.
set -euo pipefail
umask 077
export LC_ALL=C
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
platform=unsupported
case "$(uname -s)" in Darwin) platform=macos ;; Linux) platform=linux ;; esac
if [[ "$platform" == macos ]]; then export PATH="$PATH:/opt/homebrew/bin:/usr/local/bin"; fi
action="${1:-check}"
[[ $# -eq 0 ]] || shift
bundle=""
bundle_dir=""
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
case "$action" in check|setup|verify|connect|sftp|disconnect|mosh) ;; *) fail INVALID_ACTION "动作：check/setup/verify/connect/sftp/disconnect/mosh。" ;; esac
if $install_clients; then [[ "$action" == setup ]] || fail INVALID_ARGUMENT "只有 setup 可以安装客户端。"; fi
require_tunnel_admin() {
    if ! sudo -n true >/dev/null 2>&1; then
        # Logging may redirect stderr; user input still comes from the terminal.
        [[ -t 0 ]] || fail NEEDS_ADMIN "请在本人可输入密码的交互终端运行同一条命令；不要把 sudo 密码发给 Agent，也不要仅在另一终端运行 sudo -v。"
        sudo -v || fail NEEDS_ADMIN "需要本人完成 sudo 授权。"
    fi
}
if [[ -z "$bundle" ]]; then
    primary_dir="$HOME/Downloads/employee-workspace"
    fallback_dir="$repo_dir/deployment"
    bundle_dir="$primary_dir"
    # A partial primary delivery must never silently select another device's fallback.
    primary_seen=false
    for file in device-bundle.zip device-bundle.sha256 README.md; do
        if [[ -e "$primary_dir/$file" || -L "$primary_dir/$file" ]]; then primary_seen=true; fi
    done
    if ! $primary_seen; then
        for file in device-bundle.zip device-bundle.sha256 README.md; do
            if [[ -e "$fallback_dir/$file" || -L "$fallback_dir/$file" ]]; then
                bundle_dir="$fallback_dir"
                break
            fi
        done
    fi
    bundle="$bundle_dir/device-bundle.zip"
fi
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
            require_tunnel_admin
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
    [[ -n "$bundle_dir" ]] || fail PACKAGE_HASH_REQUIRED "外部设备包必须提供 --sha256。"
    [[ -f "$bundle" && ! -L "$bundle" && -f "$bundle_dir/device-bundle.sha256" && ! -L "$bundle_dir/device-bundle.sha256" ]] ||
        fail PACKAGE_MISSING "请先从管理员提供的私人链接下载接入包，仅解开外层 ZIP，并将三份文件保存到 ~/Downloads/employee-workspace/；找不到时可使用项目 deployment/。"
    expected_sha="$(tr -d '\r\n' < "$bundle_dir/device-bundle.sha256")"
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
profile=existing
ssh_user="$device"
ssh_alias=workspace
wg_port=51820
wg_keepalive=25
vnet_pattern='^ws-[a-f0-9]{8}$'
vm_pattern='^employee-[a-z0-9-]{1,40}$'
extra_fields=""
access_mode=desktop
mosh_ports=""
if [[ "$schema" == 2 && "$tool_version" == 2.0.0 ]]; then
    profile="$(json_get profile)" || fail MANIFEST_INVALID "Missing profile."
    ssh_user="$(json_get ssh_user)" || fail MANIFEST_INVALID "Missing native SSH user."
    ssh_alias="$(json_get ssh_alias)" || fail MANIFEST_INVALID "Missing profile alias."
    [[ "$profile" == oci-hub && "$ssh_user" == employee && "$ssh_alias" == "oci-hub-$device" ]] || fail MANIFEST_INVALID "Invalid native SSH profile."
    access_mode="$(json_get access_mode || printf desktop)"
    if [[ "$access_mode" == mosh ]]; then
        mosh_ports="$(json_get mosh_ports)" || fail MANIFEST_INVALID "Missing device Mosh ports."
        [[ "$mosh_ports" =~ ^(6[01][0-9]{3}):(6[01][0-9]{3})$ ]] || fail MANIFEST_INVALID "Invalid Mosh ports."
        [[ "${mosh_ports%:*}" -le "${mosh_ports#*:}" && "${mosh_ports#*:}" -le 61000 ]] || fail MANIFEST_INVALID "Invalid Mosh range."
        vm_pattern='^(employee|oci-hub)-[a-z0-9-]{1,40}$'
        extra_fields="$(printf '%s\n' profile ssh_user ssh_alias access_mode mosh_ports)"
    elif [[ "$access_mode" == desktop ]]; then
        desktop_url="$(json_get desktop_url)" || fail MANIFEST_INVALID "Missing target desktop URL."
        tls_pin="$(json_get tls_certificate_sha256)" || fail MANIFEST_INVALID "Missing target TLS pin."
        [[ "$desktop_url" == "https://$gateway:8443/" && "$tls_pin" =~ ^[a-f0-9]{64}$ ]] || fail MANIFEST_INVALID "Invalid desktop identity."
        vm_pattern='^oci-hub-[a-z0-9-]{1,40}$'
        extra_fields="$(printf '%s\n' profile ssh_user ssh_alias desktop_url tls_certificate_sha256)"
    else fail MANIFEST_INVALID "Unsupported access mode."; fi
    wg_port=51824
    wg_keepalive=15
    vnet_pattern='^wh-[a-f0-9]{8}$'
elif [[ "$schema" != 1 || "$tool_version" != 1.0.0 ]]; then
    fail PACKAGE_VERSION_UNSUPPORTED "Unsupported bundle version."
fi
expected_fields="$(printf '%s\n' schema_version tool_version device_id vm_hostname ssh_gateway wireguard_address wireguard_public_key client_wireguard_public_key wireguard_endpoint tunnel_name $extra_fields | sort)"
if [[ "$platform" == macos ]]; then
    actual_fields="$(/usr/bin/plutil -convert xml1 -o - "$stage/manifest.json" 2>/dev/null | awk -F '[<>]' '/<key>/ {print $3}' | sort)"
else
    actual_fields="$(jq -r 'keys[]' "$stage/manifest.json" 2>/dev/null | sort)"
fi
[[ "$actual_fields" == "$expected_fields" ]] || fail MANIFEST_INVALID "Unexpected manifest fields."
[[ "$device" =~ ^[a-z][a-z0-9-]{0,27}$ && "$vm_hostname" =~ $vm_pattern &&
   "$tunnel" =~ $vnet_pattern && "$peer" =~ ^[A-Za-z0-9+/]{43}=$ &&
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
    state_root="$HOME/EmployeeWorkspace/devices"
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
if [[ "$profile" == oci-hub ]]; then state_root="$state_root/oci-hub"; fi
state="$state_root/$device"
case "$state_root/" in "$repo_dir/"*) fail STATE_IN_REPOSITORY "Install state outside this repository." ;; esac
if [[ -d "$state_root" ]]; then
    [[ ! -L "$state_root" && "$(ls -nd "$state_root" | awk '{print $3}')" == "$(id -u)" ]] ||
        fail STATE_PATH_UNSAFE "State directory owner or type mismatch."
fi
if [[ "$platform" == macos ]] && $install_clients; then
    if ! command -v wg >/dev/null || ! command -v wg-quick >/dev/null || ! command -v wireguard-go >/dev/null; then
        command -v brew >/dev/null || fail HOMEBREW_REQUIRED "请按 docs/manual-macos.md 安装 Homebrew，再重跑相同命令。"
        brew install wireguard-tools >/dev/null 2>&1 || fail INSTALL_FAILED "WireGuard CLI 安装失败；检查 Homebrew 安装结果。"
    fi
fi
wg_bin="$(command -v wg || true)"
wg_quick_bin="$(command -v wg-quick || true)"
wg_bash_bin=""
wireguard_go_bin="$(command -v wireguard-go || true)"
wg_runtime_path=""
if [[ -n "$wg_bin" && -n "$wg_quick_bin" ]]; then
    if [[ "$platform" == macos ]]; then
        # The bootstrap itself supports Bash 3.2; Darwin wg-quick requires Bash 4+.
        for candidate in "$(command -v bash || true)" /opt/homebrew/bin/bash /usr/local/bin/bash; do
            [[ -n "$candidate" && -x "$candidate" ]] || continue
            if "$candidate" --noprofile --norc -c '[[ ${BASH_VERSINFO[0]} -ge 4 ]]' >/dev/null 2>&1; then
                wg_bash_bin="$candidate"
                break
            fi
        done
        if [[ -n "$wg_bash_bin" && -n "$wireguard_go_bin" ]]; then
            wg_runtime_path="${wg_bin%/*}:${wireguard_go_bin%/*}:${wg_bash_bin%/*}:/usr/bin:/bin:/usr/sbin:/sbin"
            if "$wg_bin" --version >/dev/null 2>&1 &&
               "$wireguard_go_bin" --version >/dev/null 2>&1 &&
               /usr/bin/env PATH="$wg_runtime_path" WG_QUICK_USERSPACE_IMPLEMENTATION="$wireguard_go_bin" \
                   "$wg_bash_bin" "$wg_quick_bin" --help >/dev/null 2>&1; then
                client_ready=true
            fi
        fi
    elif command -v ip >/dev/null; then client_ready=true; fi
fi
run_wg_quick() {
    if [[ "$platform" == macos ]]; then
        # Set these after sudo resets its environment; never rely on env-bash or sudo -E.
        sudo /usr/bin/env PATH="$wg_runtime_path" WG_QUICK_USERSPACE_IMPLEMENTATION="$wireguard_go_bin" \
            "$wg_bash_bin" "$wg_quick_bin" "$@"
    else
        sudo "$wg_quick_bin" "$@"
    fi
}
wg_interface=""
write_configs() {
    cat > "$stage/$tunnel.conf" <<EOF
[Interface]
PrivateKey = $wg_private
Address = $address

[Peer]
PublicKey = $peer
Endpoint = $endpoint:$wg_port
AllowedIPs = $gateway/32
PersistentKeepalive = $wg_keepalive
EOF
    cat > "$stage/ssh_config" <<EOF
Host $ssh_alias
    HostName $gateway
    User $ssh_user
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
run_bounded() {
    local seconds="$1" command_pid watcher status
    shift
    mkfifo "$stage/deadline"
    exec 9<>"$stage/deadline"
    exec 8<&0
    "$@" <&8 &
    command_pid=$!
    (
        if ! IFS= read -r -t "$seconds" -u 9; then
            : > "$stage/timed-out"
            kill -KILL "$command_pid" 2>/dev/null || true
        fi
    ) &
    watcher=$!
    if wait "$command_pid"; then status=0; else status=$?; fi
    printf 'done\n' >&9
    wait "$watcher" || true
    exec 8<&- 9>&-
    rm -f "$stage/deadline"
    [[ ! -e "$stage/timed-out" ]] || return 124
    return "$status"
}
normalize_terminal() {
    awk 'BEGIN {
        esc=sprintf("%c",27); bell=sprintf("%c",7)
        osc=esc "\\][^" esc bell "]*(" bell "|" esc "\\\\)"
        csi=esc "\\[[0-?]*[ -/]*[@-~]"
    } {gsub(osc, ""); gsub(csi, ""); gsub(/\r/, ""); print}'
}
resolve_tunnel_interface() {
    local interfaces mapped
    interfaces="$(sudo "$wg_bin" show interfaces 2>/dev/null)" || fail TUNNEL_INSPECTION_FAILED "无法读取 WireGuard 接口；未修改网络。"
    if [[ "$platform" == macos ]]; then
        # wg-quick owns this mapping; the GUI NetworkExtension has no such alias.
        mapped="$(sudo cat "/var/run/wireguard/$tunnel.name" 2>/dev/null)" || return 1
        [[ "$mapped" =~ ^utun[0-9]+$ ]] || return 1
    else mapped="$tunnel"; fi
    printf '%s\n' "$interfaces" | tr ' ' '\n' | awk -v target="$mapped" '$0==target {found=1} END {exit !found}' || return 1
    wg_interface="$mapped"
}
owned_tunnel() {
    local actual actual_peer allowed current_address
    resolve_tunnel_interface || return 1
    actual="$(sudo "$wg_bin" show "$wg_interface" public-key 2>/dev/null)" || return 1
    actual_peer="$(sudo "$wg_bin" show "$wg_interface" peers 2>/dev/null)" || return 1
    allowed="$(sudo "$wg_bin" show "$wg_interface" allowed-ips 2>/dev/null)" || return 1
    if [[ "$platform" == macos ]]; then
        current_address="$(ifconfig "$wg_interface" 2>/dev/null | awk '$1=="inet" {print $2 "/32"}')"
    else current_address="$(ip -o -4 addr show dev "$wg_interface" 2>/dev/null | awk '{print $4}')"; fi
    [[ "$actual" == "$client_public" && "$actual_peer" == "$peer" &&
       "$allowed" == "$peer"$'\t'"$gateway/32" && "$current_address" == "$address" ]]
}
check_new_tunnel_route() {
    local conflicting route_info destination
    if [[ "$platform" == macos ]]; then
        route_info="$(route -n get "$gateway" 2>/dev/null)" || fail ROUTE_INSPECTION_FAILED "无法检查入口路由；未启动隧道。"
        destination="$(printf '%s\n' "$route_info" | awk '$1=="destination:" {print $2}')"
        [[ "$destination" == default ]] || fail ROUTE_CONFLICT "入口已有特定路由；如为旧 WireGuard App 隧道，请本人先停用，再重跑。"
        # Reject an already assigned device address, even if its route disappeared.
        conflicting="$(ifconfig -a | awk -v target="${address%/32}" '$1=="inet" && $2==target {found=1} END {print found+0}')"
    else
        conflicting="$(ip -4 route show match "$gateway" | awk '$1!="default" {bad=1} END {print bad+0}')"
    fi
    [[ "$conflicting" == 0 ]] || fail ROUTE_CONFLICT "设备地址或入口路由已被使用；未停止任何现有 VPN。"
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
        $client_ready || fail DEPENDENCY_MISSING "请运行 setup --install-clients 安装 WireGuard CLI。"
        require_tunnel_admin
        if resolve_tunnel_interface; then
            owned_tunnel || fail TUNNEL_CONFLICT "Existing tunnel does not belong to this device."
        else
            check_new_tunnel_route
            if run_wg_quick up "$state/$tunnel.conf" >"$stage/wg-quick.log" 2>&1; then tunnel_status=0
            else tunnel_status=$?; fi
            if [[ "$tunnel_status" != 0 ]]; then
                if grep -q 'Version mismatch: bash' "$stage/wg-quick.log"; then
                    fail TUNNEL_START_FAILED "wg-quick 的 Bash 版本不兼容；更新项目后重跑，不要重置设备身份。"
                fi
                fail TUNNEL_START_FAILED "WireGuard 启动失败（退出码 $tunnel_status）；停止并报告此错误，不要修改其他 VPN。"
            fi
            owned_tunnel || fail TUNNEL_CONFLICT "Started tunnel does not match the assigned identity."
        fi
        report CONFIGURED ;;
    disconnect)
        require_installed
        $client_ready || fail DEPENDENCY_MISSING "缺少 WireGuard CLI。"
        require_tunnel_admin
        if resolve_tunnel_interface; then
            owned_tunnel || fail TUNNEL_CONFLICT "Tunnel ownership mismatch; nothing stopped."
            run_wg_quick down "$state/$tunnel.conf" >/dev/null 2>&1 ||
                fail TUNNEL_STOP_FAILED "Tunnel did not stop."
        elif [[ "$platform" == macos ]]; then
            check_new_tunnel_route
        fi
        report DISCONNECTED ;;
    mosh)
        require_installed
        [[ "$profile" == oci-hub && "$access_mode" == mosh ]] || fail MOSH_NOT_CONFIGURED "This bundle has no native Mosh assignment."
        command -v mosh >/dev/null && command -v mosh-client >/dev/null || fail MOSH_CLIENT_MISSING "Install Mosh in this terminal environment with user approval; see docs/mosh.md."
        # Mosh is interactive: never run it through a pipe or record its handshake key.
        [[ -t 0 && -t 1 ]] || fail INTERACTIVE_TERMINAL_REQUIRED "Run this same mosh command in the user's interactive terminal."
        config="$state/ssh_config"
        cleanup
        stage=""
        # --ssh is parsed as a command by Mosh; quote the path as shell data.
        quoted_config="$(jq -nr --arg path "$config" '$path|@sh')"
        exec mosh --ssh="ssh -F $quoted_config" --server=workspace-mosh --port="$mosh_ports" "$ssh_alias"
        ;;
    connect|sftp)
        require_installed
        cleanup
        stage=""
        if [[ "$action" == connect ]]; then exec ssh -F "$state/ssh_config" -tt "$ssh_alias"
        else exec sftp -F "$state/ssh_config" "$ssh_alias"; fi ;;
    verify)
        require_installed
        $client_ready || fail DEPENDENCY_MISSING "缺少 WireGuard CLI。"
        require_tunnel_admin
        owned_tunnel || fail TUNNEL_CONFLICT "Live tunnel identity or routing mismatch."
        nonce="$(od -An -N12 -tx1 /dev/urandom | tr -d ' \n')"
        prefix="WS_${nonce}"
        # One complete command fits the PTY line discipline. No queued commands
        # remain for a CLI or shell hook to consume. No gateway command is appended.
        if [[ "$profile" == oci-hub && "$access_mode" == desktop ]]; then
            command -v openssl >/dev/null || fail DEPENDENCY_MISSING "TLS pin verification requires openssl."
            run_bounded 15 openssl s_client -connect "$gateway:8443" -servername "$gateway" < /dev/null > "$stage/tls-peer" 2>/dev/null || fail TLS_PIN_FAILED "Target TLS handshake failed."
            openssl x509 -in "$stage/tls-peer" -outform DER -out "$stage/tls.der" 2>/dev/null || fail TLS_PIN_FAILED "Target TLS certificate invalid."
            [[ "$(hash_file "$stage/tls.der")" == "$tls_pin" ]] || fail TLS_PIN_FAILED "Target TLS identity mismatch."
        fi
        payload="$(sed -e "s/__PREFIX__/$prefix/g" -e "s/__VM__/$vm_hostname/g" "$repo_dir/scripts/verify-session.py" | base64 | tr -d '\r\n')"
        [[ ${#payload} -lt 3500 ]] || fail SSH_PROTOCOL_FAILED "Verification payload exceeds the PTY line limit."
        printf "stty -echo; exec python3 -c 'import base64;exec(base64.b64decode(\"%s\"))' </dev/null\n" "$payload" > "$stage/verify-input"
        if run_bounded 60 ssh -F "$state/ssh_config" -tt "$ssh_alias" < "$stage/verify-input" > "$stage/ssh-output" 2> "$stage/ssh-error"; then
            connection_status=0
        else connection_status=$?; fi
        [[ "$connection_status" != 124 ]] || fail VERIFY_TIMEOUT "SSH verification exceeded 60 seconds; stop and report this code."
        if [[ "$connection_status" != 0 ]]; then
            if grep -Eq 'REMOTE HOST IDENTIFICATION HAS CHANGED|Host key verification failed' "$stage/ssh-error"; then
                fail SSH_HOST_KEY_MISMATCH "Host identity changed; do not disable host verification."
            fi
            fail SSH_CONNECTION_FAILED "Check WireGuard, device permission and networking."
        fi
        normalize_terminal < "$stage/ssh-output" > "$stage/lines"
        for marker in BEGIN END; do
            [[ "$(grep -cx "${prefix}_$marker" "$stage/lines" || true)" == 1 ]] || fail SSH_PROTOCOL_FAILED "Verification frame is missing or duplicated."
        done
        for field in USER VM SUDO CLI; do
            [[ "$(grep -Ec "^${prefix}_${field}=(passed|failed)$" "$stage/lines" || true)" == 1 ]] || fail SSH_PROTOCOL_FAILED "Verification field is missing or duplicated."
        done
        [[ "$(grep -Ec "^${prefix}_AUTH=(passed|user_action_required|unavailable)$" "$stage/lines" || true)" == 1 ]] || fail SSH_PROTOCOL_FAILED "Authentication field is missing or duplicated."
        grep -qx "${prefix}_USER=passed" "$stage/lines" && ssh_identity=passed
        grep -qx "${prefix}_VM=passed" "$stage/lines" && assigned_vm=passed
        grep -qx "${prefix}_SUDO=passed" "$stage/lines" && sudo_check=passed
        grep -qx "${prefix}_CLI=passed" "$stage/lines" && cli_check=passed
        claude_auth=unavailable
        if grep -qx "${prefix}_AUTH=passed" "$stage/lines"; then claude_auth=passed
        elif grep -qx "${prefix}_AUTH=user_action_required" "$stage/lines"; then claude_auth=user_action_required; fi
        [[ "$ssh_identity" == passed && "$assigned_vm" == passed ]] ||
            fail WORKSPACE_ID_MISMATCH "Wrong user or VM; file verification was not attempted."
        if [[ "$platform" == macos || "$platform" == linux ]]; then
            timestamp="$(sudo "$wg_bin" show "$wg_interface" latest-handshakes 2>/dev/null | awk -v peer="$peer" '$1==peer {print $2}')"
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
        if run_bounded 30 sftp -F "$state/ssh_config" -b "$stage/sftp-batch" "$ssh_alias" > "$stage/sftp-output" 2>&1; then transfer_status=0
        else transfer_status=$?; fi
        [[ "$transfer_status" != 124 ]] || fail VERIFY_TIMEOUT "SFTP verification exceeded 30 seconds; stop and report this code."
        [[ "$transfer_status" == 0 ]] || fail SFTP_ROUNDTRIP_FAILED "SFTP roundtrip failed; unverified remote content left untouched."
        cmp -s "$stage/probe.txt" "$stage/returned.txt" || fail SFTP_CONTENT_MISMATCH "SFTP content differs; test directory preserved."
        printf 'rm %s/probe.txt\nrmdir %s\n' "$remote_dir" "$remote_dir" > "$stage/sftp-cleanup"
        if run_bounded 30 sftp -F "$state/ssh_config" -b "$stage/sftp-cleanup" "$ssh_alias" >/dev/null 2>&1; then cleanup_status=0
        else cleanup_status=$?; fi
        [[ "$cleanup_status" != 124 ]] || fail VERIFY_TIMEOUT "SFTP cleanup exceeded 30 seconds; stop and report this code."
        [[ "$cleanup_status" == 0 ]] || fail SFTP_CLEANUP_FAILED "Could not clean this test directory; project files untouched."
        sftp_check=passed
        [[ "$sudo_check" == passed && "$cli_check" == passed ]] || fail VM_BASELINE_FAILED "VM sudo or CLI checks failed."
        [[ "$claude_auth" != unavailable ]] || fail CLAUDE_AUTH_CHECK_FAILED "Claude status could not be checked; do not treat this as logged out."
        if [[ "$claude_auth" != passed ]]; then report CLAUDE_AUTH_USER_PENDING
        elif [[ "$handshake" == unavailable ]]; then report HANDSHAKE_INSPECTION_UNAVAILABLE
        else report CONNECTION_VERIFIED; fi ;;
esac
