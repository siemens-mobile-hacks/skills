# Siemens Mobile Hacks skills

Agent skills for Siemens phone hacking and reverse engineering.
Each directory holds one skill: a `SKILL.md` with instructions and the helper scripts it uses.

| Skill | Purpose |
|---|---|
| [ghidra-fullflash-setup](ghidra-fullflash-setup/SKILL.md) | Set up a fullflash in Ghidra: memory map, partitions, RAM dumps, swilib types and symbols |

## Install

Copy or symlink a skill directory into the skills directory of your agent, for example for Claude Code:

```sh
ln -s "$PWD/ghidra-fullflash-setup" ~/.claude/skills/ghidra-fullflash-setup
```

Use `.claude/skills/` inside a project to enable a skill only there.
