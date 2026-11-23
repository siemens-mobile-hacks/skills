---
name: ghidra-fullflash-setup
description: Set up a Siemens phone fullflash in Ghidra with SetupSiemensFullflash.java, optionally with RAM dumps from a phone or pmb887x-emu. Use when the user wants a Ghidra project for a Siemens firmware.
---

# Siemens fullflash in Ghidra

Ask the user for the fullflash and the Ghidra project location.

## Tools

Find the tools first:

| Tool | Look for |
|---|---|
| Ghidra | `$GHIDRA_INSTALL_DIR/support/analyzeHeadless`, or `analyzeHeadless` on `PATH` |
| ghidra_scripts | a directory with `SetupSiemensFullflash.java` |
| sie-tool, only for phone dumps | `sie-tool` on `PATH` |
| pmb887x-emu, only for emulator dumps | `pmb887x-emu` on `PATH` |

If a tool is not found, ask the user where it is, or offer to install it:

- Ghidra: the patched build from https://github.com/siemens-mobile-hacks/ghidra-patched/releases, set up as in https://siepatch.dev/docs/reverse-engineering/how-start.
- ghidra_scripts: `git clone https://github.com/siemens-mobile-hacks/ghidra_scripts`.
- sie-tool: `npm install -g @sie-js/sie-tool@latest`, see https://github.com/siemens-mobile-hacks/sie-tool.
- pmb887x-emu: a release package or a source build, see "Installation" in https://github.com/siemens-mobile-hacks/pmb887x-emu.

Install nothing without the user's consent.

## RAM dumps (optional)

Use dumps of the same firmware as the fullflash, named `NAME_START_SIZE.bin` or `NAME_START_END.bin` in hex, for example `EL71v45_RAM_A8000000_01000000.bin`.
sie-tool names (`EL71v45-RAM-A8000000_01000000.bin`) work as they are.
Take the dumps from the phone or from the emulator.

Phone, with sie-tool and the phone connected by cable:

```sh
sie-tool list-ports
sie-tool -p PORT memory-read-all -e FLASH -o DUMP_DIR
```

`-e FLASH` skips the flash: the fullflash already has it.
Other dumpers are listed in https://siepatch.dev/docs/reverse-engineering/memory-dump.

Emulator ([pmb887x-emu](https://github.com/siemens-mobile-hacks/pmb887x-emu)):

```sh
work=$(mktemp -d)
pmb887x-emu -f FULLFLASH.bin --headless --qemu-monitor "unix:$work/monitor.sock,server,nowait"
```

Wait about 60 s for the boot, then dump the memory and stop the emulator:

```sh
"${CLAUDE_PLUGIN_ROOT}/skills/ghidra-fullflash-setup/scripts/dump_memory.py" --monitor "$work/monitor.sock" --out DUMP_DIR --prefix EL71v45 \
	TCM:00000000:00004000 SRAM:00080000:00018000 BROM:00400000:00008000 \
	RAM:A8000000:01000000 VMALLOC:AC000000:01800000:virt
```

- Add `:virt` to VMALLOC only: it is read through the MMU.

## Setup

Close the project in the Ghidra GUI, then run:

```sh
"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" PROJECT_DIR PROJECT_NAME -import FULLFLASH.bin \
	-loader BinaryLoader -loader-baseAddr 0xA0000000 -loader-blockName FULLFLASH \
	-processor ARM:LE:32:v5t -noanalysis \
	-scriptPath GHIDRA_SCRIPTS_DIR -postScript SetupSiemensFullflash.java dumps=DUMP_DIR
```

The analysis takes 10–30 minutes.

Optional arguments:

| Argument | Use |
|---|---|
| `dumps=PATHS` | Dump files or directories, separated by `:` (`;` on Windows) |
| `target=EL71v45`, `target=none` | Swilib target when detection fails or is wrong |
| `platform=ELKA` | `ELKA`, `NSG`, `X75`, `SG`; only for models without a swilib target |
| `types=`, `cpu=`, `symbols=` | Local files instead of downloads |
| `analyze=false` | Skip the analysis |

In the GUI the user runs the same script from the Script Manager; it asks for everything in dialogs.

## Check

The log must show the chosen `Swilib target`, a `Partition` line per FFS/EEPROM partition, an `Imported` line per dump, and `Parsed N symbols!` twice.

| Message | Fix |
|---|---|
| `No swilib symbols match this firmware` | Unknown or heavily patched version; pass `target=` only if the user knows it |
| `Platform is unknown` | Pass `platform=` |
| `Skip ...` for a dump | Fix the file name or remove the overlapping dump |
| Analysis never ends | Ghidra lacks the patch from the guide |
| Project lock error | Close the project in the Ghidra GUI |
