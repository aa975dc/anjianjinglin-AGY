@echo off
rem Start KeyPresser.exe elevated. Needed when the game (or Steam, which passes its
rem token to the game) runs as administrator: Windows drops synthetic input coming
rem from a process with lower privileges.
powershell -NoProfile -Command "Start-Process -Verb RunAs -FilePath '%~dp0KeyPresser.exe'"
