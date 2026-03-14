# Saga Catalog

This directory contains the installable SagaOS modules.

Each saga is an optional component that can be installed beside the core Saga
desktop layer.

## Available Sagas

### Hrafn

Quote:

> "Often is counsel needed, and not force alone."
>
> Hrafnkels saga

What it does:

Hrafn is SagaOS's terminal-first operational awareness engine. It aggregates
local calendar state and tasks, computes deterministic signals, and exposes
them for terminal dashboards, widgets, and automation.

Install:

```bash
./cli/saga install hrafn
```

### Njal

Quote:

> "With law shall our land be built up, but with lawlessness laid waste."
>
> Njals saga

What it does:

Njal is SagaOS's shell environment module. It installs and wires the Zsh-based
terminal workflow configuration used by SagaOS.

Install:

```bash
./cli/saga install njal
```

Help:

```bash
./cli/saga help njal
```
