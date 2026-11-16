# Discord Panic Button

<img src="assets/icon.png" width="96" align="right">

A tiny Windows background app that **minimizes Discord instantly** with a hotkey or key chord.
Press the same combo again to bring Discord back.

- Runs silently in the background (no window, no tray clutter), starts with Windows
- Works with any key combo: classic hotkeys (`ctrl+alt+d`) **or** chords of normal keys (`num1+num3+num5`)
- Numpad keys work with NumLock on or off
- Supports Discord, Discord PTB and Discord Canary
- Per-user install, no admin rights needed

## Install

Download `DiscordPanicSetup-x.y.z.exe` from [Releases](../../releases) and run it.
The wizard lets you pick your hotkey and whether it should also restore Discord.

## Usage

Default combo: **hold Numpad 1 + Numpad 3, then press Numpad 5**.

Start menu → *Discord Panic Button* folder:

- **Edit hotkey settings**: opens `config.json`
- **Restart (apply settings)**: reloads after you edit the config
- **Stop Discord Panic Button**

## Settings

`%APPDATA%\DiscordPanic\config.json`

```json
{
  "hotkey": "num1+num3+num5",
  "toggle_restore": true,
  "swallow_trigger_key": true,
  "process_names": ["discord.exe", "discordptb.exe", "discordcanary.exe"]
}
```

- `hotkey`: keys joined with `+`. Modifiers: `ctrl`, `alt`, `shift`, `win`. Keys: `a`-`z`, `0`-`9`, `f1`-`f24`,
  `num0`-`num9`, `numplus`, `numminus`, `nummul`, `numdiv`, `space`, `esc`, `pause`, `insert`, `delete`, `home`, `end`,
  `pageup`, `pagedown`, `` ` ``, `-`, `=`, `[`, `]`, `;`, `'`, `,`, `.`, `/`, `\`
- `toggle_restore`: if `true`, pressing the combo again restores Discord
- `swallow_trigger_key`: in chord mode, stops the last key of the chord from being typed
- `process_names`: which executables count as Discord

Command line: `DiscordPanic.exe [--stop | --restart | --config]`

## Build from source

Requires Python 3.9+ with `pyinstaller`, and [Inno Setup 6](https://jrsoftware.org/isinfo.php).

```bat
pip install pyinstaller
set VERSION=1.0.0
build.cmd
```

Output: `dist\DiscordPanic\` (app folder) and `dist\DiscordPanicSetup-1.0.0.exe`.

## Notes

- Chords of 3+ keys need a keyboard that can register them simultaneously. Most do on the numpad; some cheap
  keyboards ghost.
- Some antivirus tools flag PyInstaller executables / global keyboard hooks as suspicious. The source is all in
  `src/discord_panic.py` (pure Python + Win32 via ctypes, no network access).

## License

MIT
