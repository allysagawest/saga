# Saga

Saga is a modular, user-space Hyprland desktop layer for Linux.

It provides:
- a complete Hyprland UI stack
- optional modules ("sagas"), starting with `njal`
- centralized shortcuts and theming
- event-driven UI updates via the Saga daemon socket

## Highlights

- User-space install only (`~/.config`, `~/.local/bin`, `~/.local/share`)
- No writes to `/etc` or `/usr`
- Symlink-based config management for clean removal
- Distro-aware dependency installation (Arch/Fedora/Debian/Ubuntu)
- Conflict-safe shortcut layer (`SUPER+ALT+...`)
- Event-bus-driven UI state (no high-frequency polling loops)

## Supported distros

- Arch (`pacman`)
- Fedora (`dnf`)
- Debian (`apt`)
- Ubuntu (`apt`, uses Debian package list)

## Architecture

Saga consists of:

1. `cli/saga`
The main user CLI (`install`, `update`, `doctor`, `theme`, `query`, `subscribe`, etc.)

2. Desktop configs under `desktop/`
Hyprland, Waybar, EWW, SwayNC, Walker

3. Theme engine under `themes/`
`theme.json` + generated variables/styles

4. Optional modules under `sagas/`
Current module: `njal` (Zsh environment)

5. Event bus integration
UI clients consume Saga daemon data from socket:
`~/.local/share/saga/saga.sock`

## What Saga installs

### User-space paths

- `~/.local/bin/saga` (symlink to repo CLI)
- `~/.local/share/saga/state.json`
- symlinked configs:
  - `~/.config/hypr -> <repo>/desktop/hypr`
  - `~/.config/waybar -> <repo>/desktop/waybar`
  - `~/.config/swaync -> <repo>/desktop/swaync`
  - `~/.config/eww -> <repo>/desktop/eww`
  - `~/.config/walker -> <repo>/desktop/walker`

### Package groups

Saga installs missing packages (via distro package manager) from `packages/*.txt`.

Core desktop:
- hyprland
- waybar
- walker
- swaynotificationcenter
- networkmanager
- pipewire
- wireplumber
- kitty
- hyprlock
- hypridle
- swww
- eww
- xdg-desktop-portal-hyprland
- bluez
- brightnessctl
- inotify-tools

CLI utilities:
- python3
- git
- curl
- wget
- ripgrep
- fd
- bat
- eza
- fzf
- jq

Optional `njal` module packages:
- zsh
- starship
- zoxide
- btop
- lazygit
- tmux

## Quick start

### 1. Clone and run install

```bash
chmod +x cli/saga scripts/*.sh sagas/njal/*.sh
./cli/saga install
```

Install with Njál module:

```bash
./cli/saga install --njal
```

During install, Saga:
- detects distro
- installs missing dependencies (with `sudo` package-manager calls)
- writes state file
- applies theme
- generates Hyprland binds
- reloads Hyprland (if available)

## Command reference

| Command | What it does |
|---|---|
| `saga install` | Installs the Saga desktop layer and dependencies. |
| `saga install --njal` | Installs Saga plus the `njal` module. |
| `saga update` | Pulls latest repo changes, updates state, refreshes installed modules, reapplies theme. |
| `saga remove <module>` | Uninstalls a Saga module and removes it from Saga state. |
| `saga list` | Lists installed Saga modules and versions. |
| `saga version` | Shows Saga version, active theme, and installed modules. |
| `saga doctor` | Runs health checks (services, Wayland, socket, portal, shortcut conflicts). |
| `saga generate-binds` | Reads `config/shortcuts.json` and regenerates `~/.config/hypr/saga-binds.conf`. |
| `saga theme apply [theme]` | Rebuilds theme-derived files and reloads UI components. |
| `saga dev [theme]` | Watches `themes/` and auto-applies theme updates on file changes. |
| `saga query <metric>` | Queries one metric from Saga daemon socket (`saga.sock`). |
| `saga subscribe <event>` | Subscribes to a live event stream from Saga daemon. |
| `saga waybar-stream <metric>` | Emits streaming Waybar JSON updates for custom modules. |
| `saga eww-stream` | Starts EWW event listeners and pushes Saga state into widget vars. |
| `saga ui-listen` | Listens for UI events (like `theme_reload`) and reloads UI processes. |
| `saga panel toggle <panel>` | Opens/closes an EWW panel (`control_center`, `wifi_menu`, etc.). |
| `saga panel refresh all` | Refreshes all EWW panel variables from Saga state. |
| `saga panel set-volume <0-100>` | Sets audio volume and refreshes panel state. |
| `saga panel set-brightness <0-100>` | Sets brightness and refreshes panel state. |
| `saga launcher [app\\|files\\|commands]` | Opens Walker in app, file search, or command mode. |
| `saga wifi connect <ssid> [password]` | Connects to WiFi using NetworkManager (`nmcli`). |
| `saga bluetooth connect <mac>` | Connects to a paired Bluetooth device. |
| `saga audio set-default <output-id>` | Sets PipeWire default output sink (`wpctl`). |
| `saga power lock` | Locks the screen with `hyprlock`. |
| `saga power suspend` | Suspends the system (`systemctl suspend`). |
| `saga power restart` | Reboots the system (`systemctl reboot`). |
| `saga power shutdown` | Powers off the system (`systemctl poweroff`). |

Common event bus examples:

```bash
saga query cpu
saga query volume
saga subscribe cpu_update
saga subscribe theme_reload
```

## Shortcuts and keybinds

Central config:
- `config/shortcuts.json`

Default bindings use conflict-safe modifier layer:
- `SUPER + ALT + SPACE` launcher
- `SUPER + ALT + ENTER` terminal
- `SUPER + ALT + C` control center
- `SUPER + ALT + N` notifications
- `SUPER + ALT + W` wifi menu
- `SUPER + ALT + B` bluetooth menu
- `SUPER + ALT + V` audio
- `SUPER + ALT + L` brightness
- `SUPER + ALT + I` system stats
- `SUPER + ALT + P` power menu
- `SUPER + ALT + F` file search

After editing shortcuts:

```bash
saga generate-binds
hyprctl reload
```

## Theming

Default theme:
- `themes/saga-cyberpunk/theme.json`

Apply:

```bash
saga theme apply saga-cyberpunk
```

Theme apply regenerates:
- `themes/<theme>/variables.css`
- `themes/<theme>/variables.scss`
- `desktop/waybar/style.css`
- `desktop/eww/eww.scss`
- `desktop/walker/style.css`
- `desktop/hypr/theme.conf`

Then it reloads UI components where available.

## Event bus model (important)

Saga UI is wired to use Saga daemon events/state as source of truth.

Socket path:
- `~/.local/share/saga/saga.sock`

Protocol (newline-delimited JSON):
- query request: `{"command":"query","metric":"cpu"}`
- subscribe request: `{"command":"subscribe","event":"cpu_update"}`

Examples:
- response: `{"cpu":13}`
- event: `{"event":"cpu_update","value":14}`

If the socket is missing, commands fail fast with a clear error.

## Uninstall

### Remove module only

```bash
saga remove njal
```

### Remove Saga desktop configs/state

```bash
./scripts/uninstall-desktop.sh
```

This removes Saga-managed symlinks/config/state only.
It does **not** uninstall system packages.

## Health checks and troubleshooting

Run:

```bash
saga doctor
```

Doctor checks:
- Hyprland command availability
- Wayland session detection
- NetworkManager service state
- PipeWire user service state
- portal command presence
- Saga socket presence
- shortcut conflicts against common Hyprland defaults

Common issues:

1. `error: saga socket not found`
Start `sagad` so `~/.local/share/saga/saga.sock` exists.

2. Waybar/EWW not updating live
Confirm event listeners are running (`saga eww-stream`, `saga ui-listen`) and daemon publishes events.

3. Keybind changes not applied
Run `saga generate-binds` then `hyprctl reload`.

4. Package name mismatch on distro
Edit the relevant `packages/<distro>.txt` entry and re-run install.

## Development workflow

Theme iteration:

```bash
saga dev
```

This watches `themes/` via `inotifywait` and reapplies/reloads on change.

Manual validation:

```bash
bash -n cli/saga scripts/*.sh sagas/njal/*.sh
jq empty themes/saga-cyberpunk/theme.json desktop/waybar/config.jsonc desktop/swaync/config.json
```

## Repository map

- `cli/` CLI entrypoint
- `config/` centralized static config (shortcuts)
- `desktop/` Hyprland/Waybar/EWW/SwayNC/Walker config
- `sagas/` optional module installs
- `scripts/` installers, generators, stream helpers
- `themes/` theme definitions and style templates
- `packages/` distro package maps
- `state/` local project state placeholder

---

Saga is intended to be safe to run repeatedly: install/update/generate operations are idempotent and keep changes scoped to user-space.
