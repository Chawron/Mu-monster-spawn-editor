# Monster Spawn Editor for MU Online

A visual editor for managing monster spawns in MU Online game files. Special version for Season 6 by Louis.

## Features
- Visual map editor for monster spawns
- Support for NPCs, monsters, traps and all MonsterSetBase sections (0-4), colour-coded on the map
- Interactive coordinate system
- Search and filter functionality (maps, monsters and spawns)
- Drag spawns to move them, arrow keys to nudge, right-click menu for quick actions
- Undo/Redo functionality (Ctrl+Z, Ctrl+Y), kept separately for every map
- Memory system to retain changes when switching maps
- Save All and automatic `.bak` backup of the original file
- Coordinate display with improved visibility
- Zoom controls for better navigation (Ctrl+Wheel, Ctrl+/-, Ctrl+0, Ctrl+1)
- Automatic directory creation
- Warning when exiting with unsaved changes

## Installation
1. Download the latest release from [Releases](https://github.com/OneAboveAlly/editmonstersetbase/releases)
2. Extract the ZIP file
3. Run `MonsterSpawnEditor.exe`

## Requirements
- Windows 10 or later
- No additional software required

## Usage
1. Select a map from the Map Selection panel (type in Search to filter the list)
2. Choose a monster from the New Mob Selection list
3. Click on the map to add a spawn, or drag over an empty area to add an area spawn
4. Use the quantity, range, direction and "Add as" fields to control new spawns
5. Click a spawn to edit it in Spawn Properties, drag it to move it, right-click for more options
6. Save your changes using File > Save (Ctrl+S) or File > Save All Modified Maps (Ctrl+Shift+S)

### Mouse and keyboard
| Action | How |
| --- | --- |
| Add spawn / area | Click / drag on an empty spot |
| Select spawn | Click it (click a stacked `xN` spot again to select the next spawn there) |
| Move spawn | Drag it, or use the arrow keys after clicking the map |
| Duplicate / delete | Ctrl+D / Delete, or right-click the spawn |
| Zoom | Ctrl+Wheel or Ctrl +/-; Ctrl+0 fits the map, Ctrl+1 shows 100% |
| Scroll / pan | Wheel, Shift+Wheel, middle mouse drag |
| Clear selection | Esc |
| Keyboard shortcut list | F1 |

### Spawn search
The search above "Mobs on Selected Map" accepts a monster name, an ID, `npc` / `trap` / `monster`, or coordinates such as `130,143`. Tick "Show only search results on map" to hide everything else on the map.

## Changelog

### Version 1.03
- **MonsterSetBase sections**: Sections 2 (single spots), 3 and 4 (event spawns) are now read and saved correctly.
  Before, maps such as Dungeon or Raklion had these spawns moved into section 1 on save.
  Spawns are coloured by section, a legend is shown under the map, and new spawns can be added to any section ("Add as").
- **Easier editing**:
  - Drag a spawn to move it (its area moves with it), or nudge it with the arrow keys.
  - Right-click menu: duplicate, delete, move the selected spawn here, use this monster, copy the spawn line or coordinates.
  - Duplicate button and Ctrl+D; Esc clears the selection; F1 shows all shortcuts.
  - Clicking a stacked spot (`xN`) again cycles through the spawns there.
  - Direction and section of a selected spawn can be edited; Enter applies the change.
  - Clicking a spawn no longer replaces the monster, quantity and direction used for new spawns.
  - Messages for adding, updating and saving are shown in the status bar instead of popups.
- **Navigation**: Ctrl+Wheel zooms at the cursor, the wheel scrolls, the middle mouse button pans.
  Zoom is kept when the window is resized; Ctrl+0 fits the map again and Ctrl+1 shows 100%.
- **Maps**: Map search box, `*` marks maps with unsaved changes, File > Save All and File > Revert Map to Saved.
  Undo history is kept per map. The first save of a file in a session keeps the original as `<file>.bak`.
- **Spawn list**: Search by coordinates (`130,143`), option to show only search results on the map, and a summary of the map's entries and monster count.
- **Bug fixes**:
  - Fixed crashes and wrong edits after switching maps while a spawn was selected.
  - Selecting identical spawns in the list now selects the right one.
  - Spawns are drawn in the right place when the map is zoomed and scrolled; dragging an area uses the right end corner.
  - File > Load Map now switches the current map (before, saving could write it into the previously selected file).
  - Removing every spawn of a map is no longer lost when switching maps.
  - Invalid values in Spawn Properties no longer create empty undo steps or mark the map as modified.
  - Delete in a text field no longer deletes the selected spawn.
  - Missing map images show a hint on the map instead of a blank canvas.
  - The program finds its data folders next to itself, from whatever folder it is started.
  - Works on Linux too (window maximising and icon no longer crash there).
  - Files are written to a temporary file first, so a failed save cannot leave a half-written map.

### Version 1.02
- **Enhanced Map & Image Handling**:
  - improved map file parser to support irregular filenames (e.g., Stadium, Icarus, Land of Trials).
  - Added support for "Swamp of Calmness" rendering using 'Swamp_of_Peace.png'.
  - Added Graceful handling of missing map images (no longer crashes, shows warning).
- **Advanced Spawn Management**:
  - **Stacked Mobs**: Visual indicator `xN` (e.g., `x2`) appears above coordinates with multiple monsters.
  - **Smart Selection**: Clicking a spawn now highlights ONLY that specific instance (raised to top) instead of all mobs of that type.
  - **Quick Edit**: Clicking a point on the map immediately loads its properties (Quantity, Range, etc.) into the editor panel.
  - **Improved List**: "Mobs on Selected Map" list is now sorted by coordinate `(X, Y)` for better grouping and readability.
- **Bug Fixes**:
  - Fixed startup crashes related to missing variables (`status_var`).
  - Fixed `AttributeError` crash when resizing the window.
  - Fixed issue where tooltips showed generic group data instead of specific instance data.

### Version 1.01
- Added Undo/Redo functionality with keyboard shortcuts (Ctrl+Z, Ctrl+Y)
- Implemented memory system for map changes - your edits are now preserved when switching between maps
- Added "Modified*" indicator for maps with unsaved changes
- Added warning dialog when exiting with unsaved changes
- Added ability to edit existing spawns (coordinates, direction, quantity)
- Fixed coordinate mapping to match exactly the coordinates displayed in tooltips
- Added custom program icon visible in both application window and taskbar
- Implemented zoom functionality (Ctrl+/- and Ctrl+0) for better navigation on large maps
- Added automatic creation of required directories if missing (MonsterSetBase, Monster, Images)
- Improved handling of different screen resolutions - better UI scaling
- Added horizontal scrollbars for monster and spawn lists
- Enhanced error handling - protection against division by zero in coordinate calculations
- Added status bar showing current coordinates and scale
- Improved coordinate tooltip visibility with better contrast and positioning

### Version Alpha 0.1
- Basic monster spawn editor functionality
- Ability to add new monster and NPC spawns
- Map and spawn display
- Basic monster stats editing
- Saving changes to MonsterSetBase files

## Development
If you want to build from source:
```bash
pip install -r requirements.txt
python src/monster_spawn_editor.py
```

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits
- Created by Shizoo
- Original game files from MU Online