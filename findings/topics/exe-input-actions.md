# Input actions (hotkeys)

Sources: `CivTech::Input::Manager::ReloadInputActions` (0x96c950, the SQL joins `InputActions` with `InputCategories` and `InputContexts`), `App::InputAction::Manager::SetupActions` (0x3b7f0, 18 action names in code) and `Parse` (0x3a4f0, icon alias groups for Generic, Nintendo, PlayStation, Stadia, Steam, Switch), the game's `InputConfiguration.xml` and the Expansion1/2 and BlackDeathScenario Config XML, and the Lua `Input` table. Reference: `docs_proto/docs/exe/input.md`, data `docs_proto/data/exe_input.json`.

- Data model (schema `Configuration/Data/Schema/InputConfiguration.sql`): `InputCategories(CategoryId, Name, Visible, SortIndex)`, `InputContexts(ContextId, Value)`, `InputActions(ActionId, Name, Description, CategoryId, ContextId, LayoutType default 'PC')`, `InputActionDefaultGestures(ActionId, Index, GestureType, GestureData)`, `InputKeyData(KeyId, KeyString, KeyIcon, KeyType)`.
- Installed game: 76 actions (59 PC / 17 Console), 7 categories, 16 contexts, 191 key records (136 KBMouse, 55 Controller). Expansion rows are `InsertOrIgnore`; the same rows appear in Expansion1 and Expansion2.
- The exe names 18 actions in code; 16 are table rows, `LeftClickCursor` and `MoveCursor` are not (inferred: code-only cursor actions).
- Scripts call `Input.GetActionId("Name")` 68 times; `Accept`, `AcceptAlt`, `StartGame`, `StartGameAlt`, `TutorialContinue`, `TutorialContinueAlt`, `TutorialShowMore` and `AutomationTogglePause` have no row (the popup and tutorial rows are commented out in the XML).
