---
name: bandit-server
description: Setup and build GamesGlobal Bandit slot game server repositories — cloning, NuGet configuration, FakeRng setup for macOS/Linux, building, and simulation CLI parameters/behaviours reference. Use when setting up a Bandit game server project, configuring simulation runs, or preparing a repo before running simulations. For end-to-end simulation workflows, use the task-bandit-simulations skill.
---

# Bandit Game Server

## Table of Contents

- [Repository Structure](#repository-structure)
- [Setup Before Building](#setup-before-building)
  - [1. Create Directory.Build.props](#1-create-directorybuildprops)
  - [2. Configure NuGet credentials](#2-configure-nuget-credentials)
  - [3. Fix RNG for macOS/Linux](#3-fix-rng-for-macoslinux)
  - [4. Build](#4-build)
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

### 1. Create Directory.Build.props

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

### 2. Configure NuGet credentials

The game depends on private NuGet packages hosted on GamesGlobal GitLab. Create `src/nuget.config`:

```xml
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
```

> **Linux credential expansion:** `${GG_GITLAB_USERNAME}` / `${GG_GITLAB_TOKEN}` style placeholders do **not** expand on Linux when NuGet reads the file. Write the actual values using a heredoc so the shell substitutes them at file-creation time:
> ```bash
> cat > src/nuget.config << EOF
> ... <add key="Username" value="${GG_GITLAB_USERNAME}" /> ...
> EOF
> ```
> Using single quotes (`<< 'EOF'`) will leave the placeholders unexpanded and cause NU1301 restore failures.

### `Directory.Build.props` template

Most Bandit repos ship a `src/Directory.Build.props.temp` with the correct `GameVariant` and `GameMid` already filled in. Copy it rather than writing from scratch:

```bash
cp src/Directory.Build.props.temp src/Directory.Build.props
```

### 3. Fix RNG for macOS/Linux

The default `rng.config.json` uses `MGS.Random.Pool.dll` which depends on Windows API (`QueryPerformanceCounter`) and crashes on macOS/Linux. Skip this step on Windows.

> **Linux runtime note:** Bandit games target `net6.0` and require **both** the base runtime and the ASP.NET Core runtime. Install both with `dotnet-install.sh` — `--runtime dotnet` alone is not enough:
> ```bash
> /tmp/dotnet-install.sh --channel 6.0 --install-dir $HOME/.dotnet --runtime dotnet
> /tmp/dotnet-install.sh --channel 6.0 --install-dir $HOME/.dotnet --runtime aspnetcore
> export DOTNET_ROOT=$HOME/.dotnet
> export PATH=$PATH:$HOME/.dotnet
> ```
> If you see `Framework: 'Microsoft.AspNetCore.App', version '6.0.0' … not found`, the aspnetcore runtime is missing.

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

### 4. Build

```bash
cd src
dotnet build <GameName>.sln
```

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

### Behaviours

Behaviour JSON files in `--behavioursPath` override session parameters (bet size, game mode, etc.). They are `DISABLED` by default — must be activated via Configure Session → Behaviours → Activate.

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