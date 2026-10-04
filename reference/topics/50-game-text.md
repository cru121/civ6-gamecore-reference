---
title: Game text
order: 50
---
# Game text: read the in-game wording here

Many entries in this reference point at text that the game shows to players: the description of a policy, a governor promotion, a moment. The reference shows these as **text keys** (such as `LOC_EMERGENCY_TARGET_REWARD_DESCRIPTION_NUCLEAR_CULTURE_SCARE`), because the text itself is Firaxis' and is not published here.

You can make the text appear anyway, from **your own copy of the game**:

1. Build a small **strings file** from your game folder (below). It contains only the text of the keys this reference uses.
2. Load it with **Load strings file** in the sidebar. From then on every key shows your text, in the language you choose, and the search finds entries by their in-game wording.

**Everything stays on your computer.** The file is read by the page in your browser and kept in the browser's local storage. Nothing is uploaded, and the site cannot see it. **Clear** in the sidebar removes it. The file contains game text, so keep it for your own use and do not redistribute it.

## Build the file in the browser

Choose the Civilization VI folder (the one that contains `Base` and `DLC`), or only its `Text` folders. Works in Chrome, Edge and Firefox.

**Expect a wait.** After you confirm the folder, the browser first reads the list of all its files (about 56,000 for the whole game folder) before the page hears anything, which can take up to a minute with no sign of activity. Then a progress bar shows the reading of the game text (about 500 files, 110 MB), which takes a few more seconds to a minute. The Python script below skips the browser's file listing and is faster.

<div id="gt-builder"></div>

## Or build it with the Python script

If you prefer a command line, [`make_strings_file.py`](https://github.com/cru121/civ6-gamecore-reference/blob/main/reference/tools/make_strings_file.py) (standard library only) does the same:

```
python make_strings_file.py "C:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization VI" --lang en_US --lang zh_Hans_CN
```

It writes `civ6-strings.json`. One file is all you need: copy it to another computer and load it there.

## Languages

The game ships text for English (`en_US`), German, Spanish, French, Italian, Japanese, Korean, Polish, Brazilian Portuguese, Russian and Chinese (simplified `zh_Hans_CN` and traditional `zh_Hant_HK`). A strings file can hold several; pick the one to show in the sidebar. Search matches any loaded language, so you can search in Chinese for an effect described in this English reference.

## What you get

* On the **where the game uses it** page of each [modifier effect](effects/index.md): the description of whatever uses the effect, in the game's words.
* **Search by wording.** Type part of an in-game sentence into the search box; matching entries appear under *In your game text*.

## Limits

* The text is the **game's own** (base game and expansions). Text added by mods is not included.
* Game text contains markers such as `{1_Num}` (a number filled in by the game) and `[ICON_...]`. They are shown simplified: icons as ⟨Name⟩, formatting removed, placeholders left as they are.
* Only keys this reference uses are in the file, so a key that the reference does not mention will not be found.
* Your game version should roughly match the data of this reference; a key the game no longer has simply shows as the key.
* A private or incognito window may not keep the file between visits; load it again then.

## File format

A plain JSON file, so other tools can use it:

```json
{"format": "civ6-ref-strings", "version": 1, "created": "2026-10-04T12:00:00Z",
 "languages": {"en_US": {"LOC_KEY": "text"}, "zh_Hans_CN": {"LOC_KEY": "文本"}}}
```
