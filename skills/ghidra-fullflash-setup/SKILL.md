---
name: ghidra-fullflash-setup
description: Set up a Siemens phone fullflash in Ghidra with RAM dumps from pmb887x-emu, swilib types, CPU registers and symbols. Use when the user wants a Ghidra project for a Siemens firmware.
---

# Siemens fullflash in Ghidra

The result is a program in the open Ghidra project: the fullflash at `A0000000`, RAM dumps from the emulator, I/O registers, swilib types and symbols, and a finished auto-analysis.

Ask the user for the fullflash and the phone model, if the file name does not show the model.

## 1. Tools

| Tool | Check |
|---|---|
| Ghidra, patched build, with Ghidra MCP | Ghidra is running and Ghidra MCP answers `get_project` |
| ghidra_scripts | `list_scripts` with filter `SetupSiemensFullflash` finds the script |
| pmb887x-emu, a version with `memsave -i` | `pmb887x-emu --version` works |
| socat | `socat -V` works |

For every missing tool, ask the user whether to install it or where it is:

- Ghidra: https://github.com/siemens-mobile-hacks/ghidra-patched/releases, set up as in https://siepatch.dev/docs/reverse-engineering/how-start.
- Ghidra MCP: https://github.com/siemens-mobile-hacks/GhidraMCP.
- ghidra_scripts: `git clone https://github.com/siemens-mobile-hacks/ghidra_scripts`, then add the directory in Script Manager → Manage Script Directories.
- pmb887x-emu: "Installation" in https://github.com/siemens-mobile-hacks/pmb887x-emu.
- socat: the system package manager.

Install nothing without the user's consent.
Without Ghidra MCP, stop.

The user must open the target project in Ghidra; the script imports into it.

## 2. RAM dumps

Ghidra needs the RAM contents to analyze the firmware correctly.

Take the memory regions from https://siepatch.dev/docs/reverse-engineering/memory-dump/: fetch the page every time, the list changes.
Dump the common regions and the regions of the phone model.
If the model is not on the page, pick the section by the phone's hardware platform: CPU generation and RAM size.
The swilib platform does not tell the memory map.
If the platform is not certain, ask the user.

Start the emulator:

```sh
work=$(mktemp -d)
pmb887x-emu -f FULLFLASH.bin --headless --qemu-monitor "unix:$work/monitor.sock,server,nowait"
```

Wait about 60 s for the boot, then dump every region and stop the emulator:

```sh
socat - UNIX-CONNECT:"$work/monitor.sock" > /dev/null <<EOF
stop
pmemsave 0x00400000 0x00008000 "DUMP_DIR/MODEL_BROM_00400000_00008000.bin"
memsave -i 0xAC000000 0x01800000 "DUMP_DIR/MODEL_VMALLOC_AC000000_01800000.bin"
quit
EOF
```

- One line per region: `pmemsave` for physical memory, `memsave -i` for VMALLOC, which is read through the MMU with unmapped pages saved as zeros.
- `DUMP_DIR` is absolute; `MODEL` is the model and firmware version, for example `EL71v45`.
- The file name `MODEL_NAME_START_SIZE.bin` tells the script where to load the dump.
- socat exits with code 1 after `quit`; check that every file exists and has the region size.
- A missing VMALLOC file means `memsave -i` is not supported: update pmb887x-emu.

## 3. Setup

Call `run_script`:

- `name`: `SetupSiemensFullflash.java`
- `args`: `["fullflash=FULLFLASH.bin", "dumps=DUMP_DIR"]`
- `timeout_seconds`: `3600`

The script imports the fullflash into the project root and opens it in a CodeBrowser.
Then it maps the memory, loads the dumps, downloads swilib types, CPU registers and symbols from devtools.siepatch.dev, runs the auto-analysis and saves the program.

The analysis takes 10–30 minutes, and the MCP call may time out before it ends.
Poll `get_analysis_status` once a minute until the analysis stops, and report the progress to the user.

Add these arguments only when needed:

| Argument | Use |
|---|---|
| `target=EL71v45`, `target=none` | Swilib target when detection fails or is wrong |
| `platform=ELKA` | `ELKA`, `NSG`, `X75`, `SG`; only for models without a swilib target |
| `types=`, `cpu=`, `symbols=` | Local files instead of downloads |
| `analyze=false` | Skip the analysis |

## 4. Check

- `list_segments` shows `FULLFLASH`, a block per dump and `IO`.
- The `run_script` output, if it returned, shows the `Swilib target`, an `Imported` line per dump and `Parsed N symbols!` twice.

| Problem | Fix |
|---|---|
| `No swilib symbols match this firmware` | Unknown or patched firmware; pass `target=` only if the user knows it |
| `Platform is unknown` | Pass `platform=` |
| `Skip ...` for a dump | Fix the file name or remove the overlapping dump |
| The analysis never ends | Ghidra lacks the patch from the setup guide |
