---
name: bandit-server
description: Setup and build GamesGlobal Bandit slot game server repositories — cloning, NuGet configuration, FakeRng setup for macOS/Linux, building, and simulation CLI parameters/behaviours reference. Use when setting up a Bandit game server project, configuring simulation runs, or preparing a repo before running simulations. For end-to-end simulation workflows, use the task-bandit-simulations skill.
---

# Bandit Game Server

## Table of Contents

- [Repository Structure](#repository-structure)
- [Setup Before Building](#setup-before-building)
  - [1. Install .NET SDK (Linux cloud agents)](#1-install-net-sdk-linux-cloud-agents)
  - [2. Create Directory.Build.props](#2-create-directorybuildprops)
  - [3. Configure NuGet credentials](#3-configure-nuget-credentials)
  - [4. Fix RNG for macOS/Linux](#4-fix-rng-for-macoslinux)
  - [5. Build](#5-build)
- [Running Multiple Variants](#running-multiple-variants)
- [Simulations](#simulations)
  - [Simulation Parameters](#simulation-parameters)
  - [Behaviours](#behaviours)
- [Next Steps](#next-steps)

---

Bandit is the C# game server framework provided by GamesGlobal. Each game has its own repository under `naileditgames` on GamesGlobal GitLab. See the `gamesglobal-gitlab` skill for cloning.

## Repository Structure

```
src/
├── <GameName>.sln
├── <GameName>/                    # Main game math service
│   ├── Config/
│   │   ├── V90/                   # RTP variant 90%
│   │   ├── V92/                   # RTP variant 92%
│   │   ├── V94/                   # RTP variant 94%
│   │   └── V96/                   # RTP variant 96%
│   │       ├── GameProperties.json
│   │       ├── Install.xml        # Contains ModuleId for this variant
│   │       ├── EmptyReels.xml
│   │       └── SkinMapping.xml
│   ├── Properties/
│   │   └── launchSettings.json    # Run profiles including Simulation
│   └── rng.config.json
├── <GameName>.Tests/
└── <GameName>.Tools/
```

## Setup Before Building

### 1. Install .NET SDK (Linux cloud agents)

Cloud agent VMs do not have .NET pre-installed. Install .NET 6 before proceeding:

```bash
wget -q https://dot.net/v1/dotnet-install.sh -O /tmp/dotnet-install.sh
chmod +x /tmp/dotnet-install.sh
sudo /tmp/dotnet-install.sh --version 6.0.427 --install-dir /usr/local/dotnet
sudo chmod -R a+rx /usr/local/dotnet
export DOTNET_ROOT=/usr/local/dotnet
export PATH=$PATH:/usr/local/dotnet
dotnet --version   # verify
```

Add both exports to `~/.bashrc` to persist across shell sessions. Skip this step on macOS (dotnet is typically available).

### 2. Create Directory.Build.props

Before building, create `src/Directory.Build.props` specifying the RTP variant and Module ID:

```xml
<Project>
  <PropertyGroup>
    <GameVariant>V96</GameVariant>
    <GameMid>104800</GameMid>
  </PropertyGroup>
</Project>
```

Find the correct `GameMid` for each variant from `Config/<Variant>/Install.xml`:

```bash
for v in V90 V92 V94 V96; do
  mid=$(grep "ModuleId" src/<GameName>/Config/$v/Install.xml | grep -o '[0-9]*')
  echo "$v -> $mid"
done
```

### 3. Configure NuGet credentials

The game depends on private NuGet packages hosted on GamesGlobal GitLab. Create `src/nuget.config`.

> **Important:** dotnet does **not** expand shell environment variables (e.g. `${GG_GITLAB_TOKEN}`) inside `nuget.config`. You must write the actual credential values. Use a shell heredoc so the variables are interpolated by the shell at write time:

```bash
cat > src/nuget.config << EOF
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" protocolVersion="3" />
    <add key="GameTechGit" value="https://gametechgit.gamesglobal.com/api/v4/projects/229/packages/nuget/index.json" />
    <add key="BanditExternalFeed" value="https://gametechgit.gamesglobal.com/api/v4/projects/802/packages/nuget/index.json" />
  </packageSources>
  <packageSourceCredentials>
    <GameTechGit>
      <add key="Username" value="${GG_GITLAB_USERNAME}" />
      <add key="ClearTextPassword" value="${GG_GITLAB_TOKEN}" />
    </GameTechGit>
    <BanditExternalFeed>
      <add key="Username" value="${GG_GITLAB_USERNAME}" />
      <add key="ClearTextPassword" value="${GG_GITLAB_TOKEN}" />
    </BanditExternalFeed>
  </packageSourceCredentials>
</configuration>
EOF
```

Credentials come from environment variables `GG_GITLAB_USERNAME` and `GG_GITLAB_TOKEN` (injected as secrets in cloud agents, or sourced from `.env` locally).

### 4. Fix RNG for macOS/Linux

The default `rng.config.json` uses `MGS.Random.Pool.dll` which depends on Windows API (`QueryPerformanceCounter`) and crashes on macOS/Linux. Skip this step on Windows.

Edit `src/<GameName>/rng.config.json`:

```json
{
  "RngConfig" : {
    "Kind" : "MGS.RNG",
    "Assembly": "HttpGames.FakeRng.dll",
    "Type": "FakeRandomPoolFactory"
  }
}
```

Add the FakeRng package to `<GameName>.csproj` (same version as other CasinoServices packages):

```xml
<PackageReference Include="CasinoServices.Library.HttpGames.FakeRng" Version="5.4.3.8"/>
```

### 5. Build

Build **only the main game project**, not the whole solution. The `.Tests` and `.Tools` projects attempt to restore packages from the private NuGet feeds for standard .NET libraries (e.g. `NUnit`, `System.Reflection`) and fail with `NU1301` errors on cloud agents. The main project is all that is needed for simulations.

```bash
cd src
dotnet build <GameName>/<GameName>.csproj
```

## Running Multiple Variants

When running simulations for several variants (e.g. V96, V94, V92, V90), you must rebuild for each variant because `GameVariant` and `GameMid` are baked into the binary at build time via `Directory.Build.props`.

**Recommended pattern — build once per variant, copy binaries, run from copies:**

```bash
export DOTNET_ROOT=/usr/local/dotnet
export PATH=$PATH:/usr/local/dotnet

declare -A MIDS=([V96]=105145 [V94]=105146 [V92]=105147 [V90]=105148)

for variant in V96 V94 V92 V90; do
  mid=${MIDS[$variant]}

  # Update Directory.Build.props for this variant
  cat > src/Directory.Build.props << EOF
<Project>
  <PropertyGroup>
    <GameVariant>$variant</GameVariant>
    <GameMid>$mid</GameMid>
  </PropertyGroup>
</Project>
EOF

  # Build
  dotnet build src/<GameName>/<GameName>.csproj

  # Copy binaries to a per-variant directory
  mkdir -p tmp/builds/$variant
  cp -r src/<GameName>/bin/Debug/net6.0/* tmp/builds/$variant/
done
```

Then run each variant directly from its binary — **no need to rebuild again**:

```bash
dotnet tmp/builds/V96/$mid.dll -c \
  --numOfGames=10000000 \
  --numOfThreads=8 \
  --logFrequency=5000 \
  --logMethod=latest \
  --logPath=/absolute/path/to/results/<GameName>V96_<strategy>/ \
  --behavioursPath=/absolute/path/to/behaviours/run_V96_<strategy>/
```

This avoids rebuilding between every simulation run and allows all variants to exist on disk simultaneously.

## Simulations

### Simulation Parameters

| Parameter | Description |
|---|---|
| `-c` | Required — starts in interactive console mode |
| `--csv` | Generates spin-level CSV file (omit if not needed) |
| `--numOfGames` | Number of spins to simulate |
| `--numOfThreads` | Number of parallel threads |
| `--logFrequency` | Write to CSV every N games — keep low (e.g. 5000) to avoid running out of RAM |
| `--logMethod` | `latest` = overwrite file, `append` = append to existing |
| `--logPath` | Output directory for `.txt` summary and `.csv` spin data — use absolute path |
| `--behavioursPath` | Directory containing behaviour JSON files — use absolute path |

> **Always add `--no-launch-profile`** to the `dotnet run` command. Without it, `dotnet run` picks up the `Simulation` profile from `launchSettings.json` and appends its own arguments (including a conflicting `--behavioursPath=../../`) to yours, causing the app to fail.
>
> When running directly from the compiled DLL (`dotnet <mid>.dll`), `--no-launch-profile` is not needed — launch profiles only apply to `dotnet run`.

### Behaviours

Behaviour JSON files in `--behavioursPath` override session parameters (bet size, game mode, etc.). They are `DISABLED` by default — must be activated via Configure Session → Behaviours → Activate.

The Behaviours menu has two options:
- `1` — **Activate Behaviours** (activates **all** JSON files in `--behavioursPath` at once)
- `2` — Deactivate Behaviours

This is why it is important to keep **only one strategy file** per `--behavioursPath` directory per run. Putting multiple files in the same directory and pressing `1` will activate all of them simultaneously.

Example `MaxBetStrategy.json`:

```json
[
  {
    "ModuleId": 104800,
    "ClientId": 50300,
    "ProductId": 0,
    "Username": "",
    "BehaviourName": "Core.Slots.StockSpinStrategy",
    "Guid": "f486ee5a-ee86-4756-99d8-2a97db9a4470",
    "Options": {
      "NumCoins$0": "Max",
      "CoinSize$0": "Max",
      "BetMultiplier$0": "Max"
    }
  }
]
```

The `ModuleId` in the file does not need to exactly match the running game's MID. Save each behaviour run to its own output directory (e.g. `results/V94/maxbet/`).
