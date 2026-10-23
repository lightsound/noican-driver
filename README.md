# noican-driver

The virtual audio driver (`Noican.driver`, device "Noican Microphone")
shipped with Noican, a noise-cancelling virtual microphone for macOS.

**This repository is the complete corresponding source for that driver**,
published under the GNU General Public License v3.0 as required by its
upstream, [BlackHole](https://github.com/ExistentialAudio/BlackHole). The
Noican application itself is a separate program that is not linked with
the driver and is not covered by this license.

## What is here

| Path | Contents |
|---|---|
| `external/blackhole` | Upstream BlackHole as a git submodule, pinned to release `v0.7.2` and never patched |
| `scripts/build-driver.sh` | Builds `dist/Noican.driver`; every customization (names, UID, channels, icon, factory UUID) is injected at build time |
| `scripts/install-driver.sh`, `scripts/uninstall-driver.sh` | Install into / remove from `/Library/Audio/Plug-Ins/HAL` and restart `coreaudiod` |
| `resources/Microphone.icns`, `scripts/make-icon.py` | Device icon copied into the bundle, and the script that generates it |
| `LICENSE` | Driver notice, source-availability statement, and the full GPL-3.0 text; embedded in the bundle as `Contents/Resources/LICENSE` |
| `docs/driver.md` | Identity, the full list of injected macros, and design notes |

Each released driver is tagged `driver-v<version>`, where `<version>` is
the bundle's `CFBundleShortVersionString`
(`/Library/Audio/Plug-Ins/HAL/Noican.driver/Contents/Info.plist`). Check
out that tag to get the exact source of the driver you received.

## Build

Requires macOS and Xcode (or its Command Line Tools).

```sh
git clone --recurse-submodules https://github.com/lightsound/noican-driver.git
cd noican-driver

bash scripts/build-driver.sh                      # ad-hoc (compile check)
NOICAN_CODESIGN_IDENTITY="Developer ID Application: ... (TEAMID)" \
  bash scripts/build-driver.sh                    # installable build

bash scripts/install-driver.sh                    # sudo; restarts coreaudiod
bash scripts/uninstall-driver.sh                  # sudo; complete removal
```

macOS 15+ `coreaudiod` only loads Developer-ID-signed drivers, so an ad-hoc
build is a compile check unless the machine runs with SIP relaxed.

## Trademarks

The BlackHole name, logo, and branding are trademarks of Existential Audio
Inc. and are not used by this build. The build is modelled on
[joycast.driver](https://github.com/joymacstudio/joycast.driver); the
scripts here are original to this project.
