@echo off
rem Starts the Frida daemon for Steam build 15038592 (GameCore_XP2_FinalRelease.dll).
rem Civ VI must be running AND a game must be loaded (never attach while the game is starting up).
rem Close the game to end the daemon; never kill it while the game should live (detaching crashes the game).
cd /d "%~dp0"
if not exist symbols.json python ..\..\..\tsv_to_symbols.py ..\..\..\..\data\old_to_new_offsets.tsv symbols.json
cd ..\..
rem 0x42780 = Game::Autoplay::Manager::Update (called ~60x/s on the game thread, also while idle), 0x5c2d0 = Player::Processor::BeginTurn
python live_daemon.py --symbols builds\15038592\symbols.json --tick 0x42780 --turn 0x5c2d0
