---
name: nailedit-game-servers
description: Describes the two types of game servers used at naileditgames — development (nkit-gs-cs) and production (GamesGlobal Bandit). Use when working with game servers, deploying games, setting up local development, or referencing server repositories.
---

# Nailedit Game Servers

## Development Servers (nkit-gs-cs)

- **Repository**: https://github.com/naileditgames/nkit-gs-cs (GitHub, monorepo)
- **Language**: C#
- **Purpose**: Local development and testing
- **Test platform**: https://gameslobby.appspot.com/ — the test lobby used to run games against these servers

Games under active development run against these servers on the local test platform.

## Production Servers (GamesGlobal Bandit)

- **Repository**: https://gametechgit.gamesglobal.com/naileditgames (GitLab, one repo per game)
- **Framework**: Bandit — provided by GamesGlobal
- **Language**: C#
- **Purpose**: Production game math services deployed to the GamesGlobal platform

Each game has its own separate repository under the `naileditgames` group in GamesGlobal GitLab. For working with these repositories, see the `gamesglobal-gitlab` skill.
