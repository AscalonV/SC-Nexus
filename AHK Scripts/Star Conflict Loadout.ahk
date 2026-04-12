;-------------------------
;-------------------------
;---------v2.0.1----------
;-----Ellydium update-----
;-------------------------
;-------------------------
#NoEnv  ; Recommended for performance and compatibility with future AutoHotkey releases.
SetWorkingDir %A_ScriptDir%  ; Ensures a consistent starting directory.
#SingleInstance Force
#InstallKeybdHook
;#NoTrayIcon
#MaxHotkeysPerInterval 1000
CoordMode, Mouse, Screen
SendMode Input
SetMouseDelay, 0
DetectHiddenWindows, On
SetKeyDelay , 50, 100,    ; 50ms is the default delay between presses, 30ms is the press length
Hotkey, LButton, Off
Hotkey, RButton, Off
Hotkey, WheelUp, Off
Hotkey, WheelDown, Off
MouseWheelCounter = 0


;-------------------------------------------------- Declare Vars --------------------------------------------------


; --- Globals for Setup GUI coordinate buttons ---
global BranchTitle_1, BranchTitle_2, BranchTitle_3, BranchTitle_4, BranchTitle_5
global BranchTitle_6, BranchTitle_7, BranchTitle_8, BranchTitle_9, BranchTitle_10
global BranchTitle_11, BranchTitle_12, BranchTitle_13, BranchTitle_14, BranchTitle_15

global Btn_CPU_1, Btn_CPU_2, Btn_CPU_3, Btn_CPU_4, Btn_CPU_5, Btn_CPU_6
global Btn_CPU_7, Btn_CPU_8, Btn_CPU_9, Btn_CPU_10, Btn_CPU_11, Btn_CPU_12

global Btn_Hull_1, Btn_Hull_2, Btn_Hull_3, Btn_Hull_4, Btn_Hull_5, Btn_Hull_6
global Btn_Hull_7, Btn_Hull_8, Btn_Hull_9, Btn_Hull_10, Btn_Hull_11, Btn_Hull_12

global Btn_Shield_1, Btn_Shield_2, Btn_Shield_3, Btn_Shield_4, Btn_Shield_5, Btn_Shield_6
global Btn_Shield_7, Btn_Shield_8, Btn_Shield_9, Btn_Shield_10, Btn_Shield_11, Btn_Shield_12

global Btn_Capacitor_1, Btn_Capacitor_2, Btn_Capacitor_3, Btn_Capacitor_4, Btn_Capacitor_5, Btn_Capacitor_6
global Btn_Capacitor_7, Btn_Capacitor_8, Btn_Capacitor_9, Btn_Capacitor_10, Btn_Capacitor_11, Btn_Capacitor_12

global Btn_Engine_1, Btn_Engine_2, Btn_Engine_3, Btn_Engine_4, Btn_Engine_5, Btn_Engine_6
global Btn_Engine_7, Btn_Engine_8, Btn_Engine_9, Btn_Engine_10, Btn_Engine_11, Btn_Engine_12

global Btn_Utility_1, Btn_Utility_2, Btn_Utility_3, Btn_Utility_4, Btn_Utility_5, Btn_Utility_6
global Btn_Utility_7, Btn_Utility_8, Btn_Utility_9, Btn_Utility_10, Btn_Utility_11, Btn_Utility_12

global Btn_Offence_1, Btn_Offence_2, Btn_Offence_3, Btn_Offence_4, Btn_Offence_5, Btn_Offence_6
global Btn_Defence_1, Btn_Defence_2, Btn_Defence_3, Btn_Defence_4, Btn_Defence_5, Btn_Defence_6

global Btn_SpecMod_1, Btn_SpecMod_2, Btn_SpecMod_3, Btn_SpecMod_4, Btn_SpecMod_5

; -- Nodes (up to 12 nodes per branch category)
global Node_CPU_1, Node_CPU_2, Node_CPU_3, Node_CPU_4, Node_CPU_5, Node_CPU_6
global Node_CPU_7, Node_CPU_8, Node_CPU_9, Node_CPU_10, Node_CPU_11, Node_CPU_12

global Node_Hull_1, Node_Hull_2, Node_Hull_3, Node_Hull_4, Node_Hull_5, Node_Hull_6
global Node_Hull_7, Node_Hull_8, Node_Hull_9, Node_Hull_10, Node_Hull_11, Node_Hull_12

global Node_Shield_1, Node_Shield_2, Node_Shield_3, Node_Shield_4, Node_Shield_5, Node_Shield_6
global Node_Shield_7, Node_Shield_8, Node_Shield_9, Node_Shield_10, Node_Shield_11, Node_Shield_12

global Node_Capacitor_1, Node_Capacitor_2, Node_Capacitor_3, Node_Capacitor_4, Node_Capacitor_5, Node_Capacitor_6
global Node_Capacitor_7, Node_Capacitor_8, Node_Capacitor_9, Node_Capacitor_10, Node_Capacitor_11, Node_Capacitor_12

global Node_Engine_1, Node_Engine_2, Node_Engine_3, Node_Engine_4, Node_Engine_5, Node_Engine_6
global Node_Engine_7, Node_Engine_8, Node_Engine_9, Node_Engine_10, Node_Engine_11, Node_Engine_12

global Node_Utility_1, Node_Utility_2, Node_Utility_3, Node_Utility_4, Node_Utility_5, Node_Utility_6
global Node_Utility_7, Node_Utility_8, Node_Utility_9, Node_Utility_10, Node_Utility_11, Node_Utility_12

global Node_Offence_1, Node_Offence_2, Node_Offence_3, Node_Offence_4, Node_Offence_5, Node_Offence_6

global Node_Defence_1, Node_Defence_2, Node_Defence_3, Node_Defence_4, Node_Defence_5, Node_Defence_6

global Node_SpecMod_1, Node_SpecMod_2, Node_SpecMod_3, Node_SpecMod_4, Node_SpecMod_5

; -- NodeEffect (up to 12 nodes per branch category)
global NodeEffect_CPU_1, NodeEffect_CPU_2, NodeEffect_CPU_3, NodeEffect_CPU_4, NodeEffect_CPU_5, NodeEffect_CPU_6
global NodeEffect_CPU_7, NodeEffect_CPU_8, NodeEffect_CPU_9, NodeEffect_CPU_10, NodeEffect_CPU_11, NodeEffect_CPU_12

global NodeEffect_Hull_1, NodeEffect_Hull_2, NodeEffect_Hull_3, NodeEffect_Hull_4, NodeEffect_Hull_5, NodeEffect_Hull_6
global NodeEffect_Hull_7, NodeEffect_Hull_8, NodeEffect_Hull_9, NodeEffect_Hull_10, NodeEffect_Hull_11, NodeEffect_Hull_12

global NodeEffect_Shield_1, NodeEffect_Shield_2, NodeEffect_Shield_3, NodeEffect_Shield_4, NodeEffect_Shield_5, NodeEffect_Shield_6
global NodeEffect_Shield_7, NodeEffect_Shield_8, NodeEffect_Shield_9, NodeEffect_Shield_10, NodeEffect_Shield_11, NodeEffect_Shield_12

global NodeEffect_Capacitor_1, NodeEffect_Capacitor_2, NodeEffect_Capacitor_3, NodeEffect_Capacitor_4, NodeEffect_Capacitor_5, NodeEffect_Capacitor_6
global NodeEffect_Capacitor_7, NodeEffect_Capacitor_8, NodeEffect_Capacitor_9, NodeEffect_Capacitor_10, NodeEffect_Capacitor_11, NodeEffect_Capacitor_12

global NodeEffect_Engine_1, NodeEffect_Engine_2, NodeEffect_Engine_3, NodeEffect_Engine_4, NodeEffect_Engine_5, NodeEffect_Engine_6
global NodeEffect_Engine_7, NodeEffect_Engine_8, NodeEffect_Engine_9, NodeEffect_Engine_10, NodeEffect_Engine_11, NodeEffect_Engine_12

global NodeEffect_Utility_1, NodeEffect_Utility_2, NodeEffect_Utility_3, NodeEffect_Utility_4, NodeEffect_Utility_5, NodeEffect_Utility_6
global NodeEffect_Utility_7, NodeEffect_Utility_8, NodeEffect_Utility_9, NodeEffect_Utility_10, NodeEffect_Utility_11, NodeEffect_Utility_12

global NodeEffect_Offence_1, NodeEffect_Offence_2, NodeEffect_Offence_3, NodeEffect_Offence_4, NodeEffect_Offence_5, NodeEffect_Offence_6
global NodeEffect_Offence_7, NodeEffect_Offence_8, NodeEffect_Offence_9, NodeEffect_Offence_10, NodeEffect_Offence_11, NodeEffect_Offence_12

global NodeEffect_Defence_1, NodeEffect_Defence_2, NodeEffect_Defence_3, NodeEffect_Defence_4, NodeEffect_Defence_5, NodeEffect_Defence_6
global NodeEffect_Defence_7, NodeEffect_Defence_8, NodeEffect_Defence_9, NodeEffect_Defence_10, NodeEffect_Defence_11, NodeEffect_Defence_12

global NodeEffect_SpecMod_1, NodeEffect_SpecMod_2, NodeEffect_SpecMod_3, NodeEffect_SpecMod_4, NodeEffect_SpecMod_5, NodeEffect_SpecMod_6
global NodeEffect_SpecMod_7, NodeEffect_SpecMod_8, NodeEffect_SpecMod_9, NodeEffect_SpecMod_10, NodeEffect_SpecMod_11, NodeEffect_SpecMod_12

; Global declarations to avoid "must be global or static" error
global Scan_CPU_1, Scan_CPU_2, Scan_CPU_3, Scan_CPU_4, Scan_CPU_5, Scan_CPU_6
global Scan_CPU_7, Scan_CPU_8, Scan_CPU_9, Scan_CPU_10, Scan_CPU_11, Scan_CPU_12

global Scan_Capacitor_1, Scan_Capacitor_2, Scan_Capacitor_3, Scan_Capacitor_4, Scan_Capacitor_5, Scan_Capacitor_6
global Scan_Capacitor_7, Scan_Capacitor_8, Scan_Capacitor_9, Scan_Capacitor_10, Scan_Capacitor_11, Scan_Capacitor_12

global Scan_Engine_1, Scan_Engine_2, Scan_Engine_3, Scan_Engine_4, Scan_Engine_5, Scan_Engine_6
global Scan_Engine_7, Scan_Engine_8, Scan_Engine_9, Scan_Engine_10, Scan_Engine_11, Scan_Engine_12

global Scan_Hull_1, Scan_Hull_2, Scan_Hull_3, Scan_Hull_4, Scan_Hull_5, Scan_Hull_6
global Scan_Hull_7, Scan_Hull_8, Scan_Hull_9, Scan_Hull_10, Scan_Hull_11, Scan_Hull_12

global Scan_Shield_1, Scan_Shield_2, Scan_Shield_3, Scan_Shield_4, Scan_Shield_5, Scan_Shield_6
global Scan_Shield_7, Scan_Shield_8, Scan_Shield_9, Scan_Shield_10, Scan_Shield_11, Scan_Shield_12

global Scan_Offence_1, Scan_Offence_2, Scan_Offence_3, Scan_Offence_4, Scan_Offence_5, Scan_Offence_6
global Scan_Offence_7, Scan_Offence_8, Scan_Offence_9, Scan_Offence_10, Scan_Offence_11, Scan_Offence_12

global Scan_Defence_1, Scan_Defence_2, Scan_Defence_3, Scan_Defence_4, Scan_Defence_5, Scan_Defence_6
global Scan_Defence_7, Scan_Defence_8, Scan_Defence_9, Scan_Defence_10, Scan_Defence_11, Scan_Defence_12

global Scan_SpecMod_1, Scan_SpecMod_2, Scan_SpecMod_3, Scan_SpecMod_4, Scan_SpecMod_5, Scan_SpecMod_6
global Scan_SpecMod_7, Scan_SpecMod_8, Scan_SpecMod_9, Scan_SpecMod_10, Scan_SpecMod_11, Scan_SpecMod_12

global Scan_Utility_1, Scan_Utility_2, Scan_Utility_3, Scan_Utility_4, Scan_Utility_5, Scan_Utility_6
global Scan_Utility_7, Scan_Utility_8, Scan_Utility_9, Scan_Utility_10, Scan_Utility_11, Scan_Utility_12





Gui, 13: +AlwaysOnTop -caption +border
Gui, 13: Color, 000000
Gui, 13: Font, cWhite s14, Arial
Gui, 13: Add, Text, x0 y10 w300 h30 center, ---------- INFO ----------
Gui, 13: Font, cWhite s22, Arial
Gui, 13: Add, Text, vRename_Ship_Text1 x0 y60 w300 center, Loading
Gui, 13: Add, Text, x0 y0 w300 h170 0x12
Gui, 13: Show, x287.5 y273.75 h170 w300, Info

;--------------------------------------------------Settings Preparation--------------------------------------------------


IniRead, Preference_Check, %A_ScriptDir%\Settings\Preferences.ini, Last|, Checked1
If (Preference_Check = "Error")
{
FileDelete, %A_ScriptDir%\Settings\Preferences.ini
Checked_N := 1
Loop, 4
{
IniWrite, 1, %A_ScriptDir%\Settings\Preferences.ini, Last|, Checked%Checked_N%
Checked_N++
}
Checked_N := 1
Loop, 4
{
IniWrite, None, %A_ScriptDir%\Settings\Preferences.ini, Last|, Ship%Checked_N%
Checked_N++
}
Checked_N := 1
Loop, 4
{
IniWrite, None, %A_ScriptDir%\Settings\Preferences.ini, Last|, Build%Checked_N%
Checked_N++
}
}

IniRead, ShipList_Check, %A_ScriptDir%\Settings\ShipList.ini, None|, Faction
If (ShipList_Check = "Error")
{
FileCreateDir, Settings
FileDelete, %A_ScriptDir%\Settings\ShipList.ini
IniWrite, None, %A_ScriptDir%\Settings\ShipList.ini, None|, Faction
IniWrite, None, %A_ScriptDir%\Settings\ShipList.ini, None|, x
IniWrite, None, %A_ScriptDir%\Settings\ShipList.ini, None|, y
}

IniRead, Builds_Check, %A_ScriptDir%\Builds\None.ini, None|, None
If (Builds_Check = "Error")
{
FileCreateDir, Builds\Ellydium
IniWrite, None, %A_ScriptDir%\Builds\None.ini, None|, None
}


Gui_Start:
SetCapsLockState, Off
Gui, 13: show
IniRead, Coordinates_Check_Empire, %A_ScriptDir%\Settings\Coordinates.ini, Empire, x
IniRead, Coordinates_Check_Federation, %A_ScriptDir%\Settings\Coordinates.ini, Federation, x
IniRead, Coordinates_Check_Jericho, %A_ScriptDir%\Settings\Coordinates.ini, Jericho, x
IniRead, Coordinates_Check_Ellydium, %A_ScriptDir%\Settings\Coordinates.ini, Ellydium, x
IniRead, Coordinates_Check_Unique, %A_ScriptDir%\Settings\Coordinates.ini, Unique, x
IniRead, Coordinates_Check_Slot1, %A_ScriptDir%\Settings\Coordinates.ini, Slot1, x
IniRead, Coordinates_Check_Slot2, %A_ScriptDir%\Settings\Coordinates.ini, Slot2, x
IniRead, Coordinates_Check_Slot3, %A_ScriptDir%\Settings\Coordinates.ini, Slot3, x
IniRead, Coordinates_Check_Slot4, %A_ScriptDir%\Settings\Coordinates.ini, Slot4, x
IniRead, Coordinates_Check_Preset1, %A_ScriptDir%\Settings\Coordinates.ini, Preset1, x
IniRead, Coordinates_Check_Preset2, %A_ScriptDir%\Settings\Coordinates.ini, Preset2, x
IniRead, Coordinates_Check_Preset3, %A_ScriptDir%\Settings\Coordinates.ini, Preset3, x
IniRead, Coordinates_Check_Preset4, %A_ScriptDir%\Settings\Coordinates.ini, Preset4, x
IniRead, Coordinates_Check_PresetL, %A_ScriptDir%\Settings\Coordinates.ini, Load Preset, x
IniRead, Coordinates_Check_Yes, %A_ScriptDir%\Settings\Coordinates.ini, Yes, x
IniRead, Coordinates_Check_Scroll, %A_ScriptDir%\Settings\Coordinates.ini, Scroll, x
IniRead, Coordinates_Check_Back, %A_ScriptDir%\Settings\Coordinates.ini, Back, x
IniRead, Coordinates_Check_Crew_A, %A_ScriptDir%\Settings\Coordinates.ini, Crew_A, x
IniRead, Coordinates_Check_Crew_B, %A_ScriptDir%\Settings\Coordinates.ini, Crew_B, x
IniRead, Coordinates_Check_Crew_C, %A_ScriptDir%\Settings\Coordinates.ini, Crew_C, x
IniRead, Coordinates_Check_Crew_D, %A_ScriptDir%\Settings\Coordinates.ini, Crew_D, x
IniRead, Coordinates_Check_Crew1_1, %A_ScriptDir%\Settings\Coordinates.ini, Crew1-1, x
IniRead, Coordinates_Check_Crew15_3, %A_ScriptDir%\Settings\Coordinates.ini, Crew15-3, x
IniRead, Coordinates_Check_Implant, %A_ScriptDir%\Settings\Coordinates.ini, Implant, x
IniRead, Coordinates_Check_Implant_Color, %A_ScriptDir%\Settings\Coordinates.ini, Implant, implant_color


Multiple := 0
IniRead,FullShipList,%A_ScriptDir%\Settings\ShipList.ini
StringReplace, FullShipList,FullShipList, `n,, All

IniRead,Preferences,%A_ScriptDir%\Settings\Preferences.ini
StringTrimLeft, Preferences, Preferences, 5
IniRead,FullShipList,%A_ScriptDir%\Settings\ShipList.ini
StringReplace, FullShipList,FullShipList, `n,, All


;--------------------------------------------------GUI--------------------------------------------------
Gui, 1: +AlwaysOnTop +Toolwindow
Gui, 1: Color, 000000
Gui, 1: Font, cWhite s12, Arial


Gui, 1: Add, Text, x0 y10 w600 center, -------------------- Select Ships --------------------


Gui, 1: Add, Text, x150 y40 w150 h30, Ship
Gui, 1: Add, Text, x270 y40 w150 h30, Loadout




Gui, 1: Add, checkbox, vShip1_checked x20 y65 h30 checked, Slot 1:
Gui, 1: Add, DDL, vShip1 gShipSelected_routine1 x105 y67 w130 sort, %FullShipList%
Gui, 1: Add, DDL, vBuilds_Ship1_selected gBuildSelected_routine1 x240 y67 w130 Choose1, %Builds_Ship1%
Gui, 1: Add, Button, gButton_Only_Ship1 x380 y61 w63.33 h35, Only`nShip
Gui, 1: Add, Button, gButton_Only_Crew1 x448.33 y61 w63.33 h35, Only`nCrew
Gui, 1: Add, Button, gButton_Ship_Crew1 x516.66 y61 w63.33 h35, Ship+`nCrew

Gui, 1: Add, checkbox, vShip2_checked x20 y115 h30 checked, Slot 2:
Gui, 1: Add, DDL, vShip2 gShipSelected_routine2 x105 y117 w130 sort, %FullShipList%
Gui, 1: Add, DDL, vBuilds_Ship2_selected gBuildSelected_routine2 x240 y117 w130 Choose1, %Builds_Ship2%
Gui, 1: Add, Button, gButton_Only_Ship2 x380 y111 w63.33 h35, Only`nShip
Gui, 1: Add, Button, gButton_Only_Crew2 x448.33 y111 w63.33 h35, Only`nCrew
Gui, 1: Add, Button, gButton_Ship_Crew2 x516.66 y111 w63.33 h35, Ship+`nCrew

Gui, 1: Add, checkbox, vShip3_checked x20 y165 h30 checked, Slot 3:
Gui, 1: Add, DDL, vShip3 gShipSelected_routine3 x105 y167 w130 sort, %FullShipList%
Gui, 1: Add, DDL, vBuilds_Ship3_selected gBuildSelected_routine3 x240 y167 w130 Choose1, %Builds_Ship3%
Gui, 1: Add, Button, gButton_Only_Ship3 x380 y161 w63.33 h35, Only`nShip
Gui, 1: Add, Button, gButton_Only_Crew3 x448.33 y161 w63.33 h35, Only`nCrew
Gui, 1: Add, Button, gButton_Ship_Crew3 x516.66 y161 w63.33 h35, Ship+`nCrew

Gui, 1: Add, checkbox, vShip4_checked x20 y215 h30 checked, Slot 4:
Gui, 1: Add, DDL, vShip4 gShipSelected_routine4 x105 y217 w130 sort, %FullShipList%
Gui, 1: Add, DDL, vBuilds_Ship4_selected gBuildSelected_routine4 x240 y217 w130 Choose1, %Builds_Ship4%
Gui, 1: Add, Button, gButton_Only_Ship4 x380 y211 w63.33 h35, Only`nShip
Gui, 1: Add, Button, gButton_Only_Crew4 x448.33 y211 w63.33 h35, Only`nCrew
Gui, 1: Add, Button, gButton_Ship_Crew4 x516.66 y211 w63.33 h35, Ship+`nCrew

Gui, 1: Add, checkbox, vUnequip_Ships_checked x20 y265 h30, Unequip Modules


Gui, 1: Font, cWhite s12, Arial
Gui, 1: Add, DDL, vLoaded_Preset gLoad_Preset x105 y305 w130 sort choose1, %Preferences%
Gui, 1: Add, Button, gLoad_Preset x240 y305 w130 h25, Load Preset



Gui, 1: Add, Button, gButton_All_Ships x380 y260 w97.5 h35, Equip all Ships
Gui, 1: Add, Button, gButton_All_Crew x482.5 y260 w97.5 h35, Equip all Crew
Gui, 1: Add, Button, gButton_All x380 y300 w200 h35, Equip all Ships + Crew


Gui, 1: Font, cWhite s9, Arial

Gui, 1: Add, Button, gEdit_Preferences_Gui_Button x415 y345 w80 h20, Presets
Gui, 1: Add, Button, gSetup_GUI x500 y345 w80 h20, Setup
Gui, 1: Add, Button, gShow_Ship_Stats_Gui_Button x415 y370 w80 h20, Loadouts
Gui, 1: Add, Button, gExit x500 y370 w80 h20, Exit


Gui, 13: hide
Gui, 1: Show, x100 y100 h400 w600, Star Conflict
Gui, 2: destroy
Gui, 3: destroy
Gui, 8: destroy

GuiControl, 1: choose, Ship1, None
GuiControl, 1: choose, Ship2, None
GuiControl, 1: choose, Ship3, None
GuiControl, 1: choose, Ship4, None
gosub, Last_Selected


If (Coordinates_Check_Implant_Color = "ERROR") or (Coordinates_Check_Empire = "ERROR") or (Coordinates_Check_Federation = "ERROR") or (Coordinates_Check_Jericho = "ERROR") or (Coordinates_Check_Ellydium = "ERROR") or (Coordinates_Check_Unique = "ERROR") or (Coordinates_Check_Slot1 = "ERROR") or (Coordinates_Check_Slot2 = "ERROR") or (Coordinates_Check_Slot3 = "ERROR") or (Coordinates_Check_Slot4 = "ERROR") or (Coordinates_Check_Preset1 = "ERROR") or (Coordinates_Check_Preset2 = "ERROR") or (Coordinates_Check_Preset3 = "ERROR") or (Coordinates_Check_Preset4 = "ERROR") or (Coordinates_Check_PresetL = "ERROR") or (Coordinates_Check_Yes = "ERROR") or (Coordinates_Check_Scroll = "ERROR") or (Coordinates_Check_Back = "ERROR") or (Coordinates_Check_Crew_A = "ERROR") or (Coordinates_Check_Crew_B = "ERROR") or (Coordinates_Check_Crew_C = "ERROR") or (Coordinates_Check_Crew_D = "ERROR") or (Coordinates_Check_Crew1_1 = "ERROR") or (Coordinates_Check_Crew15_3 = "ERROR") or (Coordinates_Check_Implant = "ERROR")
{
msgbox, Please add the missing coordinates
Gui, 8: destroy
goto, Setup_GUI
}
return


;--------------------------------------------------Main--------------------------------------------------

ShipSelected_routine_all:
gosub, ShipSelected_routine1
gosub, ShipSelected_routine2
gosub, ShipSelected_routine3
gosub, ShipSelected_routine4
return

ShipSelected_routine1:
Gui, 1:Submit, nohide
IniRead,Builds_Ship1,%A_ScriptDir%\Builds\%Ship1%.ini
StringReplace, Builds_Ship1,Builds_Ship1, `n,, All
GuiControl, 1: , Builds_Ship1_selected, |%Builds_Ship1%
GuiControl, 1: choose, Builds_Ship1_selected, 1
return

ShipSelected_routine2:
Gui, 1:Submit, nohide
IniRead,Builds_Ship2,%A_ScriptDir%\Builds\%Ship2%.ini
StringReplace, Builds_Ship2,Builds_Ship2, `n,, All
GuiControl, 1: , Builds_Ship2_selected, |%Builds_Ship2%
GuiControl, 1: choose, Builds_Ship2_selected, 1
return

ShipSelected_routine3:
Gui, 1:Submit, nohide
IniRead,Builds_Ship3,%A_ScriptDir%\Builds\%Ship3%.ini
StringReplace, Builds_Ship3,Builds_Ship3, `n,, All
GuiControl, 1: , Builds_Ship3_selected, |%Builds_Ship3%
GuiControl, 1: choose, Builds_Ship3_selected, 1
return

ShipSelected_routine4:
Gui, 1:Submit, nohide
IniRead,Builds_Ship4,%A_ScriptDir%\Builds\%Ship4%.ini
StringReplace, Builds_Ship4,Builds_Ship4, `n,, All
GuiControl, 1: , Builds_Ship4_selected, |%Builds_Ship4%
GuiControl, 1: choose, Builds_Ship4_selected, 1
return

BuildSelected_routine1:
Gui, 1:Submit, nohide
return

BuildSelected_routine2:
Gui, 1:Submit, nohide
return

BuildSelected_routine3:
Gui, 1:Submit, nohide
return

BuildSelected_routine4:
Gui, 1:Submit, nohide
return


;--------------------------------------------------Presets--------------------------------------------------


Load_Preset:
Gui, 1:Submit, nohide
StringTrimLeft, Loaded_Preset, Loaded_Preset, 1

IniRead, Edit_checked1_P,%A_ScriptDir%\Settings\Preferences.ini,%Loaded_Preset%|,Checked1
IniRead, Edit_checked2_P,%A_ScriptDir%\Settings\Preferences.ini,%Loaded_Preset%|,Checked2
IniRead, Edit_checked3_P,%A_ScriptDir%\Settings\Preferences.ini,%Loaded_Preset%|,Checked3
IniRead, Edit_checked4_P,%A_ScriptDir%\Settings\Preferences.ini,%Loaded_Preset%|,Checked4
GuiControl, 1: ,Ship1_checked, %Edit_checked1_P%
GuiControl, 1: ,Ship2_checked, %Edit_checked2_P%
GuiControl, 1: ,Ship3_checked, %Edit_checked3_P%
GuiControl, 1: ,Ship4_checked, %Edit_checked4_P%
IniRead,Preference_Ship1,%A_ScriptDir%\Settings\Preferences.ini,%Loaded_Preset%|,Ship1
IniRead,Preference_Ship2,%A_ScriptDir%\Settings\Preferences.ini,%Loaded_Preset%|,Ship2
IniRead,Preference_Ship3,%A_ScriptDir%\Settings\Preferences.ini,%Loaded_Preset%|,Ship3
IniRead,Preference_Ship4,%A_ScriptDir%\Settings\Preferences.ini,%Loaded_Preset%|,Ship4
GuiControl, 1: choose, Ship1, %Preference_Ship1%
GuiControl, 1: choose, Ship2, %Preference_Ship2%
GuiControl, 1: choose, Ship3, %Preference_Ship3%
GuiControl, 1: choose, Ship4, %Preference_Ship4%
IniRead,Preference_Build1,%A_ScriptDir%\Settings\Preferences.ini,%Loaded_Preset%|,Build1
IniRead,Preference_Build2,%A_ScriptDir%\Settings\Preferences.ini,%Loaded_Preset%|,Build2
IniRead,Preference_Build3,%A_ScriptDir%\Settings\Preferences.ini,%Loaded_Preset%|,Build3
IniRead,Preference_Build4,%A_ScriptDir%\Settings\Preferences.ini,%Loaded_Preset%|,Build4
gosub, ShipSelected_routine1
gosub, ShipSelected_routine2
gosub, ShipSelected_routine3
gosub, ShipSelected_routine4
GuiControl, 1: choose, Builds_Ship1_selected, %Preference_Build1%
GuiControl, 1: choose, Builds_Ship2_selected, %Preference_Build2%
GuiControl, 1: choose, Builds_Ship3_selected, %Preference_Build3%
GuiControl, 1: choose, Builds_Ship4_selected, %Preference_Build4%
Gui, 1:Submit, nohide
return


Last_Selected:
IniRead, Edit_checked1_P,%A_ScriptDir%\Settings\Preferences.ini,Last|,Checked1
IniRead, Edit_checked2_P,%A_ScriptDir%\Settings\Preferences.ini,Last|,Checked2
IniRead, Edit_checked3_P,%A_ScriptDir%\Settings\Preferences.ini,Last|,Checked3
IniRead, Edit_checked4_P,%A_ScriptDir%\Settings\Preferences.ini,Last|,Checked4
GuiControl, 1: ,Ship1_checked, %Edit_checked1_P%
GuiControl, 1: ,Ship2_checked, %Edit_checked2_P%
GuiControl, 1: ,Ship3_checked, %Edit_checked3_P%
GuiControl, 1: ,Ship4_checked, %Edit_checked4_P%
IniRead,Preference_Ship1,%A_ScriptDir%\Settings\Preferences.ini,Last|,Ship1
IniRead,Preference_Ship2,%A_ScriptDir%\Settings\Preferences.ini,Last|,Ship2
IniRead,Preference_Ship3,%A_ScriptDir%\Settings\Preferences.ini,Last|,Ship3
IniRead,Preference_Ship4,%A_ScriptDir%\Settings\Preferences.ini,Last|,Ship4
GuiControl, 1: choose, Ship1, %Preference_Ship1%
GuiControl, 1: choose, Ship2, %Preference_Ship2%
GuiControl, 1: choose, Ship3, %Preference_Ship3%
GuiControl, 1: choose, Ship4, %Preference_Ship4%
IniRead,Preference_Build1,%A_ScriptDir%\Settings\Preferences.ini,Last|,Build1
IniRead,Preference_Build2,%A_ScriptDir%\Settings\Preferences.ini,Last|,Build2
IniRead,Preference_Build3,%A_ScriptDir%\Settings\Preferences.ini,Last|,Build3
IniRead,Preference_Build4,%A_ScriptDir%\Settings\Preferences.ini,Last|,Build4
gosub, ShipSelected_routine1
gosub, ShipSelected_routine2
gosub, ShipSelected_routine3
gosub, ShipSelected_routine4
GuiControl, 1: choose, Builds_Ship1_selected, %Preference_Build1%
GuiControl, 1: choose, Builds_Ship2_selected, %Preference_Build2%
GuiControl, 1: choose, Builds_Ship3_selected, %Preference_Build3%
GuiControl, 1: choose, Builds_Ship4_selected, %Preference_Build4%
IniRead, Unequip_P,%A_ScriptDir%\Settings\Preferences.ini,Last|,Unequip
GuiControl, 1: ,Unequip_Ships_checked, %Unequip_P%
Gui, 1:Submit, nohide
return


;--------------------------------------------------Buttons--------------------------------------------------


Button_Only_Ship1:
Gui, 1:Submit, nohide
If (Ship1 != "None")
{
	gosub, Prepare
	gosub, Equip_Ship1
	gosub, Close_Window
	gosub, Equip_Preset1
	gosub, Resolve
}
else
{
	gosub, Prepare
	gosub, Equip_Ship1
	gosub, Close_Window
	gosub, Resolve
}
return

Button_Only_Ship2:
Gui, 1:Submit, nohide
If (Ship2 != "None")
{
	gosub, Prepare
	gosub, Equip_Ship2
	gosub, Close_Window
	gosub, Equip_Preset2
	gosub, Resolve
}
else
{
	gosub, Prepare
	gosub, Equip_Ship2
	gosub, Close_Window
	gosub, Resolve
}
return

Button_Only_Ship3:
Gui, 1:Submit, nohide
If (Ship3 != "None")
{
	gosub, Prepare
	gosub, Equip_Ship3
	gosub, Close_Window
	gosub, Equip_Preset3
	gosub, Resolve
}
else
{
	gosub, Prepare
	gosub, Equip_Ship3
	gosub, Close_Window
	gosub, Resolve
}
return

Button_Only_Ship4:
Gui, 1:Submit, nohide
If (Ship4 != "None")
{
	gosub, Prepare
	gosub, Equip_Ship4
	gosub, Close_Window
	gosub, Equip_Preset4
	gosub, Resolve
}
else
{
	gosub, Prepare
	gosub, Equip_Ship4
	gosub, Close_Window
	gosub, Resolve
}
return



Button_Only_Crew1:
Gui, 1:Submit, nohide
If (Ship1 != "None") and (Builds_Ship1_selected != "None") and (Builds_Ship1_selected != "")
{
	gosub, Prepare
	gosub, Equip_Crew1
	gosub, Resolve
}
return

Button_Only_Crew2:
Gui, 1:Submit, nohide
If (Ship2 != "None") and (Builds_Ship2_selected != "None") and (Builds_Ship2_selected != "")
{
	gosub, Prepare
	gosub, Equip_Crew2
	gosub, Resolve
}
return

Button_Only_Crew3:
Gui, 1:Submit, nohide
If (Ship3 != "None") and (Builds_Ship3_selected != "None") and (Builds_Ship3_selected != "")
{
	gosub, Prepare
	gosub, Equip_Crew3
	gosub, Resolve
}
return

Button_Only_Crew4:
Gui, 1:Submit, nohide
If (Ship4 != "None") and (Builds_Ship4_selected != "None") and (Builds_Ship4_selected != "")
{
	gosub, Prepare
	gosub, Equip_Crew4
	gosub, Resolve
}
return



Button_Ship_Crew1:
Gui, 1:Submit, nohide
If (Ship1 != "None")
{
	gosub, Prepare
	gosub, Equip_Ship1
	gosub, Close_Window
	gosub, Equip_Preset1
	gosub, Equip_Crew1
	gosub, Resolve
}
return

Button_Ship_Crew2:
Gui, 1:Submit, nohide
If (Ship2 != "None")
{
	gosub, Prepare
	gosub, Equip_Ship2
	gosub, Close_Window
	gosub, Equip_Preset2
	gosub, Equip_Crew2
	gosub, Resolve
}
return

Button_Ship_Crew3:
Gui, 1:Submit, nohide
If (Ship3 != "None")
{
	gosub, Prepare
	gosub, Equip_Ship3
	gosub, Close_Window
	gosub, Equip_Preset3
	gosub, Equip_Crew3
	gosub, Resolve
}
return

Button_Ship_Crew4:
Gui, 1:Submit, nohide
If (Ship4 != "None")
{
	gosub, Prepare
	gosub, Equip_Ship4
	gosub, Close_Window
	gosub, Equip_Preset4
	gosub, Equip_Crew4
	gosub, Resolve
}
return



Button_All_Ships:
	Gui, 1:Submit, nohide
	if (Ship1_checked = 1) or (Ship2_checked = 1) or (Ship3_checked = 1) or (Ship4_checked = 1)
	{
	gosub, Prepare
	}
	if (Ship1_checked = 1)
	{
	gosub, Equip_Ship1
	}
	if (Ship2_checked = 1)
	{
	gosub, Equip_Ship2
	}
	if (Ship3_checked = 1)
	{
	gosub, Equip_Ship3
	}
	if (Ship4_checked = 1)
	{
	gosub, Equip_Ship4
	}
	if (Ship1_checked = 1) or (Ship2_checked = 1) or (Ship3_checked = 1) or (Ship4_checked = 1)
	{
	gosub, Close_Window
	}
	if (Ship1_checked = 1)
	{
	gosub, Equip_Preset1
	}
	if (Ship2_checked = 1)
	{
	gosub, Equip_Preset2
	}
	if (Ship3_checked = 1)
	{
	gosub, Equip_Preset3
	}
	if (Ship4_checked = 1)
	{
	gosub, Equip_Preset4
	}
	if (Ship1_checked = 1) or (Ship2_checked = 1) or (Ship3_checked = 1) or (Ship4_checked = 1)
	{
	gosub, Resolve
	}
return

Button_All_Crew:
	Gui, 1:Submit, nohide
	if (Ship1_checked = 1) or (Ship2_checked = 1) or (Ship3_checked = 1) or (Ship4_checked = 1)
	{
	gosub, Prepare
	}
	if (Ship1_checked = 1)
	{
	gosub, Equip_Crew1
	}
	if (Ship2_checked = 1)
	{
	gosub, Equip_Crew2
	}
	if (Ship3_checked = 1)
	{
	gosub, Equip_Crew3
	}
	if (Ship4_checked = 1)
	{
	gosub, Equip_Crew4
	}
	if (Ship1_checked = 1) or (Ship2_checked = 1) or (Ship3_checked = 1) or (Ship4_checked = 1)
	{
	gosub, Resolve
	}
return

Button_All:
	Gui, 1:Submit, nohide
	if (Ship1_checked = 1) or (Ship2_checked = 1) or (Ship3_checked = 1) or (Ship4_checked = 1)
	{
	gosub, Prepare
	}
	if (Ship1_checked = 1)
	{
	gosub, Equip_Ship1
	}
	if (Ship2_checked = 1)
	{
	gosub, Equip_Ship2
	}
	if (Ship3_checked = 1)
	{
	gosub, Equip_Ship3
	}
	if (Ship4_checked = 1)
	{
	gosub, Equip_Ship4
	}
	if (Ship1_checked = 1) or (Ship2_checked = 1) or (Ship3_checked = 1) or (Ship4_checked = 1)
	{
	gosub, Close_Window
	}
	if (Ship1_checked = 1)
	{
	gosub, Equip_Preset1
	}
	if (Ship2_checked = 1)
	{
	gosub, Equip_Preset2
	}
	if (Ship3_checked = 1)
	{
	gosub, Equip_Preset3
	}
	if (Ship4_checked = 1)
	{
	gosub, Equip_Preset4
	}
	if (Ship1_checked = 1)
	{
	gosub, Equip_Crew1
	}
	if (Ship2_checked = 1)
	{
	gosub, Equip_Crew2
	}
	if (Ship3_checked = 1)
	{
	gosub, Equip_Crew3
	}
	if (Ship4_checked = 1)
	{
	gosub, Equip_Crew4
	}
	if (Ship1_checked = 1) or (Ship2_checked = 1) or (Ship3_checked = 1) or (Ship4_checked = 1)
	{
	gosub, Resolve
	}
return


;--------------------------------------------------Select Ships--------------------------------------------------


Equip_Ship1:
Gui, 1:Submit, nohide
Ship_loaded := Ship1
Build_Ship_loaded := Builds_Ship1_selected
Slot_selected := "Slot1"
gosub, Equip_Ship
return

Equip_Ship2:
Gui, 1:Submit, nohide
Ship_loaded := Ship2
Build_Ship_loaded := Builds_Ship2_selected
Slot_selected := "Slot2"
gosub, Equip_Ship
return

Equip_Ship3:
Gui, 1:Submit, nohide
Ship_loaded := Ship3
Build_Ship_loaded := Builds_Ship3_selected
Slot_selected := "Slot3"
gosub, Equip_Ship
return

Equip_Ship4:
Gui, 1:Submit, nohide
Ship_loaded := Ship4
Build_Ship_loaded := Builds_Ship4_selected
Slot_selected := "Slot4"
gosub, Equip_Ship
return


;--------------------------------------------------Equip Preset--------------------------------------------------


Equip_Preset1:
Gui, 1:Submit, nohide
Ship_loaded := Ship1
Build_Ship_loaded := Builds_Ship1_selected
Slot_selected := "Slot1"
gosub, Equip_Preset
return

Equip_Preset2:
Gui, 1:Submit, nohide
Ship_loaded := Ship2
Build_Ship_loaded := Builds_Ship2_selected
Slot_selected := "Slot2"
gosub, Equip_Preset
return

Equip_Preset3:
Gui, 1:Submit, nohide
Ship_loaded := Ship3
Build_Ship_loaded := Builds_Ship3_selected
Slot_selected := "Slot3"
gosub, Equip_Preset
return

Equip_Preset4:
Gui, 1:Submit, nohide
Ship_loaded := Ship4
Build_Ship_loaded := Builds_Ship4_selected
Slot_selected := "Slot4"
gosub, Equip_Preset
return


;--------------------------------------------------Equip Crew--------------------------------------------------


Equip_Crew1:
Gui, 1:Submit, nohide
Crew_selected := "Crew_A"
Ship_loaded := Ship1
Build_Ship_loaded := Builds_Ship1_selected
gosub, Load_Crew
gosub, Implant
return

Equip_Crew2:
Gui, 1:Submit, nohide
Crew_selected := "Crew_B"
Ship_loaded := Ship2
Build_Ship_loaded := Builds_Ship2_selected
gosub, Load_Crew
gosub, Implant
return

Equip_Crew3:
Gui, 1:Submit, nohide
Crew_selected := "Crew_C"
Ship_loaded := Ship3
Build_Ship_loaded := Builds_Ship3_selected
gosub, Load_Crew
gosub, Implant
return

Equip_Crew4:
Gui, 1:Submit, nohide
Crew_selected := "Crew_D"
Ship_loaded := Ship4
Build_Ship_loaded := Builds_Ship4_selected
gosub, Load_Crew
gosub, Implant
return

;--------------------------------------------------Prepare--------------------------------------------------

Prepare:
Gui 1: hide
BlockInput, MouseMove
MouseGetPos, x1, y1
WinActivate, ahk_class game_main_window
Sleep, 50
WinActivate, ahk_class game_main_window
Sleep, 50
Close_Window:
IniRead,ClickX,%A_ScriptDir%\Settings\Coordinates.ini,Back,x
IniRead,ClickY,%A_ScriptDir%\Settings\Coordinates.ini,Back,y
ControlSend, , {esc}, ahk_class game_main_window
Sleep, 50
Click, %ClickX% %ClickY%
Sleep, 50
ControlSend, , {enter}, ahk_class game_main_window
Sleep, 50
ControlSend, , {esc}, ahk_class game_main_window
Sleep, 50
return


Resolve:
ControlSend, , {esc}, ahk_class game_main_window
IniRead,ClickX,%A_ScriptDir%\Settings\Coordinates.ini,Back,x
IniRead,ClickY,%A_ScriptDir%\Settings\Coordinates.ini,Back,y
Click, %ClickX% %ClickY%
DllCall("SetCursorPos", int, x1, int, y1)
BlockInput, MouseMoveOff
Gui 1: show
return


Equip_Ship:
If Ship_loaded != None
{
	ControlSend, , {t}, ahk_class game_main_window
	sleep, 200
	IniRead,ClickX,%A_ScriptDir%\Settings\Coordinates.ini,%Slot_selected%,x
	IniRead,ClickY,%A_ScriptDir%\Settings\Coordinates.ini,%Slot_selected%,y
	Click, %ClickX% %ClickY%
	sleep, 200

	If Unequip_Ships_checked = 1
	{
	Click, %ClickX% %ClickY% right
	sleep, 200

	x_min := ClickX-50
	x_max := ClickX+500
	y_min := ClickY-300
	y_max := ClickY+300

	ImageSearch, ClickX, ClickY, x_min, y_min, x_max, y_max, *50 %A_ScriptDir%\Settings\Remove_all_modules.png
	If (ErrorLevel = 0)
	{
		ClickX := ClickX+10
		ClickY := ClickY+10
		Click, %ClickX% %ClickY%
		sleep, 1000
	}
	else if (ErrorLevel = 2)
	{
		msgbox, Could not find the unequip screenshot. Please place save the screenshot in "Settings" folder named "Remove_all_modules.png".
	}
}

IniRead,Faction,%A_ScriptDir%\Settings\ShipList.ini,%Ship_loaded%|,Faction
IniRead,ClickX,%A_ScriptDir%\Settings\Coordinates.ini,%Faction%,x
IniRead,ClickY,%A_ScriptDir%\Settings\Coordinates.ini,%Faction%,y
Click, %ClickX% %ClickY%
sleep, 200

IniRead,ClickX,%A_ScriptDir%\Settings\Coordinates.ini,Scroll,x
IniRead,ClickY,%A_ScriptDir%\Settings\Coordinates.ini,Scroll,y
IniRead,Scroll_Direction,%A_ScriptDir%\Settings\ShipList.ini,%Ship_loaded%|,Scroll
IniRead,Scroll_Amount,%A_ScriptDir%\Settings\ShipList.ini,%Ship_loaded%|,Scroll_amount
Loop, %Scroll_amount%
{
Click, %ClickX% %ClickY%
MouseClick, %Scroll_Direction%
Sleep, 1
}
IniRead,Scroll_Direction,%A_ScriptDir%\Settings\ShipList.ini,%Ship_loaded%|,Scroll2
IniRead,Scroll_Amount,%A_ScriptDir%\Settings\ShipList.ini,%Ship_loaded%|,Scroll_amount2
Sleep, 100
Loop, %Scroll_amount%
{
Click, %ClickX% %ClickY%
MouseClick, %Scroll_Direction%
Sleep, 1
}
sleep, 200

IniRead,ClickX,%A_ScriptDir%\Settings\ShipList.ini,%Ship_loaded%|,x
IniRead,ClickY,%A_ScriptDir%\Settings\ShipList.ini,%Ship_loaded%|,Y
Click, %ClickX% %ClickY%
sleep, 1000
}

;------------------------- Ellydium Ship call -------------------------

IniRead,check_ellydium_tree,%A_ScriptDir%\Builds\%Ship_Loaded%.ini,%Build_Ship_Loaded%|,SpecMod_1

If ((Faction = "Ellydium") and (check_ellydium_tree != "ERROR"))
{
IniRead,ClickX,%A_ScriptDir%\Settings\ShipList.ini,%Ship_loaded%|,x_ellydium
IniRead,ClickY,%A_ScriptDir%\Settings\ShipList.ini,%Ship_loaded%|,y_ellydium
Click, %ClickX% %ClickY%
Click, 100, 100, 0
LoadEllydiumShipData(Ship_loaded, Build_Ship_loaded)
Sleep, 500
RunEllydiumPixelAutomation()

ControlSend, , {enter}, ahk_class game_main_window
ControlSend, , {esc}, ahk_class game_main_window
ControlSend, , {esc}, ahk_class game_main_window
ControlSend, , {t}, ahk_class game_main_window

}


If Ship_loaded = None
{
ControlSend, , {t}, ahk_class game_main_window
sleep, 200
IniRead,ClickX,%A_ScriptDir%\Settings\Coordinates.ini,%Slot_selected%,x
IniRead,ClickY,%A_ScriptDir%\Settings\Coordinates.ini,%Slot_selected%,y

If Unequip_Ships_checked = 1
{
Click, %ClickX% %ClickY% right
sleep, 200

x_min := ClickX-50
x_max := ClickX+500
y_min := ClickY-300
y_max := ClickY+300

ImageSearch, ClickX, ClickY, x_min, y_min, x_max, y_max, *50 %A_ScriptDir%\Remove_all_modules.png
If (ClickX != "")
	{
	ClickX := ClickX+10
	ClickY := ClickY+10
	Click, %ClickX% %ClickY%
	sleep, 1000
	}
}

Click %ClickX% %ClickY% Down
Sleep, 200
MouseMove, 0, -200, 100, R
Click Up
sleep, 200
}
return



Equip_Preset:
If (Build_ship_loaded != "None") and (Ship_loaded != "None") and (Build_ship_loaded != "")
{
IniRead,Preset,%A_ScriptDir%\Builds\%Ship_loaded%.ini,%Build_Ship_loaded%|,Preset

If (Preset != "")
{
IniRead,Slot,%A_ScriptDir%\Settings\Coordinates.ini,%Slot_selected%,Slot
ControlSend, , {%Slot%}, ahk_class game_main_window
sleep, 200

IniRead,ClickX,%A_ScriptDir%\Settings\Coordinates.ini,Preset%Preset%,x
IniRead,ClickY,%A_ScriptDir%\Settings\Coordinates.ini,Preset%Preset%,y
Click, %ClickX% %ClickY%
sleep, 200

IniRead,ClickX,%A_ScriptDir%\Settings\Coordinates.ini,Load Preset,x
IniRead,ClickY,%A_ScriptDir%\Settings\Coordinates.ini,Load Preset,y
Click, %ClickX% %ClickY%
sleep, 100
Click, %ClickX% %ClickY%
sleep, 200

IniRead,ClickX,%A_ScriptDir%\Settings\Coordinates.ini,Yes,x
IniRead,ClickY,%A_ScriptDir%\Settings\Coordinates.ini,Yes,y
Click, %ClickX% %ClickY%
sleep, 1000
}
}
return



Load_Crew:
Gui, 1:Submit, nohide
IniRead,1,%A_ScriptDir%\Builds\%Ship_loaded%.ini,%Build_Ship_loaded%|,Crew1
IniRead,2,%A_ScriptDir%\Builds\%Ship_loaded%.ini,%Build_Ship_loaded%|,Crew2
IniRead,3,%A_ScriptDir%\Builds\%Ship_loaded%.ini,%Build_Ship_loaded%|,Crew3
IniRead,4,%A_ScriptDir%\Builds\%Ship_loaded%.ini,%Build_Ship_loaded%|,Crew4
IniRead,5,%A_ScriptDir%\Builds\%Ship_loaded%.ini,%Build_Ship_loaded%|,Crew5
IniRead,6,%A_ScriptDir%\Builds\%Ship_loaded%.ini,%Build_Ship_loaded%|,Crew6
IniRead,7,%A_ScriptDir%\Builds\%Ship_loaded%.ini,%Build_Ship_loaded%|,Crew7
IniRead,8,%A_ScriptDir%\Builds\%Ship_loaded%.ini,%Build_Ship_loaded%|,Crew8
IniRead,9,%A_ScriptDir%\Builds\%Ship_loaded%.ini,%Build_Ship_loaded%|,Crew9
IniRead,10,%A_ScriptDir%\Builds\%Ship_loaded%.ini,%Build_Ship_loaded%|,Crew10
IniRead,11,%A_ScriptDir%\Builds\%Ship_loaded%.ini,%Build_Ship_loaded%|,Crew11
IniRead,12,%A_ScriptDir%\Builds\%Ship_loaded%.ini,%Build_Ship_loaded%|,Crew12
IniRead,13,%A_ScriptDir%\Builds\%Ship_loaded%.ini,%Build_Ship_loaded%|,Crew13
IniRead,14,%A_ScriptDir%\Builds\%Ship_loaded%.ini,%Build_Ship_loaded%|,Crew14
IniRead,15,%A_ScriptDir%\Builds\%Ship_loaded%.ini,%Build_Ship_loaded%|,Crew15

IniRead,ClickX,%A_ScriptDir%\Settings\Coordinates.ini,%Crew_selected%,x
IniRead,ClickY,%A_ScriptDir%\Settings\Coordinates.ini,%Crew_selected%,y
return


Implant:
If (Build_ship_loaded != "None") and (Ship_loaded != "None") and (Build_ship_loaded != "")
{
ControlSend, , {c}, ahk_class game_main_window
Sleep, 200

Click, %ClickX% %ClickY%
Sleep, 200

gosub, Set_Implants

IniRead,ClickX,%A_ScriptDir%\Settings\Coordinates.ini,Implant,x
IniRead,ClickY,%A_ScriptDir%\Settings\Coordinates.ini,Implant,y
IniRead,implant_color,%A_ScriptDir%\Settings\Coordinates.ini,Implant,implant_color

Click, %ClickX% %ClickY%


SetTimer, Break_Impant_Loop, -3000
PixelSearch, Implant_color_check_x, Implant_color_check_y, %ClickX%, %ClickY%, %ClickX%, %ClickY%, %implant_color%, 6, Fast RGB
while !Implant_color_check_x
{
Sleep, 100
PixelSearch, Implant_color_check_x, Implant_color_check_y, %ClickX%, %ClickY%, %ClickX%, %ClickY%, %implant_color%, 6, Fast RGB
}
Sleep, 200
SetTimer, Break_Impant_Loop, Off
}
return

;--------------------------------------------------Set Implants--------------------------------------------------

Set_Implants:
Crew_n := 1
Loop, 15
{
	IniRead,s,%A_ScriptDir%\Builds\%Ship_Loaded%.ini,%Build_Ship_loaded%|,Crew%Crew_n%
	Crew_selected = Crew%Crew_n%-%s%

	IniRead,ClickX,%A_ScriptDir%\Settings\Coordinates.ini,%Crew_selected%,x
	IniRead,ClickY,%A_ScriptDir%\Settings\Coordinates.ini,%Crew_selected%,y
	If (s != "")
	{
	Click, %ClickX% %ClickY%
	}
	Sleep, 20
	Crew_n++
}
return



;--------------------------------------------------Edit Preferences--------------------------------------------------

Edit_Preferences_Gui_Button:
Gui, 13: show
Gui, 1:Submit, nohide
IniWrite,%Ship1_checked%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Checked1
IniWrite,%Ship2_checked%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Checked2
IniWrite,%Ship3_checked%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Checked3
IniWrite,%Ship4_checked%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Checked4 
IniWrite,%Ship1%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Ship1
IniWrite,%Ship2%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Ship2
IniWrite,%Ship3%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Ship3
IniWrite,%Ship4%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Ship4 
IniWrite,%Builds_Ship1_selected%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Build1
IniWrite,%Builds_Ship2_selected%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Build2
IniWrite,%Builds_Ship3_selected%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Build3
IniWrite,%Builds_Ship4_selected%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Build4
IniWrite,%Unequip_Ships_checked%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Unequip

Edit_Preferences_Gui:
IniRead,Preferences,%A_ScriptDir%\Settings\Preferences.ini
StringTrimLeft, Preferences, Preferences, 5
IniRead,FullShipList,%A_ScriptDir%\Settings\ShipList.ini
StringReplace, FullShipList,FullShipList, `n,, All


Gui, 2: +AlwaysOnTop +Toolwindow
Gui, 2: Color, 000000
Gui, 2: Font, cWhite s12, Arial


Gui, 2: Add, Text, x0 y10 w600 h30 center, -------------------- Edit Presets --------------------


Gui, 2: Add, Text, x170 y58, Preset:
Gui, 2: Add, Text, x202 y110 w150 h30, Ship
Gui, 2: Add, Text, x338 y110 w150 h30, Loadout
Gui, 2: Add, checkbox, vEdit_checked1_P x75 y139 h30, Slot 1:
Gui, 2: Add, checkbox, vEdit_checked2_P x75 y189 h30, Slot 2:
Gui, 2: Add, checkbox, vEdit_checked3_P x75 y239 h30, Slot 3:
Gui, 2: Add, checkbox, vEdit_checked4_P x75 y289 h30, Slot 4:


Gui, 2: Add, DDL, vMode gLoad_ini x235 y55 w130 Choose1 sort, %Preferences%
Gui, 2: Add, Button, gAdd_New_Preference_Gui x375 y53 w30 h30, +
Gui, 2: Add, Button, gDelete_Preference x415 y53 w30 h30, -
Gui, 2: Add, Button, gRename_Preference_Gui x455 y53 h30, Rename


Gui, 2: Add, DDL, vShip_Edit_User1 gEdit_Ship1_changed x160 y140 w130 sort, %FullShipList%
Gui, 2: Add, DDL, vShip_Edit_User2 gEdit_Ship2_changed x160 y190 w130 sort, %FullShipList%
Gui, 2: Add, DDL, vShip_Edit_User3 gEdit_Ship3_changed x160 y240 w130 sort, %FullShipList%
Gui, 2: Add, DDL, vShip_Edit_User4 gEdit_Ship4_changed x160 y290 w130 sort, %FullShipList%


Gui, 2: Add, DDL, vBuild_Edit_User1 x310 y140 w130 Choose1, 
Gui, 2: Add, DDL, vBuild_Edit_User2 x310 y190 w130 Choose1,
Gui, 2: Add, DDL, vBuild_Edit_User3 x310 y240 w130 Choose1,
Gui, 2: Add, DDL, vBuild_Edit_User4 x310 y290 w130 Choose1,


Gui, 2: Add, Button, gSave_ini x260 y335 w80 h30, Save


Gui, 2: Font, cWhite s9, Arial
Gui, 2: Add, Button, gExit2 x500 y360 w80 h20, Back

Gui, 13: hide
Gui, 2: Show, x100 y100 h400 w600, Presets
Gui, 1: destroy
Gui, 9: destroy



Load_ini:
GuiControl, 2: chooseString, Ship_Edit_User1, None
GuiControl, 2: chooseString, Ship_Edit_User2, None
GuiControl, 2: chooseString, Ship_Edit_User3, None
GuiControl, 2: chooseString, Ship_Edit_User4, None
Gui, 2:Submit, nohide
StringReplace, Mode,Mode, `n,, All


IniRead, Edit_checked1_P,%A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Checked1
Iniread, Edit_Ship1_P, %A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Ship1
Iniread, Edit_Build1_P, %A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Build1

IniRead, Edit_checked2_P,%A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Checked2
Iniread, Edit_Ship2_P, %A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Ship2
Iniread, Edit_Build2_P, %A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Build2

IniRead, Edit_checked3_P,%A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Checked3
Iniread, Edit_Ship3_P, %A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Ship3
Iniread, Edit_Build3_P, %A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Build3

IniRead, Edit_checked4_P,%A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Checked4
Iniread, Edit_Ship4_P, %A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Ship4
Iniread, Edit_Build4_P, %A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Build4

If !Mode
{

}
else
{
GuiControl, 2: ,Edit_checked1_P, %Edit_checked1_P%
GuiControl, 2: ,Edit_checked2_P, %Edit_checked2_P%
GuiControl, 2: ,Edit_checked3_P, %Edit_checked3_P%
GuiControl, 2: ,Edit_checked4_P, %Edit_checked4_P%
}

GuiControl, 2: chooseString, Ship_Edit_User1, %Edit_Ship1_P%
GuiControl, 2: chooseString, Ship_Edit_User2, %Edit_Ship2_P%
GuiControl, 2: chooseString, Ship_Edit_User3, %Edit_Ship3_P%
GuiControl, 2: chooseString, Ship_Edit_User4, %Edit_Ship4_P%

Gui, 2:Submit, nohide

Iniread, Edit_Ship1_Builds, %A_ScriptDir%\Builds\%Ship_Edit_User1%.ini
Iniread, Edit_Ship2_Builds, %A_ScriptDir%\Builds\%Ship_Edit_User2%.ini
Iniread, Edit_Ship3_Builds, %A_ScriptDir%\Builds\%Ship_Edit_User3%.ini
Iniread, Edit_Ship4_Builds, %A_ScriptDir%\Builds\%Ship_Edit_User4%.ini

StringReplace, Edit_Ship1_Builds,Edit_Ship1_Builds, `n,, All
StringReplace, Edit_Ship2_Builds,Edit_Ship2_Builds, `n,, All
StringReplace, Edit_Ship3_Builds,Edit_Ship3_Builds, `n,, All
StringReplace, Edit_Ship4_Builds,Edit_Ship4_Builds, `n,, All

GuiControl, 2:, Build_Edit_User1, |%Edit_Ship1_Builds%
GuiControl, 2:, Build_Edit_User2, |%Edit_Ship2_Builds%
GuiControl, 2:, Build_Edit_User3, |%Edit_Ship3_Builds%
GuiControl, 2:, Build_Edit_User4, |%Edit_Ship4_Builds%
GuiControl, 2: chooseString, Build_Edit_User1, None
GuiControl, 2: chooseString, Build_Edit_User2, None
GuiControl, 2: chooseString, Build_Edit_User3, None
GuiControl, 2: chooseString, Build_Edit_User4, None
GuiControl, 2: chooseString, Build_Edit_User1, %Edit_Build1_P%
GuiControl, 2: chooseString, Build_Edit_User2, %Edit_Build2_P%
GuiControl, 2: chooseString, Build_Edit_User3, %Edit_Build3_P%
GuiControl, 2: chooseString, Build_Edit_User4, %Edit_Build4_P%
return


Edit_Ship1_changed:
Gui, 2:Submit, nohide
Iniread, Edit_Ship1_Builds, %A_ScriptDir%\Builds\%Ship_Edit_User1%.ini
StringReplace, Edit_Ship1_Builds,Edit_Ship1_Builds, `n,, All
GuiControl, 2: , Build_Edit_User1, |%Edit_Ship1_Builds%
GuiControl, 2: choose, Build_Edit_User1, 1
return

Edit_Ship2_changed:
Gui, 2:Submit, nohide
Iniread, Edit_Ship2_Builds, %A_ScriptDir%\Builds\%Ship_Edit_User2%.ini
StringReplace, Edit_Ship2_Builds,Edit_Ship2_Builds, `n,, All
GuiControl, 2: , Build_Edit_User2, |%Edit_Ship2_Builds%
GuiControl, 2: choose, Build_Edit_User2, 1
return

Edit_Ship3_changed:
Gui, 2:Submit, nohide
Iniread, Edit_Ship3_Builds, %A_ScriptDir%\Builds\%Ship_Edit_User3%.ini
StringReplace, Edit_Ship3_Builds,Edit_Ship3_Builds, `n,, All
GuiControl, 2: , Build_Edit_User3, |%Edit_Ship3_Builds%
GuiControl, 2: choose, Build_Edit_User3, 1
return

Edit_Ship4_changed:
Gui, 2:Submit, nohide
Iniread, Edit_Ship4_Builds, %A_ScriptDir%\Builds\%Ship_Edit_User4%.ini
StringReplace, Edit_Ship4_Builds,Edit_Ship4_Builds, `n,, All
GuiControl, 2: , Build_Edit_User4, |%Edit_Ship4_Builds%
GuiControl, 2: choose, Build_Edit_User4, 1
return


Save_ini:
Gui, 2: submit, nohide
StringReplace, Mode,Mode, `n,, All
If !Mode
{

}
else
{
Gui, 2: +Disabled
Gui, 12: +AlwaysOnTop -caption +border
Gui, 12: Color, 000000
Gui, 12: Font, cWhite s14, Arial
Gui, 12: Add, Text, x0 y10 w300 h30 center, ---------- INFO ----------
Gui, 12: Add, Text, vPreference_save_confirm_text1 x0 y45 w300 h50 center, Preset saved
Gui, 12: Add, Button, vPreference__save_confirm_button1 gPreference_save_confirm x110 y125 w80 h30 +default, Ok
Gui, 12: Add, Text, x0 y0 w300 h170 0x12
Gui, 12: Show, x287.5 y273.75 h170 w300, Info


IniWrite,%Edit_checked1_P%, %A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Checked1
IniWrite,%Edit_checked2_P%, %A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Checked2
IniWrite,%Edit_checked3_P%, %A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Checked3
IniWrite,%Edit_checked4_P%, %A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Checked4
IniWrite,%Ship_Edit_User1%, %A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Ship1
IniWrite,%Ship_Edit_User2%, %A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Ship2
IniWrite,%Ship_Edit_User3%, %A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Ship3
IniWrite,%Ship_Edit_User4%, %A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Ship4
IniWrite,%Build_Edit_User1%, %A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Build1
IniWrite,%Build_Edit_User2%, %A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Build2
IniWrite,%Build_Edit_User3%, %A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Build3
IniWrite,%Build_Edit_User4%, %A_ScriptDir%\Settings\Preferences.ini,%Mode%|,Build4
}
return


Preference_save_confirm:
Gui, 2: -Disabled
Gui, 12: destroy
return


Exit2:
goto, Gui_Start
return


;--------------------------------------------------Add New Preference--------------------------------------------------


Add_New_Preference_Gui:
Gui, 13: Show
IniRead,FullShipList,%A_ScriptDir%\Settings\ShipList.ini
StringReplace, FullShipList,FullShipList, `n,, All

Gui, 9: +AlwaysOnTop +Toolwindow
Gui, 9: Color, 000000
Gui, 9: Font, cWhite s12, Arial


Gui, 9: Add, Text, x0 y10 w600 h30 center, -------------------- Add New Preset --------------------


Gui, 9: Add, Text, x170 y58, Preset:
Gui, 9: Add, Text, x202 y110 w150 h30, Ship
Gui, 9: Add, Text, x338 y110 w150 h30, Loadout
Gui, 9: Add, checkbox, vNew_Preference_checked1 x75 y139 h30 checked, Slot 1:
Gui, 9: Add, checkbox, vNew_Preference_checked2 x75 y189 h30 checked, Slot 2:
Gui, 9: Add, checkbox, vNew_Preference_checked3 x75 y239 h30 checked, Slot 3:
Gui, 9: Add, checkbox, vNew_Preference_checked4 x75 y289 h30 checked, Slot 4:

Gui, 9: Font, cBlack s12, Arial
Gui, 9: Add, Edit, vNew_Preference_Name x235 y55 w130,


Gui, 9: Add, DDL, vNew_Preference_Ship_User1 gNew_Preference_Ship1_changed x160 y140 w130 sort, %FullShipList%
Gui, 9: Add, DDL, vNew_Preference_Ship_User2 gNew_Preference_Ship2_changed x160 y190 w130 sort, %FullShipList%
Gui, 9: Add, DDL, vNew_Preference_Ship_User3 gNew_Preference_Ship3_changed x160 y240 w130 sort, %FullShipList%
Gui, 9: Add, DDL, vNew_Preference_Ship_User4 gNew_Preference_Ship4_changed x160 y290 w130 sort, %FullShipList%


Gui, 9: Add, DDL, vNew_Preference_Build_User1 x310 y140 w130 Choose1, 
Gui, 9: Add, DDL, vNew_Preference_Build_User2 x310 y190 w130 Choose1,
Gui, 9: Add, DDL, vNew_Preference_Build_User3 x310 y240 w130 Choose1,
Gui, 9: Add, DDL, vNew_Preference_Build_User4 x310 y290 w130 Choose1,


Gui, 9: Add, Button, gSave_New_Preference x260 y335 w80 h30, Save


Gui, 9: Font, cWhite s9, Arial
Gui, 9: Add, Button, gExit9 x500 y360 w80 h20, Back


GuiControl, 9: choose, New_Preference_Ship_User1, None
GuiControl, 9: choose, New_Preference_Ship_User2, None
GuiControl, 9: choose, New_Preference_Ship_User3, None
GuiControl, 9: choose, New_Preference_Ship_User4, None
gosub, New_Preference_Ship1_changed
gosub, New_Preference_Ship2_changed
gosub, New_Preference_Ship3_changed
gosub, New_Preference_Ship4_changed


Gui, 9: Show, x100 y100 h400 w600, Presets
Gui, 2: destroy
Gui, 13: Hide

return


New_Preference_Ship1_changed:
Gui, 9:Submit, nohide
Iniread, New_Preference_Ship1_Builds, %A_ScriptDir%\Builds\%New_Preference_Ship_User1%.ini
StringReplace, New_Preference_Ship1_Builds,New_Preference_Ship1_Builds, `n,, All
GuiControl, 9: , New_Preference_Build_User1, |%New_Preference_Ship1_Builds%
GuiControl, 9: choose, New_Preference_Build_User1, 1
return

New_Preference_Ship2_changed:
Gui, 9:Submit, nohide
Iniread, New_Preference_Ship2_Builds, %A_ScriptDir%\Builds\%New_Preference_Ship_User2%.ini
StringReplace, New_Preference_Ship2_Builds,New_Preference_Ship2_Builds, `n,, All
GuiControl, 9: , New_Preference_Build_User2, |%New_Preference_Ship2_Builds%
GuiControl, 9: choose, New_Preference_Build_User2, 1
return

New_Preference_Ship3_changed:
Gui, 9:Submit, nohide
Iniread, New_Preference_Ship3_Builds, %A_ScriptDir%\Builds\%New_Preference_Ship_User3%.ini
StringReplace, New_Preference_Ship3_Builds,New_Preference_Ship3_Builds, `n,, All
GuiControl, 9: , New_Preference_Build_User3, |%New_Preference_Ship3_Builds%
GuiControl, 9: choose, New_Preference_Build_User3, 1
return

New_Preference_Ship4_changed:
Gui, 9:Submit, nohide
Iniread, New_Preference_Ship4_Builds, %A_ScriptDir%\Builds\%New_Preference_Ship_User4%.ini
StringReplace, New_Preference_Ship4_Builds,New_Preference_Ship4_Builds, `n,, All
GuiControl, 9: , New_Preference_Build_User4, |%New_Preference_Ship4_Builds%
GuiControl, 9: choose, New_Preference_Build_User4, 1
return



Save_New_Preference:
Gui, 9:Submit, nohide
New_Preference_Name := regexreplace(New_Preference_Name, "^\s+") ;trim beginning whitespace
New_Preference_Name := regexreplace(New_Preference_Name, "\s+$") ;trim ending whitespace
IniRead,Add_New_Preference_Check,%A_ScriptDir%\Settings\Preferences.ini,%New_Preference_Name%|,Ship1
GuiControl, 9: , New_Preference_Name, %New_Preference_Name%


Gui, 9: +Disabled
Gui, 12: +AlwaysOnTop -caption +border
Gui, 12: Color, 000000
Gui, 12: Font, cWhite s14, Arial
Gui, 12: Add, Text, x0 y10 w300 h30 center, ---------- INFO ----------
Gui, 12: Add, Text, vPreference_confirm_text1 x0 y45 w300 h50 center,
Gui, 12: Add, Button, vPreference_confirm_button1 gPreference_confirm x110 y125 w80 h30 +default, Ok
Gui, 12: Add, Text, x0 y0 w300 h170 0x12

If (New_Preference_Name = "")
{
GuiControl, 12: text, Preference_confirm_text1, Field cannot be blank
Gui, 12: Show, x287.5 y273.75 h170 w300, Info
}else If (New_Preference_Name = "None")
{
GuiControl, 12: text, Preference_confirm_text1, Preset cannot be named`n"None"
Gui, 12: Show, x287.5 y273.75 h170 w300, Info
}else If (Add_New_Preference_Check != "ERROR")
{
GuiControl, 12: text, Preference_confirm_text1, Preset already added
Gui, 12: Show, x287.5 y273.75 h170 w300, Info
}
else 
{
IniWrite, %New_Preference_checked1%,%A_ScriptDir%\Settings\Preferences.ini, %New_Preference_Name%|,Checked1
IniWrite, %New_Preference_checked2%,%A_ScriptDir%\Settings\Preferences.ini, %New_Preference_Name%|,Checked2
IniWrite, %New_Preference_checked3%,%A_ScriptDir%\Settings\Preferences.ini, %New_Preference_Name%|,Checked3
IniWrite, %New_Preference_checked4%,%A_ScriptDir%\Settings\Preferences.ini, %New_Preference_Name%|,Checked4
IniWrite, %New_Preference_Ship_User1%,%A_ScriptDir%\Settings\Preferences.ini, %New_Preference_Name%|,Ship1
IniWrite, %New_Preference_Ship_User2%,%A_ScriptDir%\Settings\Preferences.ini, %New_Preference_Name%|,Ship2
IniWrite, %New_Preference_Ship_User3%,%A_ScriptDir%\Settings\Preferences.ini, %New_Preference_Name%|,Ship3
IniWrite, %New_Preference_Ship_User4%,%A_ScriptDir%\Settings\Preferences.ini, %New_Preference_Name%|,Ship4
IniWrite, %New_Preference_Build_User1%,%A_ScriptDir%\Settings\Preferences.ini, %New_Preference_Name%|,Build1
IniWrite, %New_Preference_Build_User2%,%A_ScriptDir%\Settings\Preferences.ini, %New_Preference_Name%|,Build2
IniWrite, %New_Preference_Build_User3%,%A_ScriptDir%\Settings\Preferences.ini, %New_Preference_Name%|,Build3
IniWrite, %New_Preference_Build_User4%,%A_ScriptDir%\Settings\Preferences.ini, %New_Preference_Name%|,Build4


GuiControl, 12: text, Preference_confirm_text1, Preset "%New_Preference_Name%" added
Gui, 12: Show, x287.5 y273.75 h170 w300, Info
Preference_Added := 1
}
return


Preference_confirm:
If (Preference_Added = 1)
{
Preference_Added := 0
Gui, 9: -Disabled
Gui, 12: destroy
goto, Edit_Preferences_Gui_Button
}
else
{
Gui, 9: -Disabled
Gui, 12: destroy
}
return


Exit9:
goto, Edit_Preferences_Gui_Button
return


;--------------------------------------------------Delete Preference--------------------------------------------------


Delete_Preference:
Gui, 2:Submit, nohide
If (Mode != "")
{
StringReplace, Mode,Mode, `n,, All
Gui, 2: +Disabled
Gui, 15: +AlwaysOnTop -caption +border
Gui, 15: Color, 000000
Gui, 15: Font, cRed s14, Arial
Gui, 15: Add, Text, x0 y10 w300 h30 center, --------- WARNING ---------
Gui, 15: Font, cWhite s14, Arial
Gui, 15: Add, Text, vDelete_Preference_Text1 x5 y40 w290 center, Do you really want to delete`npreset "%Mode%"?
Gui, 15: Add, Button, vDelete_Preference_Button2 gDelete_Preference_No x170 y125 w80 h30 +default, NO
Gui, 15: Add, Button, vDelete_Preference_Button1 gDelete_Preference_Yes x50 y125 w80 h30, YES
Gui, 15: Add, Text, x0 y0 w300 h170 0x12
Gui, 15: Show, x287.5 y273.75 h170 w300, WARNING
}
return

Delete_Preference_Yes:
IniDelete, %A_ScriptDir%\Settings\Preferences.ini, %Mode%|
GuiControl, 15: text, Delete_Preference_Text1, "%Mode%" deleted
GuiControl, 15: hide, Delete_Preference_Button1
GuiControl, 15: hide, Delete_Preference_Button2

Gui, 15: Add, Button, vDelete_Preference_Button3 gDelete_Preference_Ok x110 y125 w80 h30 +default, Ok
return

Delete_Preference_OK:
IniRead,Preferences,%A_ScriptDir%\Settings\Preferences.ini
StringTrimLeft, Preferences, Preferences, 5
IniRead,FullShipList,%A_ScriptDir%\Settings\ShipList.ini
StringReplace, FullShipList,FullShipList, `n,, All
GuiControl, 2:, Mode, |%Preferences%
GuiControl, 2: choose, Mode, 1
Gosub, Load_ini
Gui, 2: -Disabled
Gui, 15: destroy
return

Delete_Preference_No:
Gui, 2: -Disabled
Gui, 15: destroy
return

;--------------------------------------------------Rename Preference--------------------------------------------------


Rename_Preference_Gui:
Gui, 2:Submit, nohide
If (Mode != "")
{
StringReplace, Mode,Mode, `n,, All
Gui, 2: +Disabled
Gui, 14: +AlwaysOnTop -caption +border
Gui, 14: Color, 000000
Gui, 14: Font, cWhite s14, Arial
Gui, 14: Add, Text, x0 y10 w300 h30 center, ---------- INFO ----------
Gui, 14: Add, Text, vRename_Preference_Text1 x10 y40 w280 h25 center, Rename: "%Mode%"
Gui, 14: Font, cBlack s14, Arial
Gui, 14: Add, edit, vRename_Preference_New_Name x40 y75 w220 h30 center,%Mode%
Gui, 14: Font, cWhite s14, Arial
Gui, 14: Add, Button, gRename_Preference_Save x65 y125 w80 h30 +default, Save
Gui, 14: Add, Button, gRename_Preference_Cancel x155 y125 w80 h30, Cancel
Gui, 14: Add, Text, x0 y0 w300 h170 0x12
Gui, 14: Show, x287.5 y273.75 h170 w300, Info
}
return

Rename_Preference_Save:
Gui,2:Submit, nohide
Gui,14:Submit, nohide
StringReplace, Mode,Mode, `n,, All
Rename_Preference_New_Name := regexreplace(Rename_Preference_New_Name, "^\s+") ;trim beginning whitespace
Rename_Preference_New_Name := regexreplace(Rename_Preference_New_Name, "\s+$") ;trim ending whitespace
GuiControl, 12: , Rename_Preference_New_Name, %Rename_Preference_New_Name%
IniRead,Rename_Preference_New_Name_Check,%A_ScriptDir%\Settings\Preferences.ini, %Rename_Preference_New_Name%|


If (Rename_Preference_New_Name = "")
{
GuiControl, 14: Text, Rename_Preference_Text1, Field cannot be blank
SetTimer, Timer_Rename_Preference_Text, -3000
}else if (Rename_Preference_New_Name = "None")
{
GuiControl, 14: Text, Rename_Preference_Text1, Preset cannot be named:
SetTimer, Timer_Rename_Preference_Text, -3000
}else If (!Rename_Preference_New_Name_Check)
{

filePath = Settings\Preferences.ini
newData := replaceLabel(Mode "|", Rename_Preference_New_Name "|", filePath)

GuiControl, 14: Text, Rename_Preference_Text1, Preset name changed
Gui, 2: -Disabled
IniRead,Preferences,%A_ScriptDir%\Settings\Preferences.ini
StringTrimLeft, Preferences, Preferences, 5
IniRead,FullShipList,%A_ScriptDir%\Settings\ShipList.ini
StringReplace, FullShipList,FullShipList, `n,, All
GuiControl, 2:, Mode, |%Preferences%
GuiControl, 2: choose, Mode, 1
Gui, 14: destroy
}
else
{
GuiControl, 14: Text, Rename_Preference_Text1, Preset already exists
SetTimer, Timer_Rename_Preference_Text, -3000
}
gosub, load_ini
return


Timer_Rename_Preference_Text:
StringReplace, Mode,Mode, `n,, All
GuiControl, 14: Text, Rename_Preference_Text1, Rename: "%Mode%"
return


Rename_Preference_Cancel:
Gui, 2: -Disabled
Gui, 14: destroy
return


;--------------------------------------------------Show Ship Settings--------------------------------------------------

Show_Ship_Stats_Gui_Button:
Gui, 1:Submit, nohide
IniWrite,%Ship1_checked%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Checked1
IniWrite,%Ship2_checked%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Checked2
IniWrite,%Ship3_checked%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Checked3
IniWrite,%Ship4_checked%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Checked4 
IniWrite,%Ship1%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Ship1
IniWrite,%Ship2%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Ship2
IniWrite,%Ship3%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Ship3
IniWrite,%Ship4%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Ship4 
IniWrite,%Builds_Ship1_selected%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Build1
IniWrite,%Builds_Ship2_selected%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Build2
IniWrite,%Builds_Ship3_selected%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Build3
IniWrite,%Builds_Ship4_selected%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Build4
IniWrite,%Unequip_Ships_checked%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Unequip

Show_Ship_Stats_Gui:
Gui, 13: show
IniRead,FullShipList,%A_ScriptDir%\Settings\ShipList.ini
StringReplace, FullShipList,FullShipList, `n,, All

Gui, 3: +AlwaysOnTop +Toolwindow
Gui, 3: Color, 000000
Gui, 3: Font, cWhite s12, Arial

Gui, 3: Add, Text, x0 y10 w590 center, -------------------- View Ship Settings --------------------


Gui, 3: Add, DDL, vEdit_Loadout_Ship_selected gLoad_Ship_stats x235 y55 w130 sort, %FullShipList%
Gui, 3: Add, Button, gAdd_New_Ship_Gui x375 y53 w30 h30, +
Gui, 3: Add, Button, gDelete_Ship x415 y53 w30 h30, -
Gui, 3: Add, Button, gRename_Ship_Gui x455 y53 h30, Rename


Gui, 3: Add, Text, x30 y120 w257 center, Settings:
Gui, 3: Add, Text, x113 y140 w90 0x10 ;White Line
Gui, 3: Add, Text, x45 y150 w110 right, Faction:
Gui, 3: Add, Text, x45 y180 w110 right, Coordinates:
Gui, 3: Add, Text, vDisplay_Faction x165 y150 w120,
Gui, 3: Add, Text, vDisplay_X x165 y180 w120, X
Gui, 3: Add, Text, vDisplay_Y x165 y200 w120, Y
Gui, 3: Add, Text, x45 y230 w110 right, Scroll 1:
Gui, 3: Add, Text, x45 y260 w110 right, Scroll 2:
Gui, 3: Add, Text, vDisplay_Scroll1 x165 y230 w120,
Gui, 3: Add, Text, vDisplay_Scroll2 x165 y260 w120,
Gui, 3: Add, Text, x30 y110 w257 0x10 ;White Line
Gui, 3: Add, Text, x30 y111 h230 0x11 ;White Line
Gui, 3: Add, Text, x30 y340 w257 0x10 ;White Line
Gui, 3: Add, Text, x285 y111 h230 0x11 ;White Line
Gui, 3: Add, Button, gEdit_Ship_Gui x230 y120 w45 h25, Edit


Gui, 3: Add, Text, x315 y120 w257 h30 center, Loadouts:
Gui, 3: Add, Text, x395 y140 w100 0x10 ;White Line
Gui, 3: Add, Text, vDisplay_Loadouts x370 y150 w150 h160 center, 
Gui, 3: Add, Text, x315 y110 w257 0x10 ;White Line
Gui, 3: Add, Text, x315 y111 h230 0x11 ;White Line
Gui, 3: Add, Text, x315 y340 w257 0x10 ;White Line
Gui, 3: Add, Text, x570 y111 h230 0x11 ;White Line
Gui, 3: Add, Button, gEdit_Loadout_Gui x515 y120 w45 h25, Edit


Gui, 3: Font, cWhite s9, Arial
Gui, 3: Add, Button, gExit3 x500 y360 w80 h20, Back


Gui, 13: hide
Gui, 3: Show, x100 y100 h400 w600, Loadouts
Gui, 1: destroy
Gui, 4: destroy
Gui, 5: destroy
Gui, 6: destroy


if (Add_New_Ship_Ship != "")
{
GuiControl, 3: choose, Edit_Loadout_Ship_selected, %Add_New_Ship_Ship%
Add_New_Ship_Ship := ""
}else if (Edit_Loadout_Ship_selected != "")
{
GuiControl, 3: choose, Edit_Loadout_Ship_selected, %Edit_Loadout_Ship_selected%
}
else
{
GuiControl, 3: choose, Edit_Loadout_Ship_selected, None
}

Load_Ship_stats:
Gui, 3:Submit, nohide
Iniread, Edit_Loadout_List, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini
StringReplace, Edit_Loadout_Ship_selected,Edit_Loadout_Ship_selected, `n,, All
StringReplace, Edit_Loadout_List,Edit_Loadout_List, `n,, All

Iniread, Ship_X, %A_ScriptDir%\Settings\ShipList.ini,%Edit_Loadout_Ship_selected%|,x
Iniread, Ship_Y, %A_ScriptDir%\Settings\ShipList.ini,%Edit_Loadout_Ship_selected%|,y
Iniread, Ship_X_ellydium, %A_ScriptDir%\Settings\ShipList.ini,%Edit_Loadout_Ship_selected%|,x_ellydium
Iniread, Ship_Y_ellydium, %A_ScriptDir%\Settings\ShipList.ini,%Edit_Loadout_Ship_selected%|,y_ellydium
Iniread, Ship_Scroll, %A_ScriptDir%\Settings\ShipList.ini,%Edit_Loadout_Ship_selected%|,Scroll
Iniread, Ship_Scroll_amount, %A_ScriptDir%\Settings\ShipList.ini,%Edit_Loadout_Ship_selected%|,Scroll_amount
Iniread, Ship_Scroll2, %A_ScriptDir%\Settings\ShipList.ini,%Edit_Loadout_Ship_selected%|,Scroll2
Iniread, Ship_Scroll_amount2, %A_ScriptDir%\Settings\ShipList.ini,%Edit_Loadout_Ship_selected%|,Scroll_amount2
Iniread, Ship_Faction, %A_ScriptDir%\Settings\ShipList.ini,%Edit_Loadout_Ship_selected%|,Faction

StringTrimLeft, Ship_Scroll, Ship_Scroll, 5
StringTrimLeft, Ship_Scroll2, Ship_Scroll2, 5


if Ship_Scroll_amount = ERROR
{
Ship_Scroll_amount := ""
}


if Ship_Scroll_amount2 = ERROR
{
Ship_Scroll_amount2 := ""
}

StringReplace, Display_Loadouts, Edit_Loadout_List, None| , , All
StringReplace, Display_Loadouts, Display_Loadouts, | , `n, All
If !Display_Loadouts
{
GuiControl, 3: text, Display_Loadouts, None
}
else
{
GuiControl, 3: text, Display_Loadouts, %Display_Loadouts%
}

if (Ship_Faction != "None")
{
GuiControl, 3: text, Display_Faction, %Ship_Faction%
}
else
{
GuiControl, 3: text, Display_Faction, 
}

if (Ship_X != "None")
{
GuiControl, 3: text, Display_X, X %Ship_X%
}
else
{
GuiControl, 3: text, Display_X, X
}

if (Ship_Y != "None")
{
GuiControl, 3: text, Display_Y, Y %Ship_Y%
}
else
{
GuiControl, 3: text, Display_Y, Y
}

GuiControl, 3: text, Display_Scroll1, %Ship_Scroll% %Ship_Scroll_amount%
GuiControl, 3: text, Display_Scroll2, %Ship_Scroll2% %Ship_Scroll_amount2%

return





Delete_Ship:
Gui, 3:Submit, nohide
If (Edit_Loadout_Ship_selected != "None")
{
Gui, 3: +Disabled
Gui, 10: +AlwaysOnTop -caption
Gui, 10: Color, 000000
Gui, 10: Font, cRed s14, Arial
Gui, 10: Add, Text, x0 y10 w300 h30 center, --------- WARNING ---------
Gui, 10: Font, cWhite s14, Arial
Gui, 10: Add, Text, x0 y0 w300 h170 0x12

Gui, 10: Add, Text, vDelete_Ship_Text1 x5 y40 w290 center, Do you really want to delete`nthe settings and loadouts`nfrom "%Edit_Loadout_Ship_selected%"?
Gui, 10: Add, Button, vDelete_Ship_Button2 gDelete_Ship_No x170 y125 w80 h30 +default, NO
Gui, 10: Add, Button, vDelete_Ship_Button1 gDelete_Ship_Yes x50 y125 w80 h30, YES
Gui, 10: Add, Text, x0 y0 w300 h170 0x12
Gui, 10: Show, x287.5 y273.75 h170 w300, WARNING
}
return

Delete_Ship_Yes:
FileDelete, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini
IniDelete, %A_ScriptDir%\Settings\ShipList.ini, %Edit_Loadout_Ship_selected%|
GuiControl, 10: text, Delete_Ship_Text1, "%Edit_Loadout_Ship_selected%" deleted
GuiControl, 10: hide, Delete_Ship_Button1
GuiControl, 10: hide, Delete_Ship_Button2
GuiControl, 10: disable, Delete_Ship_Button1
GuiControl, 10: disable, Delete_Ship_Button2
Gui, 10: Add, Button, vDelete_Ship_Button3 gDelete_Ship_OK x110 y125 w80 h30 +default, Ok
return


Delete_Ship_OK:
IniRead,FullShipList,%A_ScriptDir%\Settings\ShipList.ini
StringReplace, FullShipList,FullShipList, `n,, All
GuiControl, 3:, Edit_Loadout_Ship_selected, |%FullShipList%
GuiControl, 3: choose, Edit_Loadout_Ship_selected, None
Gosub, Load_Ship_stats
Gui, 3: -Disabled
Gui, 10: destroy
return


Delete_Ship_No:
Gui, 3: -Disabled
Gui, 10: destroy
return


Exit3:
goto, Gui_Start
return


;--------------------------------------------------Rename Ship--------------------------------------------------


Rename_Ship_Gui:
Gui, 3:Submit, nohide
If (Edit_Loadout_Ship_selected != "None")
{
Gui, 3: +Disabled
Gui, 12: +AlwaysOnTop -caption +border
Gui, 12: Color, 000000
Gui, 12: Font, cWhite s14, Arial
Gui, 12: Add, Text, x0 y10 w300 h30 center, ---------- INFO ----------
Gui, 12: Add, Text, vRename_Ship_Text1 x10 y40 w280 h25 center, Rename: "%Edit_Loadout_Ship_selected%"
Gui, 12: Font, cBlack s14, Arial
Gui, 12: Add, edit, vRename_Ship_New_Name x40 y75 w220 h30 center,%Edit_Loadout_Ship_selected%
Gui, 12: Font, cWhite s14, Arial
Gui, 12: Add, Button, gRename_Ship_Save x65 y125 w80 h30 +default, Save
Gui, 12: Add, Button, gRename_Ship_Cancel x155 y125 w80 h30, Cancel
Gui, 12: Add, Text, x0 y0 w300 h170 0x12
Gui, 12: Show, x287.5 y273.75 h170 w300, Info
return

Rename_Ship_Save:
Gui,3:Submit, nohide
Gui,12:Submit, nohide
Rename_Ship_New_Name := regexreplace(Rename_Ship_New_Name, "^\s+") ;trim beginning whitespace
Rename_Ship_New_Name := regexreplace(Rename_Ship_New_Name, "\s+$") ;trim ending whitespace
GuiControl, 12: , Rename_Ship_New_Name, %Rename_Ship_New_Name%
IniRead,Rename_Ship_New_Name_Check,%A_ScriptDir%\Settings\ShipList.ini, %Rename_Ship_New_Name%|


If (Rename_Ship_New_Name = "")
{
GuiControl, 12: Text, Rename_Ship_Text1, Field cannot be blank
SetTimer, Timer_Rename_Ship_Text, -3000
}else if (Rename_Ship_New_Name = "None")
{
GuiControl, 12: Text, Rename_Ship_Text1, Ship cannot be named:
SetTimer, Timer_Rename_Ship_Text, -3000
}else If (!Rename_Ship_New_Name_Check)
{

filePath = Settings\ShipList.ini
newData := replaceLabel(Edit_Loadout_Ship_selected "|", Rename_Ship_New_Name "|", filePath)
FileMove, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %A_ScriptDir%\Builds\%Rename_Ship_New_Name%.ini

GuiControl, 12: Text, Rename_Ship_Text1, Ship name changed
Gui, 3: -Disabled
Iniread, FullShipList, %A_ScriptDir%\Settings\ShipList.ini
StringReplace, FullShipList,FullShipList, `n,, All
GuiControl, 3: , Edit_Loadout_Ship_selected, |%FullShipList%
GuiControl, 3: chooseString, Edit_Loadout_Ship_selected, %Rename_Ship_New_Name%
Gui, 12: destroy
return
}
else
{
GuiControl, 12: Text, Rename_Ship_Text1, Ship already exists
SetTimer, Timer_Rename_Ship_Text, -3000
}
return


Timer_Rename_Ship_Text:
GuiControl, 12: Text, Rename_Ship_Text1, Rename: "%Edit_Loadout_Ship_selected%"
return


Rename_Ship_Cancel:
Gui, 3: -Disabled
Gui, 12: destroy
return

}
else
{
}
return


;--------------------------------------------------Add New Ships--------------------------------------------------

Add_New_Ship_Gui:
Gui, 13: show
IniRead,FullShipList,%A_ScriptDir%\Settings\ShipList.ini
StringReplace, FullShipList,FullShipList, `n,, All


Gui, 4: +AlwaysOnTop +Toolwindow
Gui, 4: Color, 000000
Gui, 4: Font, cWhite s12, Arial


Gui, 4: Add, Text, x0 y10 w600 h30 center, -------------------- Add New Ship --------------------


Gui, 4: Add, Text, x55 y84 w130 h30 right, New Ship:
Gui, 4: Add, Text, x55 y123 w130 h30 right, Faction:
Gui, 4: Add, Text, x46 y159 w140 h30 right, Coordinates X:
Gui, 4: Add, Text, x290 y159 w20 h30 right, Y:
Gui, 4: Add, Text, x55 y198 w130 h30 right, Scroll 1:
Gui, 4: Add, Text, x55 y233 w130 h30 right, Scroll 2:
Gui, 4: Add, Text, x405 y198 w130 h30, Times
Gui, 4: Add, Text, x405 y233 w130 h30, Times
Gui, 4: Add, Text, x46 y270 w140 h30 right hidden vEllydium_New_text1, Build X:
Gui, 4: Add, Text, x290 y270 w20 h30 right hidden vEllydium_New_text2, Y:


Gui, 4: Font, cBlack s12, Arial
Gui, 4: Add, Edit, vAdd_New_Ship_Ship x200 y80 w200 h30,
Gui, 4: Add, DDL, vAdd_New_Ship_Faction gFactionChangedNewShip x200 y120 w200 choose1, Empire|Federation|Jericho|Ellydium|Unique
Gui, 4: Add, Edit, vAdd_New_Ship_X x200 y155 w80 h30 number,
Gui, 4: Add, Edit, vAdd_New_Ship_Y x320 y155 w80 h30 number,
Gui, 4: Add, Button, gAuto_Coordinates_Start x410 y156 h28, Click
Gui, 4: Add, Edit, vAdd_New_Ship_X_Ellydium x200 y265 w80 h30 number hidden,
Gui, 4: Add, Edit, vAdd_New_Ship_Y_Ellydium x320 y265 w80 h30 number hidden,
Gui, 4: Add, Button, gAuto_Coordiantes_Start_Ellydium vEllydium_New_Button x410 y266 h28 hidden, Click


Gui, 4: Add, DDL, vAdd_New_Ship_Scroll x200 y195 w80 choose3, |Up|Down
Gui, 4: Add, Edit, vAdd_New_Ship_Scroll_amount x320 y196 w80 h25 number, 110
Gui, 4: Add, DDL, vAdd_New_Ship_Scroll2 x200 y230 w80 choose1, |Up|Down
Gui, 4: Add, Edit, vAdd_New_Ship_Scroll_amount2 x320 y231 w80 h25 number,
Gui, 4: Add, Button, gNew_Ship x205 y305 w190 h25, Add


Gui, 4: Font, cWhite s9, Arial
Gui, 4: Add, Button, gExit4 x500 y360 w80 h20, Back

Gui, 4: Add, Text, x10 y360 w300 h30, Rightclick: Transfer scroll value`nMousewheel click: Reset scroll counter

Gui, 13: hide
Gui, 4: Show, x100 y100 h400 w600, Add New Ship
Gui, 3: destroy

Hotkey, RButton, On
Hotkey, WheelUp, On
Hotkey, WheelDown, On
return




New_Ship:
Gui, 4:Submit, nohide
IniRead,Add_New_Ship_Check,%A_ScriptDir%\Settings\ShipList.ini,%Add_New_Ship_Ship%|,Faction
Add_New_Ship_Ship := regexreplace(Add_New_Ship_Ship, "^\s+") ;trim beginning whitespace
Add_New_Ship_Ship := regexreplace(Add_New_Ship_Ship, "\s+$") ;trim ending whitespace
GuiControl, 4: , Add_New_Ship_Ship, %Add_New_Ship_Ship%

Gui, 4: +Disabled
Gui, 12: +AlwaysOnTop -caption +border
Gui, 12: Color, 000000
Gui, 12: Font, cWhite s14, Arial
Gui, 12: Add, Text, x0 y10 w300 h30 center, ---------- INFO ----------
Gui, 12: Add, Text, vShip_confirm_text1 x0 y45 w300 h50 center,
Gui, 12: Add, Button, vShip_confirm_button1 gShip_confirm x110 y125 w80 h30 +default, Ok
Gui, 12: Add, Text, x0 y0 w300 h170 0x12

If (Add_New_Ship_Ship = "")
{
GuiControl, 12: text, Ship_confirm_text1, Field cannot be blank
Gui, 12: Show, x287.5 y273.75 h170 w300, Info
}else If (Add_New_Ship_Ship = "None")
{
GuiControl, 12: text, Ship_confirm_text1, Ship cannot be named`n"None"
Gui, 12: Show, x287.5 y273.75 h170 w300, Info
}else If (Add_New_Ship_Check != "ERROR")
{
GuiControl, 12: text, Ship_confirm_text1, Ship already added
Gui, 12: Show, x287.5 y273.75 h170 w300, Info
}
else 
{
IniWrite, %Add_New_Ship_Faction%,%A_ScriptDir%\Settings\ShipList.ini, %Add_New_Ship_Ship%|,Faction
IniWrite, %Add_New_Ship_X%,%A_ScriptDir%\Settings\ShipList.ini, %Add_New_Ship_Ship%|,x
IniWrite, %Add_New_Ship_Y%,%A_ScriptDir%\Settings\ShipList.ini, %Add_New_Ship_Ship%|,y
IniWrite, %Add_New_Ship_Scroll_amount%,%A_ScriptDir%\Settings\ShipList.ini, %Add_New_Ship_Ship%|,Scroll_amount
IniWrite, %Add_New_Ship_Scroll_amount2%,%A_ScriptDir%\Settings\ShipList.ini, %Add_New_Ship_Ship%|,Scroll_amount2

If (Add_New_Ship_Faction = "Ellydium")
{
IniWrite, %Add_New_Ship_X_ellydium%,%A_ScriptDir%\Settings\ShipList.ini, %Add_New_Ship_Ship%|,x_ellydium
IniWrite, %Add_New_Ship_Y_ellydium%,%A_ScriptDir%\Settings\ShipList.ini, %Add_New_Ship_Ship%|,y_ellydium
}


If (Add_New_Ship_Scroll != "")
{
IniWrite, wheel%Add_New_Ship_Scroll%,%A_ScriptDir%\Settings\ShipList.ini, %Add_New_Ship_Ship%|,Scroll
}
else
{
IniWrite, %Add_New_Ship_Scroll%,%A_ScriptDir%\Settings\ShipList.ini, %Add_New_Ship_Ship%|,Scroll
}
If (Add_New_Ship_Scroll2 != "")
{
IniWrite, wheel%Add_New_Ship_Scroll2%,%A_ScriptDir%\Settings\ShipList.ini, %Add_New_Ship_Ship%|,Scroll2
}
else
{
IniWrite, %Add_New_Ship_Scroll2%,%A_ScriptDir%\Settings\ShipList.ini, %Add_New_Ship_Ship%|,Scroll2
}

IniWrite, None, %A_ScriptDir%\Builds\%Add_New_Ship_Ship%.ini, None|, None

IniDelete, %A_ScriptDir%\Builds\%Add_New_Ship_Ship%.ini, None|, None
IniRead,FullShipList,%A_ScriptDir%\Settings\ShipList.ini
GuiControl, 12: text, Ship_confirm_text1, Ship "%Add_New_Ship_Ship%" added
Gui, 12: Show, x287.5 y273.75 h170 w300, Info
Ship_Added := 1
Hotkey, RButton, Off
Hotkey, WheelUp, Off
Hotkey, WheelDown, Off
Gosub, RemoveToolTip
}
return


Ship_confirm:
If (Ship_Added = 1)
{
Ship_Added := 0
Gui, 4: -Disabled
Gui, 12: destroy
goto, Show_Ship_Stats_Gui
}
else
{
Gui, 4: -Disabled
Gui, 12: destroy
}
return


Exit4:
Hotkey, RButton, Off
Hotkey, WheelUp, Off
Hotkey, WheelDown, Off
Gosub, RemoveToolTip
goto, Show_Ship_Stats_Gui
return

FactionChangedNewShip:
Gui, 4: Submit, nohide
If (Add_New_Ship_Faction = "Ellydium")
{
	GuiControl, 4: show, Ellydium_New_text1
	GuiControl, 4: show, Ellydium_New_text2
	GuiControl, 4: show, Add_New_Ship_X_ellydium
	GuiControl, 4: show, Add_New_Ship_Y_ellydium
	GuiControl, 4: show, Ellydium_New_Button
}
else
{
	GuiControl, 4: hide, Ellydium_New_text1
	GuiControl, 4: hide, Ellydium_New_text2
	GuiControl, 4: hide, Add_New_Ship_X_ellydium
	GuiControl, 4: hide, Add_New_Ship_Y_ellydium
	GuiControl, 4: hide, Ellydium_New_Button
}

return
;--------------------------------------------------Edit Ship Settings--------------------------------------------------


Edit_Ship_Gui:
Gui, 3:Submit, nohide
If (Edit_Loadout_Ship_selected != "None")
{ 
Gui, 13: show
Gui, 5: +AlwaysOnTop +Toolwindow
Gui, 5: Color, 000000
Gui, 5: Font, cWhite s22, Arial
Gui, 5: Add, Text, x5 y50 w590 center, %Edit_Loadout_Ship_selected%


Gui, 5: Font, cWhite s12, Arial
Gui, 5: Add, Text, x0 y10 w600 h30 center, -------------------- Edit Settings --------------------
Gui, 5: Add, Text, x55 y123 w130 h30 right, Faction:
Gui, 5: Add, Text, x46 y159 w140 h30 right, Coordinates X:
Gui, 5: Add, Text, x290 y159 w20 h30 right, Y:
Gui, 5: Add, Text, x55 y198 w130 h30 right, Scroll 1:
Gui, 5: Add, Text, x55 y233 w130 h30 right, Scroll 2:
Gui, 5: Add, Text, x405 y198 w130 h30, Times
Gui, 5: Add, Text, x405 y233 w130 h30, Times
Gui, 5: Add, Text, x46 y270 w140 h30 right hidden vEllydium_text1, Build X:
Gui, 5: Add, Text, x290 y270 w20 h30 right hidden vEllydium_text2, Y:



Gui, 5: Font, cBlack s12, Arial
Gui, 5: Add, DDL, vEdit_Ship_Faction gFactionChanged x200 y120 w200, Empire|Federation|Jericho|Ellydium|Unique
Gui, 5: Add, Edit, vEdit_Ship_X x200 y155 w80 h30 number,
Gui, 5: Add, Edit, vEdit_Ship_Y x320 y155 w80 h30 number,
Gui, 5: Add, Button, gAuto_Coordinates_Start x410 y156 h28, Click
Gui, 5: Add, Edit, vEdit_Ship_X_ellydium x200 y265 w80 h30 number hidden,
Gui, 5: Add, Edit, vEdit_Ship_Y_ellydium x320 y265 w80 h30 number hidden,
Gui, 5: Add, Button, gAuto_Coordiantes_Start_Ellydium vEllydium_Button x410 y266 h28 hidden, Click


Gui, 5: Add, DDL, vEdit_Ship_Scroll x200 y195 w80 choose1, |Up|Down
Gui, 5: Add, Edit, vEdit_Ship_Scroll_amount x320 y196 w80 h25 number,
Gui, 5: Add, DDL, vEdit_Ship_Scroll2 x200 y230 w80 choose1, |Up|Down
Gui, 5: Add, Edit, vEdit_Ship_Scroll_amount2 x320 y231 w80 h25 number,
Gui, 5: Add, Button, gSubmit_Setting_Changes x205 y305 w190 h25, Save Changes


Gui, 5: Font, cWhite s9, Arial
Gui, 5: Add, Button, gExit5 x500 y360 w80 h20, Back

Gui, 5: Add, Text, x10 y360 w300 h30, Rightclick: Transfer scroll value`nMousewheel click: Reset scroll counter

Gui, 13: hide
Gui, 5: Show, x100 y100 h400 w600, Edit
Gui, 3: destroy
Gui, 5:Submit, nohide


GuiControl, 5:, Edit_Ship_X, %Ship_X%
GuiControl, 5:, Edit_Ship_Y, %Ship_Y%
GuiControl, 5:, Edit_Ship_X_ellydium, %Ship_X_ellydium%
GuiControl, 5:, Edit_Ship_Y_ellydium, %Ship_Y_ellydium%
GuiControl, 5: choose, Edit_Ship_Faction, %Ship_Faction%
GuiControl, 5: choose, Edit_Ship_Scroll, %Ship_Scroll%
GuiControl, 5: choose, Edit_Ship_Scroll2, %Ship_Scroll2%
GuiControl, 5:, Edit_Ship_Scroll_amount, %Ship_Scroll_amount%
GuiControl, 5:, Edit_Ship_Scroll_amount2, %Ship_Scroll_amount2%

Hotkey, RButton, On
Hotkey, WheelUp, On
Hotkey, WheelDown, On
}
else
{
Gui, 3: +Disabled
Gui, 12: +AlwaysOnTop -caption +border
Gui, 12: Color, 000000
Gui, 12: Font, cWhite s14, Arial
Gui, 12: Add, Text, x0 y10 w300 h30 center, ---------- INFO ----------
Gui, 12: Add, Text, vShip_confirm_text1 x0 y45 w300 h50 center, No Ship selected
Gui, 12: Add, Button, vShip_confirm_button1 gEdit_confirm x110 y125 w80 h30 +default, Ok
Gui, 12: Add, Text, x0 y0 w300 h170 0x12
Gui, 12: Show, x287.5 y273.75 h170 w300, Info
}

gosub, FactionChanged
return

Edit_confirm:
Gui, 3: -Disabled
Gui, 12: Destroy
return



Submit_Setting_Changes:
Gui, 5:Submit, nohide
Gui, 5: +Disabled
IniWrite, %Edit_Ship_Faction%,%A_ScriptDir%\Settings\ShipList.ini, %Edit_Loadout_Ship_selected%|,Faction
IniWrite, %Edit_Ship_X%,%A_ScriptDir%\Settings\ShipList.ini, %Edit_Loadout_Ship_selected%|,x
IniWrite, %Edit_Ship_Y%,%A_ScriptDir%\Settings\ShipList.ini, %Edit_Loadout_Ship_selected%|,y
IniWrite, %Edit_Ship_Scroll_amount%,%A_ScriptDir%\Settings\ShipList.ini, %Edit_Loadout_Ship_selected%|,Scroll_amount
IniWrite, %Edit_Ship_Scroll_amount2%,%A_ScriptDir%\Settings\ShipList.ini, %Edit_Loadout_Ship_selected%|,Scroll_amount2

If (Edit_Ship_Faction = "Ellydium")
{
IniWrite, %Edit_Ship_X_ellydium%,%A_ScriptDir%\Settings\ShipList.ini, %Edit_Loadout_Ship_selected%|,x_ellydium
IniWrite, %Edit_Ship_Y_ellydium%,%A_ScriptDir%\Settings\ShipList.ini, %Edit_Loadout_Ship_selected%|,y_ellydium
}
else
{
IniDelete, %A_ScriptDir%\Settings\ShipList.ini, %Edit_Loadout_Ship_selected%|,x_ellydium
IniDelete, %A_ScriptDir%\Settings\ShipList.ini, %Edit_Loadout_Ship_selected%|,y_ellydium
}


If (Edit_Ship_Scroll != "")
{
IniWrite, wheel%Edit_Ship_Scroll%,%A_ScriptDir%\Settings\ShipList.ini, %Edit_Loadout_Ship_selected%|,Scroll
}
else
{
IniWrite, %Edit_Ship_Scroll%,%A_ScriptDir%\Settings\ShipList.ini, %Edit_Loadout_Ship_selected%|,Scroll
}

If (Edit_Ship_Scroll2 != "")
{
IniWrite, wheel%Edit_Ship_Scroll2%,%A_ScriptDir%\Settings\ShipList.ini, %Edit_Loadout_Ship_selected%|,Scroll2
}
else
{
IniWrite, %Edit_Ship_Scroll2%,%A_ScriptDir%\Settings\ShipList.ini, %Edit_Loadout_Ship_selected%|,Scroll2
}
Gui, 5: +Disabled
Gui, 12: +AlwaysOnTop -caption +border
Gui, 12: Color, 000000
Gui, 12: Font, cWhite s14, Arial
Gui, 12: Add, Text, x0 y10 w300 h30 center, ---------- INFO ----------
Gui, 12: Add, Text, vShip_confirm_text1 x0 y45 w300 h50 center, Settings Saved
Gui, 12: Add, Button, vShip_confirm_button1 gSettings_saved_confirm x110 y125 w80 h30 +default, Ok
Gui, 12: Add, Text, x0 y0 w300 h170 0x12
Gui, 12: Show, x287.5 y273.75 h170 w300, Info

Hotkey, RButton, Off
Hotkey, WheelUp, Off
Hotkey, WheelDown, Off
Gosub, RemoveToolTip
return

Settings_saved_confirm:
Gui, 5: -Disabled
Gui, 12: destroy
goto, Show_Ship_Stats_Gui
return

Exit5:
Hotkey, RButton, Off
Hotkey, WheelUp, Off
Hotkey, WheelDown, Off
Gosub, RemoveToolTip
goto, Show_Ship_Stats_Gui
return

FactionChanged:
Gui, 5: Submit, nohide
If (Edit_Ship_Faction = "Ellydium")
{
	GuiControl, 5: show, Ellydium_text1
	GuiControl, 5: show, Ellydium_text2
	GuiControl, 5: show, Edit_Ship_X_ellydium
	GuiControl, 5: show, Edit_Ship_Y_ellydium
	GuiControl, 5: show, Ellydium_Button
}
else
{
	GuiControl, 5: hide, Ellydium_text1
	GuiControl, 5: hide, Ellydium_text2
	GuiControl, 5: hide, Edit_Ship_X_ellydium
	GuiControl, 5: hide, Edit_Ship_Y_ellydium
	GuiControl, 5: hide, Ellydium_Button
}

return

;--------------------------------------------------Edit Ship Loadouts--------------------------------------------------


Edit_Loadout_Gui:
Gui, 3:Submit, nohide
If (Edit_Loadout_Ship_selected != "None")
{ 
Gui, 13: show
Iniread, Edit_Loadout_List, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini
StringReplace, Edit_Loadout_Ship_selected,Edit_Loadout_Ship_selected, `n,, All
StringReplace, Edit_Loadout_List,Edit_Loadout_List, `n,, All


Gui, 6: +AlwaysOnTop +Toolwindow
Gui, 6: Color, 000000
Gui, 6: Font, cWhite s22, Arial
Gui, 6: Add, Text, x5 y40 w590 center, %Edit_Loadout_Ship_selected%


Gui, 6: Font, cWhite s12, Arial
Gui, 6: Add, Text, x0 y10 w600 h30 center, -------------------- Edit Loadouts --------------------


Gui, 6: Add, Text, x95 y100 w130 h30 right, Loadout:
Gui, 6: Add, Text, x130 y160 w130 h30 right, Preset:


Gui, 6: Font, cBlack s12, Arial
Gui, 6: Add, DDL, vEdit_Loadout_Loadout_selected gLoad_Loadout x235 y95 w130 Choose1 , %Edit_Loadout_List%
Gui, 6: Add, Button, gAdd_New_Loadout_Gui x375 y93 w30 h30, +
Gui, 6: Add, Button, gDelete_Loadout x415 y93 w30 h30, -
Gui, 6: Add, Button, gRename_Loadout_Gui x455 y93 h30, Rename

if (New_Loadout_Name != "")
{
GuiControl, 6: chooseString, Edit_Loadout_Loadout_selected, %New_Loadout_Name%
New_Loadout_Name := ""
}
else
{
GuiControl, 6: chooseString, Edit_Loadout_Loadout_selected, None
} 

Gui, 6: Font, cWhite s16, Arial
Gui, 6: Add, DDL, vEdit_Preset x270 y153 w50 Choose1 center, |1|2|3|4|


if (Ship_Faction = "Ellydium")
{
	Gui, 6: Font, cBlack s12, Arial
	Gui, 6: Add, Button, gEdit_Ellydium_tree x370 y153 w100, Ellydium Tree
	Gui, 6: Add, Button, gSetup_Ellydium x480 y153 w60, Setup
	Gui, 6: Font, cWhite s10, Arial
	Gui, 6: Add, Text, vTree_active_text x370 y190 w200 h30 left, Ellydium Tree active: 
	
}


Gui, 6: Font, cWhite s16, Arial
Gui, 6: Add, Text, x255 y200 w80 h30 center, Crew
Gui, 6: Font, cWhite s16, Arial
Gui, 6: Add, Text, x20 y230 w550 0x10 ;White Line


Gui, 6: Font, cWhite s16, Arial
Gui, 6: Add, Text, x19 y240 center, 1
Gui, 6: Add, Text, x53 y240 center, 2
Gui, 6: Add, Text, x92 y240 center, 3
Gui, 6: Add, Text, x130 y240 center, 4
Gui, 6: Add, Text, x168 y240 center, 5
Gui, 6: Add, Text, x208 y240 center, 6
Gui, 6: Add, Text, x248 y240 center, 7
Gui, 6: Add, Text, x285 y240 center, 8
Gui, 6: Add, Text, x323 y240 center, 9
Gui, 6: Add, Text, x357 y240 center, 10
Gui, 6: Add, Text, x400 y240 center, 11
Gui, 6: Add, Text, x434 y240 center, 12
Gui, 6: Add, Text, x472 y240 center, 13
Gui, 6: Add, Text, x511 y240 center, 14
Gui, 6: Add, Text, x549 y240 center, 15

Gui, 6: Add, Text, x25 y270 h15 0x11 ;White Line
Gui, 6: Add, Text, x63.57 y270 h15 0x11 ;White Line
Gui, 6: Add, Text, x102.14 y270 h15 0x11 ;White Line
Gui, 6: Add, Text, x140.71 y270 h15 0x11 ;White Line
Gui, 6: Add, Text, x179.28 y270 h15 0x11 ;White Line
Gui, 6: Add, Text, x217.85 y270 h15 0x11 ;White Line
Gui, 6: Add, Text, x256.42 y270 h15 0x11 ;White Line
Gui, 6: Add, Text, x294.99 y270 h15 0x11 ;White Line
Gui, 6: Add, Text, x333.56 y270 h15 0x11 ;White Line
Gui, 6: Add, Text, x372.13 y270 h15 0x11 ;White Line
Gui, 6: Add, Text, x410.7 y270 h15 0x11 ;White Line
Gui, 6: Add, Text, x449.27 y270 h15 0x11 ;White Line
Gui, 6: Add, Text, x487.84 y270 h15 0x11 ;White Line
Gui, 6: Add, Text, x526.41 y270 h15 0x11 ;White Line
Gui, 6: Add, Text, x564.98 y270 h15 0x11 ;White Line

Gui, 6: Font, cBlack s16, Arial
Gui, 6: Add, Edit, vEdit_Crew1 gCheck_Number1 x10 y300 w30 h30 +center +number limit1, 
Gui, 6: Add, Edit, vEdit_Crew2 gCheck_Number2 x48.57 y300 w30 h30 +center +number limit1, 
Gui, 6: Add, Edit, vEdit_Crew3 gCheck_Number3 x87.14 y300 w30 h30 +center +number limit1, 
Gui, 6: Add, Edit, vEdit_Crew4 gCheck_Number4 x125.71 y300 w30 h30 +center +number limit1, 
Gui, 6: Add, Edit, vEdit_Crew5 gCheck_Number5 x164.28 y300 w30 h30 +center +number limit1, 
Gui, 6: Add, Edit, vEdit_Crew6 gCheck_Number6 x202.85 y300 w30 h30 +center +number limit1, 
Gui, 6: Add, Edit, vEdit_Crew7 gCheck_Number7 x241.42 y300 w30 h30 +center +number limit1, 
Gui, 6: Add, Edit, vEdit_Crew8 gCheck_Number8 x279.99 y300 w30 h30 +center +number limit1, 
Gui, 6: Add, Edit, vEdit_Crew9 gCheck_Number9 x318.56 y300 w30 h30 +center +number limit1, 
Gui, 6: Add, Edit, vEdit_Crew10 gCheck_Number10 x357.13 y300 w30 h30 +center +number limit1, 
Gui, 6: Add, Edit, vEdit_Crew11 gCheck_Number11 x395.7 y300 w30 h30 +center +number limit1, 
Gui, 6: Add, Edit, vEdit_Crew12 gCheck_Number12 x434.27 y300 w30 h30 +center +number limit1, 
Gui, 6: Add, Edit, vEdit_Crew13 gCheck_Number13 x472.84 y300 w30 h30 +center +number limit1, 
Gui, 6: Add, Edit, vEdit_Crew14 gCheck_Number14 x511.41 y300 w30 h30 +center +number limit1, 
Gui, 6: Add, Edit, vEdit_Crew15 gCheck_Number15 x549.98 y300 w30 h30 +center +number limit1, 


Gui, 6: Add, Button, gSave_Loadout x255 y350 w80 h30, Save


Gui, 6: Font, cWhite s9, Arial
Gui, 6: Add, Button, gExit6 x500 y360 w80 h20, Back


Gui, 13: hide
Gui, 6: Show, x100 y100 h400 w600, Edit Loadout
Gui, 3: destroy
Gui, 7: destroy
Gui, 16: destroy
Gui, 17: destroy

gosub, Load_Loadout

}
else
{
Gui, 3: +Disabled
Gui, 12: +AlwaysOnTop -caption +border
Gui, 12: Color, 000000
Gui, 12: Font, cWhite s14, Arial
Gui, 12: Add, Text, x0 y10 w300 h30 center, ---------- INFO ----------
Gui, 12: Add, Text, vShip_confirm_text1 x0 y45 w300 h50 center, No Ship selected
Gui, 12: Add, Button, vShip_confirm_button1 gEdit_confirm x110 y125 w80 h30 +default, Ok
Gui, 12: Add, Text, x0 y0 w300 h170 0x12
Gui, 12: Show, x287.5 y273.75 h170 w300, Info
}
return


Load_Loadout:
Gui, 6:Submit, nohide
Iniread, Edit_Crew1, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini,%Edit_Loadout_Loadout_selected%|,Crew1
Iniread, Edit_Crew2, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini,%Edit_Loadout_Loadout_selected%|,Crew2
Iniread, Edit_Crew3, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini,%Edit_Loadout_Loadout_selected%|,Crew3
Iniread, Edit_Crew4, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini,%Edit_Loadout_Loadout_selected%|,Crew4
Iniread, Edit_Crew5, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini,%Edit_Loadout_Loadout_selected%|,Crew5
Iniread, Edit_Crew6, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini,%Edit_Loadout_Loadout_selected%|,Crew6
Iniread, Edit_Crew7, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini,%Edit_Loadout_Loadout_selected%|,Crew7
Iniread, Edit_Crew8, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini,%Edit_Loadout_Loadout_selected%|,Crew8
Iniread, Edit_Crew9, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini,%Edit_Loadout_Loadout_selected%|,Crew9
Iniread, Edit_Crew10, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini,%Edit_Loadout_Loadout_selected%|,Crew10
Iniread, Edit_Crew11, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini,%Edit_Loadout_Loadout_selected%|,Crew11
Iniread, Edit_Crew12, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini,%Edit_Loadout_Loadout_selected%|,Crew12
Iniread, Edit_Crew13, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini,%Edit_Loadout_Loadout_selected%|,Crew13
Iniread, Edit_Crew14, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini,%Edit_Loadout_Loadout_selected%|,Crew14
Iniread, Edit_Crew15, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini,%Edit_Loadout_Loadout_selected%|,Crew15
Iniread, Edit_Preset, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini,%Edit_Loadout_Loadout_selected%|,Preset
GuiControl, 6: , Edit_Crew1, %Edit_Crew1%
GuiControl, 6: , Edit_Crew2, %Edit_Crew2%
GuiControl, 6: , Edit_Crew3, %Edit_Crew3%
GuiControl, 6: , Edit_Crew4, %Edit_Crew4%
GuiControl, 6: , Edit_Crew5, %Edit_Crew5%
GuiControl, 6: , Edit_Crew6, %Edit_Crew6%
GuiControl, 6: , Edit_Crew7, %Edit_Crew7%
GuiControl, 6: , Edit_Crew8, %Edit_Crew8%
GuiControl, 6: , Edit_Crew9, %Edit_Crew9%
GuiControl, 6: , Edit_Crew10, %Edit_Crew10%
GuiControl, 6: , Edit_Crew11, %Edit_Crew11%
GuiControl, 6: , Edit_Crew12, %Edit_Crew12%
GuiControl, 6: , Edit_Crew13, %Edit_Crew13%
GuiControl, 6: , Edit_Crew14, %Edit_Crew14%
GuiControl, 6: , Edit_Crew15, %Edit_Crew15%
GuiControl, 6: chooseString, Edit_Preset, %Edit_Preset%

IniRead,check_ellydium_tree,%A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini,%Edit_Loadout_Loadout_selected%|,SpecMod_1

If (check_ellydium_tree = "ERROR")
{
	GuiControl, 6: , Tree_active_text, Ellydium Tree active: No
}
else
{
	GuiControl, 6: , Tree_active_text, Ellydium Tree active: Yes
}
return




Save_Loadout:
Gui, 6:Submit, nohide
If (Edit_Loadout_Loadout_selected != "None")
{
Gui, 6: +Disabled
IniWrite, %Edit_Crew1%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %Edit_Loadout_Loadout_selected%|,Crew1
IniWrite, %Edit_Crew2%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %Edit_Loadout_Loadout_selected%|,Crew2
IniWrite, %Edit_Crew3%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %Edit_Loadout_Loadout_selected%|,Crew3
IniWrite, %Edit_Crew4%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %Edit_Loadout_Loadout_selected%|,Crew4
IniWrite, %Edit_Crew5%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %Edit_Loadout_Loadout_selected%|,Crew5
IniWrite, %Edit_Crew6%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %Edit_Loadout_Loadout_selected%|,Crew6
IniWrite, %Edit_Crew7%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %Edit_Loadout_Loadout_selected%|,Crew7
IniWrite, %Edit_Crew8%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %Edit_Loadout_Loadout_selected%|,Crew8
IniWrite, %Edit_Crew9%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %Edit_Loadout_Loadout_selected%|,Crew9
IniWrite, %Edit_Crew10%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %Edit_Loadout_Loadout_selected%|,Crew10
IniWrite, %Edit_Crew11%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %Edit_Loadout_Loadout_selected%|,Crew11
IniWrite, %Edit_Crew12%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %Edit_Loadout_Loadout_selected%|,Crew12
IniWrite, %Edit_Crew13%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %Edit_Loadout_Loadout_selected%|,Crew13
IniWrite, %Edit_Crew14%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %Edit_Loadout_Loadout_selected%|,Crew14
IniWrite, %Edit_Crew15%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %Edit_Loadout_Loadout_selected%|,Crew15
IniWrite, %Edit_Preset%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %Edit_Loadout_Loadout_selected%|,Preset


Gui, 12: +AlwaysOnTop -caption +border
Gui, 12: Color, 000000
Gui, 12: Font, cWhite s14, Arial
Gui, 12: Add, Text, x0 y10 w300 h30 center, ---------- INFO ----------
Gui, 12: Add, Text, vShip_confirm_text1 x10 y45 w280 h50 center, Loadout "%Edit_Loadout_Loadout_selected%" Saved
Gui, 12: Add, Button, vShip_confirm_button1 gLoadout_saved_confirm x110 y125 w80 h30 +default, Ok
Gui, 12: Add, Text, x0 y0 w300 h170 0x12
Gui, 12: Show, x287.5 y273.75 h170 w300, Info
}
else
{

}
return

Loadout_saved_confirm:
Gui, 6: -Disabled
Gui, 12: Destroy
return


Delete_Loadout:
Gui, 6:Submit, nohide

If (Edit_Loadout_Loadout_selected != "None")
{
Gui, 6: +Disabled
Gui, 11: +AlwaysOnTop -caption +border
Gui, 11: Color, 000000
Gui, 11: Font, cRed s14, Arial
Gui, 11: Add, Text, x0 y10 w300 h30 center, --------- WARNING ---------
Gui, 11: Font, cWhite s14, Arial
Gui, 11: Add, Text, vDelete_Loadout_Text1 x5 y40 w290 center, Do you really want to delete`nloadout "%Edit_Loadout_Loadout_selected%"`nfrom "%Edit_Loadout_Ship_selected%"?
Gui, 11: Add, Button, vDelete_Loadout_Button2 gDelete_Loadout_No x170 y125 w80 h30 +default, NO
Gui, 11: Add, Button, vDelete_Loadout_Button1 gDelete_Loadout_Yes x50 y125 w80 h30, YES
Gui, 11: Add, Text, x0 y0 w300 h170 0x12
Gui, 11: Show, x287.5 y273.75 h170 w300, WARNING
}
return

Delete_Loadout_Yes:
IniDelete, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %Edit_Loadout_Loadout_selected%|
GuiControl, 11: text, Delete_Loadout_Text1, "%Edit_Loadout_Loadout_selected%" deleted
GuiControl, 11: hide, Delete_Loadout_Button1
GuiControl, 11: hide, Delete_Loadout_Button2

Gui, 11: Add, Button, vDelete_Loadout_Button3 gDelete_Loadout_Ok x110 y125 w80 h30 +default, Ok
return

Delete_Loadout_OK:
IniRead,Edit_Loadout_List,%A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini
StringReplace, Edit_Loadout_List,Edit_Loadout_List, `n,, All
GuiControl, 6:, Edit_Loadout_Loadout_selected, |%Edit_Loadout_List%
GuiControl, 6: chooseString, Edit_Loadout_Loadout_selected, None
Gui, 6: -Disabled
Gui, 11: destroy
return

Delete_Loadout_No:
Gui, 6: -Disabled
Gui, 11: destroy
return

return


Exit6:
goto, Show_Ship_Stats_Gui
return




;--------------------------------------------------Rename Loadout--------------------------------------------------


Rename_Loadout_Gui:
If (Edit_Loadout_Loadout_selected != "None")
{
Gui, 6: +Disabled
Gui, 12: +AlwaysOnTop -caption +border
Gui, 12: Color, 000000
Gui, 12: Font, cWhite s14, Arial
Gui, 12: Add, Text, x0 y10 w300 h30 center, ---------- INFO ----------
Gui, 12: Add, Text, vRename_Loadout_Text1 x10 y40 w280 h25 center, Rename: "%Edit_Loadout_Loadout_selected%"
Gui, 12: Font, cBlack s14, Arial
Gui, 12: Add, edit, vRename_Loadout_New_Name x40 y75 w220 h30 center,%Edit_Loadout_Loadout_selected%
Gui, 12: Font, cWhite s14, Arial
Gui, 12: Add, Button, gRename_Loadout_Save x65 y125 w80 h30 +default, Save
Gui, 12: Add, Button, gRename_Loadout_Cancel x155 y125 w80 h30, Cancel
Gui, 12: Add, Text, x0 y0 w300 h170 0x12
Gui, 12: Show, x287.5 y273.75 h170 w300, Info

return

Rename_Loadout_Save:
Gui,12:Submit, nohide
Rename_Loadout_New_Name := regexreplace(Rename_Loadout_New_Name, "^\s+") ;trim beginning whitespace
Rename_Loadout_New_Name := regexreplace(Rename_Loadout_New_Name, "\s+$") ;trim ending whitespace
GuiControl, 12: , Rename_Loadout_New_Name, %Rename_Loadout_New_Name%
IniRead,Rename_Loadout_New_Name_Check,%A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini,%Rename_Loadout_New_Name%|


If (Rename_Loadout_New_Name = "")
{
GuiControl, 12: Text, Rename_Loadout_Text1, Field cannot be blank
SetTimer, Timer_Rename_Loadout_Text, -3000
}else if (Rename_Loadout_New_Name = "None")
{
GuiControl, 12: Text, Rename_Loadout_Text1, Loadout cannot be named:
SetTimer, Timer_Rename_Loadout_Text, -3000
}else If (!Rename_Loadout_New_Name_Check)
{

filePath = Builds\%Edit_Loadout_Ship_selected%.ini
newData := replaceLabel(Edit_Loadout_Loadout_selected "|", Rename_Loadout_New_Name "|", filePath)
GuiControl, 12: Text, Rename_Loadout_Text1, Loadout name changed
Gui, 6: -Disabled
Iniread, Edit_Loadout_List, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini
StringReplace, Edit_Loadout_Ship_selected,Edit_Loadout_Ship_selected, `n,, All
StringReplace, Edit_Loadout_List,Edit_Loadout_List, `n,, All
GuiControl, 6: , Edit_Loadout_Loadout_selected, |%Edit_Loadout_List%
GuiControl, 6: chooseString, Edit_Loadout_Loadout_selected, %Rename_Loadout_New_Name%
Gui, 12: destroy
return
}
else
{
GuiControl, 12: Text, Rename_Loadout_Text1, Preset already exists
SetTimer, Timer_Rename_Loadout_Text, -3000
}
return


Timer_Rename_Loadout_Text:
GuiControl, 12: Text, Rename_Loadout_Text1, Rename: "%Edit_Loadout_Loadout_selected%"
return


Rename_Loadout_Cancel:
Gui, 6: -Disabled
Gui, 12: destroy
return

}
else
{
}
return


;--------------------------------------------------Add Ship Loadout--------------------------------------------------


Add_New_Loadout_Gui:
Gui, 13: show

Gui, 7: +AlwaysOnTop +Toolwindow
Gui, 7: Color, 000000
Gui, 7: Font, cWhite s22, Arial
Gui, 7: Add, Text, x0 y40 w600 center, %Edit_Loadout_Ship_selected%


Gui, 7: Font, cWhite s12, Arial
Gui, 7: Add, Text, x0 y10 w600 h30 center, -------------------- Add Loadout --------------------


Gui, 7: Add, Text, x95 y100 w130 h30 right, New Loadout:
Gui, 7: Add, Text, x130 y160 w130 h30 right, Preset:


Gui, 7: Font, cBlack s12, Arial
Gui, 7: Add, edit, vNew_Loadout_Name x235 y95 w130,
Gui, 7: Font, cWhite s16, Arial
Gui, 7: Add, DDL, vEdit_Preset x270 y153 w50 Choose1 center, |1|2|3|4|


Gui, 7: Font, cWhite s16, Arial
Gui, 7: Add, Text, x255 y200 w80 h30 center, Crew
Gui, 6: Font, cWhite s12, Arial
Gui, 7: Add, Text, x20 y230 w550 0x10 ;White Line


Gui, 7: Font, cWhite s16, Arial
Gui, 7: Add, Text, x19 y240 center, 1
Gui, 7: Add, Text, x53 y240 center, 2
Gui, 7: Add, Text, x92 y240 center, 3
Gui, 7: Add, Text, x130 y240 center, 4
Gui, 7: Add, Text, x168 y240 center, 5
Gui, 7: Add, Text, x208 y240 center, 6
Gui, 7: Add, Text, x248 y240 center, 7
Gui, 7: Add, Text, x285 y240 center, 8
Gui, 7: Add, Text, x323 y240 center, 9
Gui, 7: Add, Text, x357 y240 center, 10
Gui, 7: Add, Text, x400 y240 center, 11
Gui, 7: Add, Text, x434 y240 center, 12
Gui, 7: Add, Text, x472 y240 center, 13
Gui, 7: Add, Text, x511 y240 center, 14
Gui, 7: Add, Text, x549 y240 center, 15

Gui, 7: Add, Text, x25 y270 h15 0x11 ;White Line
Gui, 7: Add, Text, x63.57 y270 h15 0x11 ;White Line
Gui, 7: Add, Text, x102.14 y270 h15 0x11 ;White Line
Gui, 7: Add, Text, x140.71 y270 h15 0x11 ;White Line
Gui, 7: Add, Text, x179.28 y270 h15 0x11 ;White Line
Gui, 7: Add, Text, x217.85 y270 h15 0x11 ;White Line
Gui, 7: Add, Text, x256.42 y270 h15 0x11 ;White Line
Gui, 7: Add, Text, x294.99 y270 h15 0x11 ;White Line
Gui, 7: Add, Text, x333.56 y270 h15 0x11 ;White Line
Gui, 7: Add, Text, x372.13 y270 h15 0x11 ;White Line
Gui, 7: Add, Text, x410.7 y270 h15 0x11 ;White Line
Gui, 7: Add, Text, x449.27 y270 h15 0x11 ;White Line
Gui, 7: Add, Text, x487.84 y270 h15 0x11 ;White Line
Gui, 7: Add, Text, x526.41 y270 h15 0x11 ;White Line
Gui, 7: Add, Text, x564.98 y270 h15 0x11 ;White Line

Gui, 7: Font, cBlack s16, Arial
Gui, 7: Add, Edit, vEdit_Crew1 gCheck_Number_New1 x10 y300 w30 h30 +center +number limit1, 
Gui, 7: Add, Edit, vEdit_Crew2 gCheck_Number_New2 x48.57 y300 w30 h30 +center +number limit1, 
Gui, 7: Add, Edit, vEdit_Crew3 gCheck_Number_New3 x87.14 y300 w30 h30 +center +number limit1, 
Gui, 7: Add, Edit, vEdit_Crew4 gCheck_Number_New4 x125.71 y300 w30 h30 +center +number limit1, 
Gui, 7: Add, Edit, vEdit_Crew5 gCheck_Number_New5 x164.28 y300 w30 h30 +center +number limit1, 
Gui, 7: Add, Edit, vEdit_Crew6 gCheck_Number_New6 x202.85 y300 w30 h30 +center +number limit1, 
Gui, 7: Add, Edit, vEdit_Crew7 gCheck_Number_New7 x241.42 y300 w30 h30 +center +number limit1, 
Gui, 7: Add, Edit, vEdit_Crew8 gCheck_Number_New8 x279.99 y300 w30 h30 +center +number limit1, 
Gui, 7: Add, Edit, vEdit_Crew9 gCheck_Number_New9 x318.56 y300 w30 h30 +center +number limit1, 
Gui, 7: Add, Edit, vEdit_Crew10 gCheck_Number_New10 x357.13 y300 w30 h30 +center +number limit1, 
Gui, 7: Add, Edit, vEdit_Crew11 gCheck_Number_New11 x395.7 y300 w30 h30 +center +number limit1, 
Gui, 7: Add, Edit, vEdit_Crew12 gCheck_Number_New12 x434.27 y300 w30 h30 +center +number limit1, 
Gui, 7: Add, Edit, vEdit_Crew13 gCheck_Number_New13 x472.84 y300 w30 h30 +center +number limit1, 
Gui, 7: Add, Edit, vEdit_Crew14 gCheck_Number_New14 x511.41 y300 w30 h30 +center +number limit1, 
Gui, 7: Add, Edit, vEdit_Crew15 gCheck_Number_New15 x549.98 y300 w30 h30 +center +number limit1, 


Gui, 7: Add, Button, gAdd_New_Loadout x255 y350 w80 h30, Add


Gui, 7: Font, cWhite s9, Arial
Gui, 7: Add, Button, gExit7 x500 y360 w80 h20, Back


Gui, 13: hide
Gui, 7: Show, x100 y100 h400 w600, Add Loadout
Gui, 6: destroy
return


Add_New_Loadout:
Gui, 7:Submit, nohide
New_Loadout_Name := regexreplace(New_Loadout_Name, "^\s+") ;trim beginning whitespace
New_Loadout_Name := regexreplace(New_Loadout_Name, "\s+$") ;trim ending whitespace
GuiControl, 7: , New_Loadout_Name, %New_Loadout_Name%
IniRead,Add_New_Loadout_Check,%A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini,%New_Loadout_Name%|

Gui, 12: +AlwaysOnTop -caption +border
Gui, 12: Color, 000000
Gui, 12: Font, cWhite s14, Arial
Gui, 12: Add, Text, x0 y10 w300 h30 center, ---------- INFO ----------
Gui, 12: Add, Text, vShip_confirm_text1 x10 y45 w280 h50 center,
Gui, 12: Add, Button, vShip_confirm_button1 gLoadout_confirm x110 y125 w80 h30 +default, Ok
Gui, 12: Add, Text, x0 y0 w300 h170 0x12


If (New_Loadout_Name = "")
{
GuiControl, 12: Text, Ship_confirm_text1, Field cannot be blank
Gui, 12: Show, x287.5 y273.75 h170 w300, Info
}else if (New_Loadout_Name = "None")
{
GuiControl, 12: Text, Ship_confirm_text1, Loadout cannot be named "None"
Gui, 12: Show, x287.5 y273.75 h170 w300, Info
}else If (!Add_New_Loadout_Check)
{
Gui, 7: +Disabled
IniWrite, %Edit_Crew1%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %New_Loadout_Name%|,Crew1
IniWrite, %Edit_Crew2%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %New_Loadout_Name%|,Crew2
IniWrite, %Edit_Crew3%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %New_Loadout_Name%|,Crew3
IniWrite, %Edit_Crew4%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %New_Loadout_Name%|,Crew4
IniWrite, %Edit_Crew5%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %New_Loadout_Name%|,Crew5
IniWrite, %Edit_Crew6%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %New_Loadout_Name%|,Crew6
IniWrite, %Edit_Crew7%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %New_Loadout_Name%|,Crew7
IniWrite, %Edit_Crew8%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %New_Loadout_Name%|,Crew8
IniWrite, %Edit_Crew9%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %New_Loadout_Name%|,Crew9
IniWrite, %Edit_Crew10%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %New_Loadout_Name%|,Crew10
IniWrite, %Edit_Crew11%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %New_Loadout_Name%|,Crew11
IniWrite, %Edit_Crew12%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %New_Loadout_Name%|,Crew12
IniWrite, %Edit_Crew13%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %New_Loadout_Name%|,Crew13
IniWrite, %Edit_Crew14%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %New_Loadout_Name%|,Crew14
IniWrite, %Edit_Crew15%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %New_Loadout_Name%|,Crew15
IniWrite, %Edit_Preset%, %A_ScriptDir%\Builds\%Edit_Loadout_Ship_selected%.ini, %New_Loadout_Name%|,Preset

GuiControl, 12: Text, Ship_confirm_text1, Preset "%New_Loadout_Name%" added
Gui, 12: Show, x287.5 y273.75 h170 w300, Info
Loadout_Added := 1
}
else
{
GuiControl, 12: Text, Ship_confirm_text1, Preset "%New_Loadout_Name%" already exists
Gui, 12: Show, x287.5 y273.75 h170 w300, Info
}
return


Loadout_confirm:
If (Loadout_Added = 1)
{
Loadout_Added := 0
Gui, 7: -Disabled
Gui, 12: destroy
goto, Edit_Loadout_Gui
}
else
{
Gui, 7: -Disabled
Gui, 12: destroy
}
return


Exit7:
goto, Edit_Loadout_Gui
return



;--------------------------------------------------Check Number--------------------------------------------------

Check_Number1:
Gui, 6:Submit, nohide
If (Edit_Crew1 < 1) or (Edit_Crew1 >= 4) or (Edit_Loadout_Loadout_selected = "None")
{
Edit_Crew1 := ""
GuiControl, 6: , Edit_Crew1, 
}
return

Check_Number2:
Gui, 6:Submit, nohide
If (Edit_Crew2 < 1) or (Edit_Crew2 >= 4) or (Edit_Loadout_Loadout_selected = "None")
{
Edit_Crew2 := ""
GuiControl, 6: , Edit_Crew2,  
}
return

Check_Number3:
Gui, 6:Submit, nohide
If (Edit_Crew3 < 1) or (Edit_Crew3 >= 4) or (Edit_Loadout_Loadout_selected = "None")
{
Edit_Crew3 := ""
GuiControl, 6: , Edit_Crew3,  
}
return

Check_Number4:
Gui, 6:Submit, nohide
If (Edit_Crew4 < 1) or (Edit_Crew4 >= 4) or (Edit_Loadout_Loadout_selected = "None")
{
Edit_Crew4 := ""
GuiControl, 6: , Edit_Crew4, 
}
return

Check_Number5:
Gui, 6:Submit, nohide
If (Edit_Crew5 < 1) or (Edit_Crew5 >= 4) or (Edit_Loadout_Loadout_selected = "None")
{
Edit_Crew5 := ""
GuiControl, 6: , Edit_Crew5, 
}

return

Check_Number6:
Gui, 6:Submit, nohide
If (Edit_Crew6 < 1) or (Edit_Crew6 >= 4) or (Edit_Loadout_Loadout_selected = "None")
{
Edit_Crew6 := ""
GuiControl, 6: , Edit_Crew6,  
}

return

Check_Number7:
Gui, 6:Submit, nohide
If (Edit_Crew7 < 1) or (Edit_Crew7 >= 4) or (Edit_Loadout_Loadout_selected = "None")
{
Edit_Crew7 := ""
GuiControl, 6: , Edit_Crew7,  
}

return

Check_Number8:
Gui, 6:Submit, nohide
If (Edit_Crew8 < 1) or (Edit_Crew8 >= 4) or (Edit_Loadout_Loadout_selected = "None")
{
Edit_Crew8 := ""
GuiControl, 6: , Edit_Crew8,   
}
return

Check_Number9:
Gui, 6:Submit, nohide
If (Edit_Crew9 < 1) or (Edit_Crew9 >= 4) or (Edit_Loadout_Loadout_selected = "None")
{
Edit_Crew9 := ""
GuiControl, 6: , Edit_Crew9, 
}
return

Check_Number10:
Gui, 6:Submit, nohide
If (Edit_Crew10 < 1) or (Edit_Crew10 >= 4) or (Edit_Loadout_Loadout_selected = "None")
{
Edit_Crew10 := ""
GuiControl, 6: , Edit_Crew10, 
}
return

Check_Number11:
Gui, 6:Submit, nohide
If (Edit_Crew11 < 1) or (Edit_Crew11 >= 4) or (Edit_Loadout_Loadout_selected = "None")
{
Edit_Crew11 := ""
GuiControl, 6: , Edit_Crew11,  
}
return

Check_Number12:
Gui, 6:Submit, nohide
If (Edit_Crew12 < 1) or (Edit_Crew12 >= 4) or (Edit_Loadout_Loadout_selected = "None")
{
Edit_Crew12 := ""
GuiControl, 6: , Edit_Crew12,  
}
return

Check_Number13:
Gui, 6:Submit, nohide
If (Edit_Crew13 < 1) or (Edit_Crew13 >= 4) or (Edit_Loadout_Loadout_selected = "None")
{
Edit_Crew13 := ""
GuiControl, 6: , Edit_Crew13,  
}
return

Check_Number14:
Gui, 6:Submit, nohide
If (Edit_Crew14 < 1) or (Edit_Crew14 >= 4) or (Edit_Loadout_Loadout_selected = "None")
{
Edit_Crew14 := ""
GuiControl, 6: , Edit_Crew14,  
}
return

Check_Number15:
Gui, 6:Submit, nohide
If (Edit_Crew15 < 1) or (Edit_Crew15 >= 4) or (Edit_Loadout_Loadout_selected = "None")
{
Edit_Crew15 := ""
GuiControl, 6: , Edit_Crew15,  
}
return




Check_Number_New1:
Gui, 7:Submit, nohide
If (Edit_Crew1 < 1) or (Edit_Crew1 >= 4)
{
Edit_Crew1 := "" 
GuiControl, 7: , Edit_Crew1, 
}
return

Check_Number_New2:
Gui, 7:Submit, nohide
If (Edit_Crew2 < 1) or (Edit_Crew2 >= 4)
{
Edit_Crew2 := ""
GuiControl, 7: , Edit_Crew2, 
}
return

Check_Number_New3:
Gui, 7:Submit, nohide
If (Edit_Crew3 < 1) or (Edit_Crew3 >= 4)
{
Edit_Crew3 := ""
GuiControl, 7: , Edit_Crew3, 
}
return

Check_Number_New4:
Gui, 7:Submit, nohide
If (Edit_Crew4 < 1) or (Edit_Crew4 >= 4)
{
Edit_Crew4 := ""
GuiControl, 7: , Edit_Crew4, 
}
return

Check_Number_New5:
Gui, 7:Submit, nohide
If (Edit_Crew5 < 1) or (Edit_Crew5 >= 4)
{
Edit_Crew5 := ""
GuiControl, 7: , Edit_Crew5, 
}

return

Check_Number_New6:
Gui, 7:Submit, nohide
If (Edit_Crew6 < 1) or (Edit_Crew6 >= 4)
{
Edit_Crew6 := ""
GuiControl, 7: , Edit_Crew6, 
}

return

Check_Number_New7:
Gui, 7:Submit, nohide
If (Edit_Crew7 < 1) or (Edit_Crew7 >= 4)
{
Edit_Crew7 := ""
GuiControl, 7: , Edit_Crew7, 
}

return

Check_Number_New8:
Gui, 7:Submit, nohide
If (Edit_Crew8 < 1) or (Edit_Crew8 >= 4)
{
Edit_Crew8 := ""
GuiControl, 7: , Edit_Crew8,  
}
return

Check_Number_New9:
Gui, 7:Submit, nohide
If (Edit_Crew9 < 1) or (Edit_Crew9 >= 4)
{
Edit_Crew9 := ""
GuiControl, 7: , Edit_Crew9,  
}
return

Check_Number_New10:
Gui, 7:Submit, nohide
If (Edit_Crew10 < 1) or (Edit_Crew10 >= 4)
{
Edit_Crew10 := ""
GuiControl, 7: , Edit_Crew10, 
}
return

Check_Number_New11:
Gui, 7:Submit, nohide
If (Edit_Crew11 < 1) or (Edit_Crew11 >= 4)
{
Edit_Crew11 := ""
GuiControl, 7: , Edit_Crew11, 
}
return

Check_Number_New12:
Gui, 7:Submit, nohide
If (Edit_Crew12 < 1) or (Edit_Crew12 >= 4)
{
Edit_Crew12 := ""
GuiControl, 7: , Edit_Crew12, 
}
return

Check_Number_New13:
Gui, 7:Submit, nohide
If (Edit_Crew13 < 1) or (Edit_Crew13 >= 4)
{
Edit_Crew13 := ""
GuiControl, 7: , Edit_Crew13, 
}
return

Check_Number_New14:
Gui, 7:Submit, nohide
If (Edit_Crew14 < 1) or (Edit_Crew14 >= 4)
{
Edit_Crew14 := ""
GuiControl, 7: , Edit_Crew14, 
}
return

Check_Number_New15:
Gui, 7:Submit, nohide
If (Edit_Crew15 < 1) or (Edit_Crew15 >= 4)
{
Edit_Crew15 := ""
GuiControl, 7: , Edit_Crew15, 
}
return


;--------------------------------------------------Auto Coordinates--------------------------------------------------


Auto_Coordinates_Start:
Auto_Coordiantes_Ship := 1
Hotkey, LButton, On
return

Auto_Coordiantes_Start_Ellydium:
Auto_Coordiantes_Ship_Ellydium := 1
Hotkey, LButton, On
return

LButton::
If (Auto_Coordiantes_Ship = 1)
{
Hotkey, LButton, Off
MouseGetPos , MouseX, MouseY
GuiControl, 4: Text, Add_New_Ship_X, %MouseX%
GuiControl, 4: Text, Add_New_Ship_Y, %MouseY%
GuiControl, 5: Text, Edit_Ship_X, %MouseX%
GuiControl, 5: Text, Edit_Ship_Y, %MouseY%
Auto_Coordiantes_Ship := 0
}
else if (Auto_Coordiantes_Ship_Ellydium = 1)
{
Hotkey, LButton, Off
MouseGetPos , MouseX, MouseY
GuiControl, 4: Text, Add_New_Ship_X_ellydium, %MouseX%
GuiControl, 4: Text, Add_New_Ship_Y_ellydium, %MouseY%
GuiControl, 5: Text, Edit_Ship_X_ellydium, %MouseX%
GuiControl, 5: Text, Edit_Ship_Y_ellydium, %MouseY%
}
else
{
	Hotkey, LButton, Off
	MouseGetPos , MouseX, MouseY
	IniWrite, %MouseX%, %A_ScriptDir%\Settings\Coordinates.ini, %Loaded%, x
	IniWrite, %MouseY%, %A_ScriptDir%\Settings\Coordinates.ini, %Loaded%, y
	
	If Loaded = Implant
	{
		PixelGetColor, implant_color, %MouseX%, %MouseY%, RGB
		IniWrite, %implant_color%, %A_ScriptDir%\Settings\Coordinates.ini, %Loaded%, implant_color
	}
	
	If Loaded = Slot1
	{
		IniWrite, 1, %A_ScriptDir%\Settings\Coordinates.ini, %Loaded%, Slot
	}
	If Loaded = Slot2
	{
		IniWrite, 2, %A_ScriptDir%\Settings\Coordinates.ini, %Loaded%, Slot
	}
	If Loaded = Slot3
	{
		IniWrite, 3, %A_ScriptDir%\Settings\Coordinates.ini, %Loaded%, Slot
	}
	If Loaded = Slot4
	{
		IniWrite, 4, %A_ScriptDir%\Settings\Coordinates.ini, %Loaded%, Slot
	}
	

	If Crew_Calc = 1
	{
		Crew_Calc := 0
		IniRead, Crew1_1_X, %A_ScriptDir%\Settings\Coordinates.ini, Crew1-1, x
		IniRead, Crew1_1_Y, %A_ScriptDir%\Settings\Coordinates.ini, Crew1-1, y
		IniRead, Crew15_3_X, %A_ScriptDir%\Settings\Coordinates.ini, Crew15-3, x
		IniRead, Crew15_3_Y, %A_ScriptDir%\Settings\Coordinates.ini, Crew15-3, y


		CrewX_1 := (Crew1_1_X)
		CrewX_2 := Format("{:d}", (Crew15_3_X-Crew1_1_X)/14*1+Crew1_1_X)
		CrewX_3 := Format("{:d}", (Crew15_3_X-Crew1_1_X)/14*2+Crew1_1_X)
		CrewX_4 := Format("{:d}", (Crew15_3_X-Crew1_1_X)/14*3+Crew1_1_X)
		CrewX_5 := Format("{:d}", (Crew15_3_X-Crew1_1_X)/14*4+Crew1_1_X)
		CrewX_6 := Format("{:d}", (Crew15_3_X-Crew1_1_X)/14*5+Crew1_1_X)
		CrewX_7 := Format("{:d}", (Crew15_3_X-Crew1_1_X)/14*6+Crew1_1_X)
		CrewX_8 := Format("{:d}", (Crew15_3_X-Crew1_1_X)/14*7+Crew1_1_X)
		CrewX_9 := Format("{:d}", (Crew15_3_X-Crew1_1_X)/14*8+Crew1_1_X)
		CrewX_10 := Format("{:d}", (Crew15_3_X-Crew1_1_X)/14*9+Crew1_1_X)
		CrewX_11 := Format("{:d}", (Crew15_3_X-Crew1_1_X)/14*10+Crew1_1_X)
		CrewX_12 := Format("{:d}", (Crew15_3_X-Crew1_1_X)/14*11+Crew1_1_X)
		CrewX_13 := Format("{:d}", (Crew15_3_X-Crew1_1_X)/14*12+Crew1_1_X)
		CrewX_14 := Format("{:d}", (Crew15_3_X-Crew1_1_X)/14*13+Crew1_1_X)
		CrewX_15 := (Crew15_3_X)

		CrewY_1 := (Crew1_1_Y)
		CrewY_2 := Format("{:d}", (Crew15_3_Y-Crew1_1_Y)/2+Crew1_1_Y)    
		CrewY_3 := (Crew15_3_Y)


		IniWrite, %CrewX_1%, %A_ScriptDir%\Settings\Coordinates.ini, Crew1-1, x
		IniWrite, %CrewX_1%, %A_ScriptDir%\Settings\Coordinates.ini, Crew1-2, x
		IniWrite, %CrewX_1%, %A_ScriptDir%\Settings\Coordinates.ini, Crew1-3, x

		IniWrite, %CrewX_2%, %A_ScriptDir%\Settings\Coordinates.ini, Crew2-1, x
		IniWrite, %CrewX_2%, %A_ScriptDir%\Settings\Coordinates.ini, Crew2-2, x
		IniWrite, %CrewX_2%, %A_ScriptDir%\Settings\Coordinates.ini, Crew2-3, x

		IniWrite, %CrewX_3%, %A_ScriptDir%\Settings\Coordinates.ini, Crew3-1, x
		IniWrite, %CrewX_3%, %A_ScriptDir%\Settings\Coordinates.ini, Crew3-2, x
		IniWrite, %CrewX_3%, %A_ScriptDir%\Settings\Coordinates.ini, Crew3-3, x

		IniWrite, %CrewX_4%, %A_ScriptDir%\Settings\Coordinates.ini, Crew4-1, x
		IniWrite, %CrewX_4%, %A_ScriptDir%\Settings\Coordinates.ini, Crew4-2, x
		IniWrite, %CrewX_4%, %A_ScriptDir%\Settings\Coordinates.ini, Crew4-3, x

		IniWrite, %CrewX_5%, %A_ScriptDir%\Settings\Coordinates.ini, Crew5-1, x
		IniWrite, %CrewX_5%, %A_ScriptDir%\Settings\Coordinates.ini, Crew5-2, x
		IniWrite, %CrewX_5%, %A_ScriptDir%\Settings\Coordinates.ini, Crew5-3, x

		IniWrite, %CrewX_6%, %A_ScriptDir%\Settings\Coordinates.ini, Crew6-1, x
		IniWrite, %CrewX_6%, %A_ScriptDir%\Settings\Coordinates.ini, Crew6-2, x
		IniWrite, %CrewX_6%, %A_ScriptDir%\Settings\Coordinates.ini, Crew6-3, x

		IniWrite, %CrewX_7%, %A_ScriptDir%\Settings\Coordinates.ini, Crew7-1, x
		IniWrite, %CrewX_7%, %A_ScriptDir%\Settings\Coordinates.ini, Crew7-2, x
		IniWrite, %CrewX_7%, %A_ScriptDir%\Settings\Coordinates.ini, Crew7-3, x

		IniWrite, %CrewX_8%, %A_ScriptDir%\Settings\Coordinates.ini, Crew8-1, x
		IniWrite, %CrewX_8%, %A_ScriptDir%\Settings\Coordinates.ini, Crew8-2, x
		IniWrite, %CrewX_8%, %A_ScriptDir%\Settings\Coordinates.ini, Crew8-3, x

		IniWrite, %CrewX_9%, %A_ScriptDir%\Settings\Coordinates.ini, Crew9-1, x
		IniWrite, %CrewX_9%, %A_ScriptDir%\Settings\Coordinates.ini, Crew9-2, x
		IniWrite, %CrewX_9%, %A_ScriptDir%\Settings\Coordinates.ini, Crew9-3, x

		IniWrite, %CrewX_10%, %A_ScriptDir%\Settings\Coordinates.ini, Crew10-1, x
		IniWrite, %CrewX_10%, %A_ScriptDir%\Settings\Coordinates.ini, Crew10-2, x
		IniWrite, %CrewX_10%, %A_ScriptDir%\Settings\Coordinates.ini, Crew10-3, x

		IniWrite, %CrewX_11%, %A_ScriptDir%\Settings\Coordinates.ini, Crew11-1, x
		IniWrite, %CrewX_11%, %A_ScriptDir%\Settings\Coordinates.ini, Crew11-2, x
		IniWrite, %CrewX_11%, %A_ScriptDir%\Settings\Coordinates.ini, Crew11-3, x

		IniWrite, %CrewX_12%, %A_ScriptDir%\Settings\Coordinates.ini, Crew12-1, x
		IniWrite, %CrewX_12%, %A_ScriptDir%\Settings\Coordinates.ini, Crew12-2, x
		IniWrite, %CrewX_12%, %A_ScriptDir%\Settings\Coordinates.ini, Crew12-3, x

		IniWrite, %CrewX_13%, %A_ScriptDir%\Settings\Coordinates.ini, Crew13-1, x
		IniWrite, %CrewX_13%, %A_ScriptDir%\Settings\Coordinates.ini, Crew13-2, x
		IniWrite, %CrewX_13%, %A_ScriptDir%\Settings\Coordinates.ini, Crew13-3, x

		IniWrite, %CrewX_14%, %A_ScriptDir%\Settings\Coordinates.ini, Crew14-1, x
		IniWrite, %CrewX_14%, %A_ScriptDir%\Settings\Coordinates.ini, Crew14-2, x
		IniWrite, %CrewX_14%, %A_ScriptDir%\Settings\Coordinates.ini, Crew14-3, x

		IniWrite, %CrewX_15%, %A_ScriptDir%\Settings\Coordinates.ini, Crew15-1, x
		IniWrite, %CrewX_15%, %A_ScriptDir%\Settings\Coordinates.ini, Crew15-2, x
		IniWrite, %CrewX_15%, %A_ScriptDir%\Settings\Coordinates.ini, Crew15-3, x


		IniWrite, %CrewY_1%, %A_ScriptDir%\Settings\Coordinates.ini, Crew1-1, y
		IniWrite, %CrewY_1%, %A_ScriptDir%\Settings\Coordinates.ini, Crew2-1, y
		IniWrite, %CrewY_1%, %A_ScriptDir%\Settings\Coordinates.ini, Crew3-1, y
		IniWrite, %CrewY_1%, %A_ScriptDir%\Settings\Coordinates.ini, Crew4-1, y
		IniWrite, %CrewY_1%, %A_ScriptDir%\Settings\Coordinates.ini, Crew5-1, y
		IniWrite, %CrewY_1%, %A_ScriptDir%\Settings\Coordinates.ini, Crew6-1, y
		IniWrite, %CrewY_1%, %A_ScriptDir%\Settings\Coordinates.ini, Crew7-1, y
		IniWrite, %CrewY_1%, %A_ScriptDir%\Settings\Coordinates.ini, Crew8-1, y
		IniWrite, %CrewY_1%, %A_ScriptDir%\Settings\Coordinates.ini, Crew9-1, y
		IniWrite, %CrewY_1%, %A_ScriptDir%\Settings\Coordinates.ini, Crew10-1, y
		IniWrite, %CrewY_1%, %A_ScriptDir%\Settings\Coordinates.ini, Crew11-1, y
		IniWrite, %CrewY_1%, %A_ScriptDir%\Settings\Coordinates.ini, Crew12-1, y
		IniWrite, %CrewY_1%, %A_ScriptDir%\Settings\Coordinates.ini, Crew13-1, y
		IniWrite, %CrewY_1%, %A_ScriptDir%\Settings\Coordinates.ini, Crew14-1, y
		IniWrite, %CrewY_1%, %A_ScriptDir%\Settings\Coordinates.ini, Crew15-1, y

		IniWrite, %CrewY_2%, %A_ScriptDir%\Settings\Coordinates.ini, Crew1-2, y
		IniWrite, %CrewY_2%, %A_ScriptDir%\Settings\Coordinates.ini, Crew2-2, y
		IniWrite, %CrewY_2%, %A_ScriptDir%\Settings\Coordinates.ini, Crew3-2, y
		IniWrite, %CrewY_2%, %A_ScriptDir%\Settings\Coordinates.ini, Crew4-2, y
		IniWrite, %CrewY_2%, %A_ScriptDir%\Settings\Coordinates.ini, Crew5-2, y
		IniWrite, %CrewY_2%, %A_ScriptDir%\Settings\Coordinates.ini, Crew6-2, y
		IniWrite, %CrewY_2%, %A_ScriptDir%\Settings\Coordinates.ini, Crew7-2, y
		IniWrite, %CrewY_2%, %A_ScriptDir%\Settings\Coordinates.ini, Crew8-2, y
		IniWrite, %CrewY_2%, %A_ScriptDir%\Settings\Coordinates.ini, Crew9-2, y
		IniWrite, %CrewY_2%, %A_ScriptDir%\Settings\Coordinates.ini, Crew10-2, y
		IniWrite, %CrewY_2%, %A_ScriptDir%\Settings\Coordinates.ini, Crew11-2, y
		IniWrite, %CrewY_2%, %A_ScriptDir%\Settings\Coordinates.ini, Crew12-2, y
		IniWrite, %CrewY_2%, %A_ScriptDir%\Settings\Coordinates.ini, Crew13-2, y
		IniWrite, %CrewY_2%, %A_ScriptDir%\Settings\Coordinates.ini, Crew14-2, y
		IniWrite, %CrewY_2%, %A_ScriptDir%\Settings\Coordinates.ini, Crew15-2, y

		IniWrite, %CrewY_3%, %A_ScriptDir%\Settings\Coordinates.ini, Crew1-3, y
		IniWrite, %CrewY_3%, %A_ScriptDir%\Settings\Coordinates.ini, Crew2-3, y
		IniWrite, %CrewY_3%, %A_ScriptDir%\Settings\Coordinates.ini, Crew3-3, y
		IniWrite, %CrewY_3%, %A_ScriptDir%\Settings\Coordinates.ini, Crew4-3, y
		IniWrite, %CrewY_3%, %A_ScriptDir%\Settings\Coordinates.ini, Crew5-3, y
		IniWrite, %CrewY_3%, %A_ScriptDir%\Settings\Coordinates.ini, Crew6-3, y
		IniWrite, %CrewY_3%, %A_ScriptDir%\Settings\Coordinates.ini, Crew7-3, y
		IniWrite, %CrewY_3%, %A_ScriptDir%\Settings\Coordinates.ini, Crew8-3, y
		IniWrite, %CrewY_3%, %A_ScriptDir%\Settings\Coordinates.ini, Crew9-3, y
		IniWrite, %CrewY_3%, %A_ScriptDir%\Settings\Coordinates.ini, Crew10-3, y
		IniWrite, %CrewY_3%, %A_ScriptDir%\Settings\Coordinates.ini, Crew11-3, y
		IniWrite, %CrewY_3%, %A_ScriptDir%\Settings\Coordinates.ini, Crew12-3, y
		IniWrite, %CrewY_3%, %A_ScriptDir%\Settings\Coordinates.ini, Crew13-3, y
		IniWrite, %CrewY_3%, %A_ScriptDir%\Settings\Coordinates.ini, Crew14-3, y
		IniWrite, %CrewY_3%, %A_ScriptDir%\Settings\Coordinates.ini, Crew15-3, y
	}
	Goto, Setup_GUI
	return
}
return


;----------------------------------------------------------------------------------------------------


									   replaceLabel(curLabel, newlabel, filePath)
{
	FileRead, fileDataStr, % filePath
	newData := StrReplace(fileDataStr, "[" curLabel "]", "[" newLabel "]")
	FileRecycle, % filePath
	sleep, 200
	FileAppend, % newData, % filePath
	return newData
}
return


;--------------------------------------------------Auto Coordinates--------------------------------------------------


Setup_GUI:
Gui, 1:Submit, nohide
IniWrite,%Ship1_checked%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Checked1
IniWrite,%Ship2_checked%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Checked2
IniWrite,%Ship3_checked%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Checked3
IniWrite,%Ship4_checked%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Checked4 
IniWrite,%Ship1%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Ship1
IniWrite,%Ship2%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Ship2
IniWrite,%Ship3%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Ship3
IniWrite,%Ship4%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Ship4 
IniWrite,%Builds_Ship1_selected%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Build1
IniWrite,%Builds_Ship2_selected%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Build2
IniWrite,%Builds_Ship3_selected%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Build3
IniWrite,%Builds_Ship4_selected%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Build4
IniWrite,%Unequip_Ships_checked%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Unequip

IniRead, Empire_X, %A_ScriptDir%\Settings\Coordinates.ini, Empire, x
IniRead, Empire_Y, %A_ScriptDir%\Settings\Coordinates.ini, Empire, y
IniRead, Federation_X, %A_ScriptDir%\Settings\Coordinates.ini, Federation, x
IniRead, Federation_Y, %A_ScriptDir%\Settings\Coordinates.ini, Federation, y
IniRead, Jericho_X, %A_ScriptDir%\Settings\Coordinates.ini, Jericho, x
IniRead, Jericho_Y, %A_ScriptDir%\Settings\Coordinates.ini, Jericho, y
IniRead, Ellydium_X, %A_ScriptDir%\Settings\Coordinates.ini, Ellydium, x
IniRead, Ellydium_Y, %A_ScriptDir%\Settings\Coordinates.ini, Ellydium, y
IniRead, Unique_X, %A_ScriptDir%\Settings\Coordinates.ini, Unique, x
IniRead, Jericho_Y, %A_ScriptDir%\Settings\Coordinates.ini, Unique, y
IniRead, Unique_X, %A_ScriptDir%\Settings\Coordinates.ini, Unique, x
IniRead, Unique_Y, %A_ScriptDir%\Settings\Coordinates.ini, Unique, y

IniRead, Scroll_X, %A_ScriptDir%\Settings\Coordinates.ini, Scroll, x
IniRead, Scroll_Y, %A_ScriptDir%\Settings\Coordinates.ini, Scroll, y
IniRead, Back_X, %A_ScriptDir%\Settings\Coordinates.ini, Back, x
IniRead, Back_Y, %A_ScriptDir%\Settings\Coordinates.ini, Back, y

IniRead, Slot1_X, %A_ScriptDir%\Settings\Coordinates.ini, Slot1, x
IniRead, Slot1_Y, %A_ScriptDir%\Settings\Coordinates.ini, Slot1, y
IniRead, Slot2_X, %A_ScriptDir%\Settings\Coordinates.ini, Slot2, x
IniRead, Slot2_Y, %A_ScriptDir%\Settings\Coordinates.ini, Slot2, y
IniRead, Slot3_X, %A_ScriptDir%\Settings\Coordinates.ini, Slot3, x
IniRead, Slot3_Y, %A_ScriptDir%\Settings\Coordinates.ini, Slot3, y
IniRead, Slot4_X, %A_ScriptDir%\Settings\Coordinates.ini, Slot4, x
IniRead, Slot4_Y, %A_ScriptDir%\Settings\Coordinates.ini, Slot4, y
IniRead, Apply_Ellydium_X, %A_ScriptDir%\Settings\Coordinates.ini, Apply_Ellydium, x
IniRead, Apply_Ellydium_Y, %A_ScriptDir%\Settings\Coordinates.ini, Apply_Ellydium, y

IniRead, Preset1_X, %A_ScriptDir%\Settings\Coordinates.ini, Preset1, x
IniRead, Preset1_Y, %A_ScriptDir%\Settings\Coordinates.ini, Preset1, y
IniRead, Preset2_X, %A_ScriptDir%\Settings\Coordinates.ini, Preset2, x
IniRead, Preset2_Y, %A_ScriptDir%\Settings\Coordinates.ini, Preset2, y
IniRead, Preset3_X, %A_ScriptDir%\Settings\Coordinates.ini, Preset3, x
IniRead, Preset3_Y, %A_ScriptDir%\Settings\Coordinates.ini, Preset3, y
IniRead, Preset4_X, %A_ScriptDir%\Settings\Coordinates.ini, Preset4, x
IniRead, Preset4_Y, %A_ScriptDir%\Settings\Coordinates.ini, Preset4, y
IniRead, PresetL_X, %A_ScriptDir%\Settings\Coordinates.ini, Load Preset, x
IniRead, PresetL_Y, %A_ScriptDir%\Settings\Coordinates.ini, Load Preset, y
IniRead, PresetYes_X, %A_ScriptDir%\Settings\Coordinates.ini, Yes, x
IniRead, PresetYes_Y, %A_ScriptDir%\Settings\Coordinates.ini, Yes, y

IniRead, CrewA_X, %A_ScriptDir%\Settings\Coordinates.ini, Crew_A, x
IniRead, CrewA_Y, %A_ScriptDir%\Settings\Coordinates.ini, Crew_A, y
IniRead, CrewB_X, %A_ScriptDir%\Settings\Coordinates.ini, Crew_B, x
IniRead, CrewB_Y, %A_ScriptDir%\Settings\Coordinates.ini, Crew_B, y
IniRead, CrewC_X, %A_ScriptDir%\Settings\Coordinates.ini, Crew_C, x
IniRead, CrewC_Y, %A_ScriptDir%\Settings\Coordinates.ini, Crew_C, y
IniRead, CrewD_X, %A_ScriptDir%\Settings\Coordinates.ini, Crew_D, x
IniRead, CrewD_Y, %A_ScriptDir%\Settings\Coordinates.ini, Crew_D, y

IniRead, Crew1_1_X, %A_ScriptDir%\Settings\Coordinates.ini, Crew1-1, x
IniRead, Crew1_1_Y, %A_ScriptDir%\Settings\Coordinates.ini, Crew1-1, y
IniRead, Crew15_3_X, %A_ScriptDir%\Settings\Coordinates.ini, Crew15-3, x
IniRead, Crew15_3_Y, %A_ScriptDir%\Settings\Coordinates.ini, Crew15-3, y
IniRead, CrewImplant_X, %A_ScriptDir%\Settings\Coordinates.ini, Implant, x
IniRead, CrewImplant_Y, %A_ScriptDir%\Settings\Coordinates.ini, Implant, y
IniRead, implant_color, %A_ScriptDir%\Settings\Coordinates.ini, Implant, implant_color


;---------- Removing old variables from .ini ----------
IniDelete, %A_ScriptDir%\Settings\Coordinates.ini, Unequip_1
IniDelete, %A_ScriptDir%\Settings\Coordinates.ini, Unequip_2
;------------------------------------------------------


Gui, 13: show
Gui, 8: +AlwaysOnTop +Toolwindow
Gui, 8: Color, 000000
Gui, 8: Font, cWhite s12, Arial


Gui, 8: Add, Text, x0 y10 w600 center, -------------------- Setup --------------------
Gui, 8: Add, Text, x300 y40 h350 0x11 ;White Line

Gui, 8: Add, Text, vText1 x30 y40 w200 h30, Empire:
Gui, 8: Add, Text, vText2 x30 y70 w200 h30, Federation:
Gui, 8: Add, Text, vText3 x30 y100 w200 h30, Jericho:
Gui, 8: Add, Text, vText4 x30 y130 w200 h30, Ellydium:
Gui, 8: Add, Text, vText5 x30 y160 w200 h30, Unique:
Gui, 8: Add, Text, vText6 x30 y190 w200 h30, Scroll:
Gui, 8: Add, Text, vText7 x30 y220 w200 h30, Back:
Gui, 8: Add, Text, vText8 x30 y250 w200 h30, Ship Slot 1:
Gui, 8: Add, Text, vText9 x30 y280 w200 h30, Ship Slot 2:
Gui, 8: Add, Text, vText10 x30 y310 w200 h30, Ship Slot 3:
Gui, 8: Add, Text, vText11 x30 y340 w200 h30, Ship Slot 4:
Gui, 8: Add, Text, vText27 x30 y370 w200 h30, Apply Ellydium:

Gui, 8: Add, Text, vText12 x330 y40 w200 h30, Preset 1:
Gui, 8: Add, Text, vText13 x330 y70 w200 h30, Preset 2:
Gui, 8: Add, Text, vText14 x330 y100 w200 h30, Preset 3:
Gui, 8: Add, Text, vText15 x330 y130 w200 h30, Preset 4:
Gui, 8: Add, Text, vText16 x330 y160 w200 h30, Preset Load:
Gui, 8: Add, Text, vText17 x330 y190 w200 h30, Preset Yes:
Gui, 8: Add, Text, vText18 x330 y220 w200 h30, Crew A:
Gui, 8: Add, Text, vText19 x330 y250 w200 h30, Crew B:
Gui, 8: Add, Text, vText20 x330 y280 w200 h30, Crew C:
Gui, 8: Add, Text, vText21 x330 y310 w200 h30, Crew D:
Gui, 8: Add, Text, vText22 x330 y340 w200 h30, Crew 1-1:
Gui, 8: Add, Text, vText23 x330 y370 w200 h30, Crew 15-3:
Gui, 8: Add, Text, vText24 x330 y400 w200 h35, Implant:`nColor:



Gui, 8: Add, Button, gEdit_Text1 x240 y38 w50 h20, Edit
Gui, 8: Add, Button, gEdit_Text2 x240 y68 w50 h20, Edit
Gui, 8: Add, Button, gEdit_Text3 x240 y98 w50 h20, Edit
Gui, 8: Add, Button, gEdit_Text4 x240 y128 w50 h20, Edit
Gui, 8: Add, Button, gEdit_Text5 x240 y158 w50 h20, Edit
Gui, 8: Add, Button, gEdit_Text6 x240 y188 w50 h20, Edit
Gui, 8: Add, Button, gEdit_Text7 x240 y218 w50 h20, Edit
Gui, 8: Add, Button, gEdit_Text8 x240 y248 w50 h20, Edit
Gui, 8: Add, Button, gEdit_Text9 x240 y278 w50 h20, Edit
Gui, 8: Add, Button, gEdit_Text10 x240 y308 w50 h20, Edit
Gui, 8: Add, Button, gEdit_Text11 x240 y338 w50 h20, Edit
Gui, 8: Add, Button, gEdit_Text27 x240 y368 w50 h20, Edit

Gui, 8: Add, Button, gEdit_Text12 x540 y38 w50 h20, Edit
Gui, 8: Add, Button, gEdit_Text13 x540 y68 w50 h20, Edit
Gui, 8: Add, Button, gEdit_Text14 x540 y98 w50 h20, Edit
Gui, 8: Add, Button, gEdit_Text15 x540 y128 w50 h20, Edit
Gui, 8: Add, Button, gEdit_Text16 x540 y158 w50 h20, Edit
Gui, 8: Add, Button, gEdit_Text17 x540 y188 w50 h20, Edit
Gui, 8: Add, Button, gEdit_Text18 x540 y218 w50 h20, Edit
Gui, 8: Add, Button, gEdit_Text19 x540 y248 w50 h20, Edit
Gui, 8: Add, Button, gEdit_Text20 x540 y278 w50 h20, Edit
Gui, 8: Add, Button, gEdit_Text21 x540 y308 w50 h20, Edit
Gui, 8: Add, Button, gEdit_Text22 x540 y338 w50 h20, Edit
Gui, 8: Add, Button, gEdit_Text23 x540 y368 w50 h20, Edit
Gui, 8: Add, Button, gEdit_Text24 x540 y403 w50 h20, Edit

Gui, 8: Add, Button, gSetup_save x215 y475 w80 h30, Continue
Gui, 8: Add, Button, gSetup_cancel x305 y475 w80 h30, Exit App


Gui, 13: hide
Gui, 8: Show, x100 y100 h520 w600, Setup
Gui, 1: destroy

If (Empire_X != "ERROR")
{
GuiControl, 8: text, Text1, Empire:   x%Empire_X% y%Empire_Y%
}

If (Federation_X != "ERROR")
{
GuiControl, 8: text, Text2, Federation:   x%Federation_X% y%Federation_Y%
}

If (Jericho_X != "ERROR")
{
GuiControl, 8: text, Text3, Jericho:   x%Jericho_X% y%Jericho_Y%
}

If (Ellydium_X != "ERROR")
{
GuiControl, 8: text, Text4, Ellydium:   x%Ellydium_X% y%Ellydium_Y%
}

If (Unique_X != "ERROR")
{
GuiControl, 8: text, Text5, Unique:   x%Unique_X% y%Unique_Y%
}

If (Scroll_X != "ERROR")
{
GuiControl, 8: text, Text6, Scroll:   x%Scroll_X% y%Scroll_Y%
}

If (Back_X != "ERROR")
{
GuiControl, 8: text, Text7, Back:   x%Back_X% y%Back_Y%
}

If (Slot1_X != "ERROR")
{
GuiControl, 8: text, Text8, Ship Slot 1:   x%Slot1_X% y%Slot1_Y%
}

If (Slot2_X != "ERROR")
{
GuiControl, 8: text, Text9, Ship Slot 2:   x%Slot2_X% y%Slot2_Y%
}

If (Slot3_X != "ERROR")
{
GuiControl, 8: text, Text10, Ship Slot 3:   x%Slot3_X% y%Slot3_Y%
}

If (Slot4_X != "ERROR")
{
GuiControl, 8: text, Text11, Ship Slot 4:   x%Slot4_X% y%Slot4_Y%
}

If (Preset1_X != "ERROR")
{
GuiControl, 8: text, Text12, Preset 1:   x%Preset1_X% y%Preset1_Y%
}

If (Preset2_X != "ERROR")
{
GuiControl, 8: text, Text13, Preset 2:   x%Preset2_X% y%Preset2_Y%
}

If (Preset3_X != "ERROR")
{
GuiControl, 8: text, Text14, Preset 3:   x%Preset3_X% y%Preset3_Y%
}

If (Preset4_X != "ERROR")
{
GuiControl, 8: text, Text15, Preset 4:   x%Preset4_X% y%Preset4_Y%
}

If (PresetL_X != "ERROR")
{
GuiControl, 8: text, Text16, Preset Load:   x%PresetL_X% y%PresetL_Y%
}

If (PresetYes_X != "ERROR")
{
GuiControl, 8: text, Text17, Preset Yes:   x%PresetYes_X% y%PresetYes_Y%
}

If (CrewA_X != "ERROR")
{
GuiControl, 8: text, Text18, Crew A:   x%CrewA_X% y%CrewA_Y%
}

If (CrewB_X != "ERROR")
{
GuiControl, 8: text, Text19, Crew B:   x%CrewB_X% y%CrewB_Y%
}

If (CrewC_X != "ERROR")
{
GuiControl, 8: text, Text20, Crew C:   x%CrewC_X% y%CrewC_Y%
}

If (CrewD_X != "ERROR")
{
GuiControl, 8: text, Text21, Crew D:   x%CrewD_X% y%CrewD_Y%
}

If (Crew1_1_X != "ERROR")
{
GuiControl, 8: text, Text22, Crew 1-1:   x%Crew1_1_X% y%Crew1_1_Y%
}

If (Crew15_3_X != "ERROR")
{
GuiControl, 8: text, Text23, Crew 15-3:   x%Crew15_3_X% y%Crew15_3_Y%
}

If (CrewImplant_X != "ERROR")
{
GuiControl, 8: text, Text24, Implant:   x%CrewImplant_X% y%CrewImplant_Y%`nColor:     %implant_color%
}

If (Apply_Ellydium_X != "ERROR")
{
GuiControl, 8: text, Text27, Apply Elly:  x%Apply_Ellydium_X% y%Apply_Ellydium_Y%
}


return


Edit_Text1:
Hotkey, LButton, On
Loaded := "Empire"
Gui, 8: destroy
return

Edit_Text2:
Hotkey, LButton, On
Loaded := "Federation"
Gui, 8: destroy
return

Edit_Text3:
Hotkey, LButton, On
Loaded := "Jericho"
Gui, 8: destroy
return

Edit_Text4:
Hotkey, LButton, On
Loaded := "Ellydium"
Gui, 8: destroy
return

Edit_Text5:
Hotkey, LButton, On
Loaded := "Unique"
Gui, 8: destroy
return

Edit_Text6:
Hotkey, LButton, On
Loaded := "Scroll"
Gui, 8: destroy
return

Edit_Text7:
Hotkey, LButton, On
Loaded := "Back"
Gui, 8: destroy
return

Edit_Text8:
Hotkey, LButton, On
Loaded := "Slot1"
Gui, 8: destroy
return

Edit_Text9:
Hotkey, LButton, On
Loaded := "Slot2"
Gui, 8: destroy
return

Edit_Text10:
Hotkey, LButton, On
Loaded := "Slot3"
Gui, 8: destroy
return

Edit_Text11:
Hotkey, LButton, On
Loaded := "Slot4"
Gui, 8: destroy
return

Edit_Text12:
Hotkey, LButton, On
Loaded := "Preset1"
Gui, 8: destroy
return

Edit_Text13:
Hotkey, LButton, On
Loaded := "Preset2"
Gui, 8: destroy
return

Edit_Text14:
Hotkey, LButton, On
Loaded := "Preset3"
Gui, 8: destroy
return

Edit_Text15:
Hotkey, LButton, On
Loaded := "Preset4"
Gui, 8: destroy
return

Edit_Text16:
Hotkey, LButton, On
Loaded := "Load Preset"
Gui, 8: destroy
return

Edit_Text17:
Hotkey, LButton, On
Loaded := "Yes"
Gui, 8: destroy
return

Edit_Text18:
Hotkey, LButton, On
Loaded := "Crew_A"
Gui, 8: destroy
return

Edit_Text19:
Hotkey, LButton, On
Loaded := "Crew_B"
Gui, 8: destroy
return

Edit_Text20:
Hotkey, LButton, On
Loaded := "Crew_C"
Gui, 8: destroy
return

Edit_Text21:
Hotkey, LButton, On
Loaded := "Crew_D"
Gui, 8: destroy
return

Edit_Text22:
Hotkey, LButton, On
Loaded := "Crew1-1"
Gui, 8: destroy
Crew_Calc := 1
return

Edit_Text23:
Hotkey, LButton, On
Loaded := "Crew15-3"
Gui, 8: destroy
Crew_Calc := 1
return

Edit_Text24:
Hotkey, LButton, On
Loaded := "Implant"
Gui, 8: destroy
return

Edit_Text27:
Hotkey, LButton, On
Loaded := "Apply_Ellydium"
Gui, 8: destroy
return


Setup_Save:
Reload
return


~WheelUp::
    MouseWheelCounter++
	Goto, MouseWheelToolTip
return

~WheelDown::
    MouseWheelCounter--
	Goto, MouseWheelToolTip
return

~RButton::
	If MouseWheelCounter >= 1
	{
		Gui, 4:Submit, nohide
		Gui, 5:Submit, nohide
		If Add_New_Ship_Scroll = Up
		{
			GuiControl, 4: , Add_New_Ship_Scroll_amount, %MouseWheelCounter%
		}
		
		If Add_New_Ship_Scroll2 = Up
		{
			GuiControl, 4: , Add_New_Ship_Scroll_amount2, %MouseWheelCounter%
		}
		
		If Edit_Ship_Scroll = Up
		{
			GuiControl, 5: , Edit_Ship_Scroll_amount, %MouseWheelCounter%
		}
		
		If Edit_Ship_Scroll2 = Up
		{
			GuiControl, 5: , Edit_Ship_Scroll_amount2, %MouseWheelCounter%
		}
		
		
	}
	
	If MouseWheelCounter <= -1
	{
		Gui, 4:Submit, nohide
		Gui, 5:Submit, nohide
		If Add_New_Ship_Scroll = Down
		{
			GuiControl, 4: , Add_New_Ship_Scroll_amount, %MouseWheelCounterToolTip%
		}
		
		If Add_New_Ship_Scroll2 = Down
		{
			GuiControl, 4: , Add_New_Ship_Scroll_amount2, %MouseWheelCounterToolTip%
		}
		
		If Edit_Ship_Scroll = Down
		{
			GuiControl, 5: , Edit_Ship_Scroll_amount, %MouseWheelCounterToolTip%
		}
		
		If Edit_Ship_Scroll2 = Down
		{
			GuiControl, 5: , Edit_Ship_Scroll_amount2, %MouseWheelCounterToolTip%
		}
	}
return

MouseWheelToolTip:
	If MouseWheelCounter >= 1
	{
		MouseWheelCounterToolTip := MouseWheelCounter
		Tooltip, Up: %MouseWheelCounterToolTip%
	}
	If MouseWheelCounter = 0
	{
		MouseWheelCounterToolTip := MouseWheelCounter
		Tooltip, %MouseWheelCounterToolTip%
	}
	If MouseWheelCounter <= -1
	{
		MouseWheelCounterToolTip := -MouseWheelCounter
		Tooltip, Down: %MouseWheelCounterToolTip%
	}
return

RemoveToolTip:
~MButton::
ToolTip
MouseWheelCounter = 0
return


Break_Impant_Loop:
BlockInput, MouseMoveOff
Msgbox, Color of implant button not found. Closing script.
ExitApp
return


;------------------------------------------------------------ Ellydium integration ------------------------------------------------------------


LoadEllydiumShipData(shipName, loadoutName := "")
{
    global CurrentShipContext

    ; Initialize
    CurrentShipContext := {}
	CurrentShipContext.ShipName := shipName
    CurrentShipContext.Nodes := {}
    CurrentShipContext.NodeStates := {}
    CurrentShipContext.MaxPoints := 0
    CurrentShipContext.BranchMinimums := {}
    CurrentShipContext.NodeColors := {}

    setupFile := A_ScriptDir . "\Builds\Ellydium\" . shipName . ".ini"
    buildFile := A_ScriptDir . "\Builds\" . shipName . ".ini"
	CoordinatesFile := A_ScriptDir . "\Settings\Coordinates.ini"

    ; Read full .ini content
    FileRead, iniContent, %setupFile%
    currentSection := ""

    Loop, Parse, iniContent, `n, `r
    {
        line := Trim(A_LoopField)
        if (line = "")
            continue

        if (RegExMatch(line, "^\[(.*)\]$", m)) ; New Section
        {
            currentSection := m1
            continue
        }

        if (currentSection = "")
            continue

        StringSplit, kv, line, =
        key := Trim(kv1)
        value := Trim(kv2)

        ; --- special case for Ship_tree_Points ---
        if (currentSection = "Ship_tree_Points")
        {
            if (key = "Max")
                CurrentShipContext.MaxPoints := value
            else if (RegExMatch(key, "Tree(\d+)", mTree))
                CurrentShipContext.BranchMinimums[mTree1] := value
            continue
        }

        ; --- normal nodes ---
        if (key = "x" or key = "y" or key = "Effect" or key = "Branch" or key = "Cost")
        {
            if (!IsObject(CurrentShipContext.Nodes[currentSection]))
                CurrentShipContext.Nodes[currentSection] := {}

            CurrentShipContext.Nodes[currentSection][key] := value
        }
    }

    ; --- Load Build Data if loadoutName is provided ---
    if (loadoutName != "")
    {
        loadoutSection := loadoutName . "|"
		IniRead, buildContent, %buildFile%, %loadoutSection%


        if (buildContent != "ERROR")
        {
            Loop, Parse, buildContent, `n, `r
            {
                line := Trim(A_LoopField)
                if (line = "" or RegExMatch(line, "^\[.*\]$"))
                    continue

                StringSplit, kv, line, =
                key := Trim(kv1)
                value := Trim(kv2)

                if (CurrentShipContext.Nodes.HasKey(key))
                {
                    CurrentShipContext.NodeStates[key] := (value = "1") ? 1 : 0
                }
            }
        }
    }
    else
    {
        for sectionName, _ in CurrentShipContext.Nodes
            CurrentShipContext.NodeStates[sectionName] := 0
    }
	
	
	; --- Load Setup_Colors ---
	colorKeys := ["Normal_ON", "Normal_OFF", "Spec_ON", "Spec_OFF"]
	for index, key in colorKeys
	{
		IniRead, cVal, %CoordinatesFile%, Setup_Colors, %key%
		if (cVal != "ERROR")
			CurrentShipContext.NodeColors[key] := cVal
	}
	
	
	if (CurrentShipContext.Nodes.Count() = 0)
	{
		MsgBox, 48, Error, The Ellydium setup file for '%shipName%' has no nodes defined.`nPlease set up coordinates first.
		return false
	}

	if (!CurrentShipContext.BranchMinimums.HasKey(1) || CurrentShipContext.MaxPoints = "")
	{
		MsgBox, 48, Error, The Ellydium file for '%shipName%' is missing tree point data.`nDid you forget to define [Ship_tree_Points]?
		return false
	}
	return true
}




BuildSetupGUI()
{
    global CurrentShipContext
    global selectedCategory

    Gui, 17:+Resize +Toolwindow +AlwaysOnTop
    Gui, 17:Color, Black
    Gui, 17:Font, cWhite s12, Segoe UI

    selectedCategory := ""

    ; Top Title
    Gui, 17:Add, Text, x0 y10 w650 Center, Coordinate Setup Tool

    ; Categories
    categories := ["CPU", "Hull", "Shield", "Capacitor", "Engine", "Utility", "Offence", "Defence", "SpecMod"]

    xpos_start := 50
    ypos_start := 70
    colGap := 180
    rowGap := 100
    btnW := 150
    btnH := 50

    for index, cat in categories
    {
        col := Mod(index-1, 3)
        row := Floor((index-1) / 3)

        xpos := xpos_start + (col * colGap)
        ypos := ypos_start + (row * rowGap)

        Gui, 17:Add, Button, x%xpos% y%ypos% w%btnW% h%btnH% gCategorySelect, %cat%
    }

    ; Setup Node Colors Button
    Gui, 17:Add, Button, x120 y420 w180 h40 gShowColorSetupMenu, Setup Node Colors
	Gui, 17:Add, Button, x320 y420 w180 h40 gCheckNodeStatesFromSetupGUI, Check Nodes



    ; Exit Button
    Gui, 17:Add, Button, x220 y480 w180 h40 gExitProgram, Exit

    Gui, 17:Show, x100 y100 w620 h550, Coordinate Setup
}



ShowCategory(category)
{
    global CurrentShipContext
    global selectedCategory

    selectedCategory := category

    Gui, 17:Destroy
    Gui, 17:New
    Gui, 17:+AlwaysOnTop +Toolwindow
    Gui, 17:Color, Black
    Gui, 17:Font, cWhite s14 wBold, Segoe UI
    Gui, 17:Add, Text, x10 y10 w1400 Center, %category% Setup

    ; Fetch entries
    entries := []

    for section, values in CurrentShipContext.Nodes
    {
        if (InStr(section, category . "_"))
            entries.Push({section: section, values: values})
    }

    ; Build grid
    xpos_start := 100
    ypos_start := 80
    colGap := 300
    rowGap := 135

	for i, entry in entries
	{
		col := Mod(i-1, 4)
		row := Floor((i-1) / 4)

		xpos := xpos_start + (col * colGap)
		ypos := ypos_start + (row * rowGap)

		section := entry.section
		values := entry.values
		displayEffect := values["Effect"] ? values["Effect"] : "(No effect text)"
		displayX := values["x"] ? values["x"] : "-"
		displayY := values["y"] ? values["y"] : "-"

		; Pre-calculate Y positions
		yTitle := ypos
		yEffect := ypos + 22
		yCoords := ypos + 65
		yButton := ypos + 97
		xXCoord := xpos + 20
		xYCoord := xpos + 110
		centerBtnX := xpos + 40

		; Section Title
		Gui, 17:Font, cWhite s12 wBold, Segoe UI
		branch := values["Branch"] ? values["Branch"] : "?"
		Gui, 17:Add, Text, x%xpos% y%yTitle% w200 Center, %section% (Branch: %branch%)

		; Effect Text
		Gui, 17:Font, cWhite s11, Segoe UI
		Gui, 17:Add, Text, x%xpos% y%yEffect% w200 h43 Center, %displayEffect%

		; X and Y Texts
		Gui, 17:Font, % (displayX = "-" ? "cRed" : "cWhite") " s11", Segoe UI
		Gui, 17:Add, Text, x%xXCoord% y%yCoords% w80 Left, % "X: " displayX

		Gui, 17:Font, % (displayY = "-" ? "cRed" : "cWhite") " s11", Segoe UI
		Gui, 17:Add, Text, x%xYCoord% y%yCoords% w80 Left, % "Y: " displayY

		; Set Coordinates Button
		Gui, 17:Font, cWhite s11, Segoe UI
		Gui, 17:Add, Button, x%centerBtnX% y%yButton% w120 h26 gSetCoord17 vBtn_%section%, Set Coordinates

		if (i >= 12)
			break
	}

    ; Back Button
    Gui, 17:Add, Button, x600 y480 w200 h50 gShowMainMenu, Back

    Gui, 17:Show, x100 y100, Coordinate Setup
}



BuildEllydiumTreeGUI()
{
    global CurrentShipContext, TotalPointsCounter
	CurrentShipContext.ShipName := Edit_Loadout_Ship_selected
	CurrentShipContext.LoadoutName := Edit_Loadout_Loadout_selected

    Gui, 17:Destroy
    Gui, 17:New
    Gui, 17:Color, Black
    Gui, 17:Font, cWhite s12 wBold, Segoe UI

    ; Layout variables
    xposStart := 20
    yposStart := 50
    colGap := 210
    rowGap := 50
    xpos := xposStart
	
    ; Organize Nodes into Branches
    BranchNodes := {}
    for sectionName, nodeData in CurrentShipContext.Nodes
    {
        branch := nodeData.Branch
        if (!BranchNodes.HasKey(branch))
            BranchNodes[branch] := []
        BranchNodes[branch].Push(sectionName)
    }

    ; Total points counter
	branchCount := BranchNodes.Count()
	guiWidth := xposStart + (branchCount * colGap)
	pointsX := guiWidth-320  ; adjust padding as needed
    maxPoints := CurrentShipContext.MaxPoints
	Gui, 17:Add, Text, vTotalPointsCounter x%pointsX% y10 w300 Right, Points: 0 / %maxPoints%
	
    ; Draw Branches
    for branchNum, nodeList in BranchNodes
	{
		ypos := yposStart

		; Check if branchMin is loaded correctly
		branchMin := CurrentShipContext.BranchMinimums[branchNum]
		if (branchMin = "")
		{
			MsgBox, Error: Missing branch data for branch number %branchNum%.
			return
		}
		Gui, 6:Destroy
		; Branch title
		Gui, 17:Font, cWhite s12 wBold, Segoe UI
		ctrlName := "BranchTitle_" branchNum
		options := "v" ctrlName " x" xpos " y" ypos " w200 Center"
		Gui, 17:Add, Text, %options%, % "Branch " branchNum " (0/" branchMin ")" 

		ypos += 30

		; Node Checkboxes
		; Step 1: Group nodes by category
		categoryOrder := ["CPU", "Hull", "Shield", "Capacitor", "Engine", "Utility", "Offence", "Defence", "SpecMod"]
		groupedNodes := {}

		; Group nodes into their category
		for _, sectionName in nodeList
		{
			for _, cat in categoryOrder
			{
				if (InStr(sectionName, cat . "_"))
				{
					if (!IsObject(groupedNodes[cat]))
						groupedNodes[cat] := []
					groupedNodes[cat].Push(sectionName)
					break
				}
			}
		}

		; Step 2: Draw categories
		for _, category in categoryOrder
		{
			if (!groupedNodes.HasKey(category))
				continue
			Gui, 17:Font, s1 w0 cGray, Segoe UI
			Gui, 17:Add, Text, x%xpos% y%ypos% w200 h2 +0x10,  ; Line
			ypos += 10
			
			; Category label
			color := GetCategoryColor(category)
			upperCat := category
			StringUpper, upperCat, upperCat
			Gui, 17:Font, s11 Bold c%color%, Segoe UI
			Gui, 17:Add, Text, x%xpos% y%ypos% w200 Center, %upperCat%
			ypos += 25

			; 🛠️ Reset font to normal before checkboxes
			Gui, 17:Font, s8 wNormal cWhite, Segoe UI


			; Nodes under this category
			for _, sectionName in groupedNodes[category]
			{
				effectText := CurrentShipContext.Nodes[sectionName].Effect
				if (effectText = "")
					effectText := sectionName

				costText := CurrentShipContext.Nodes[sectionName].Cost
				if (costText = "")
					costText := ""

				checked := CurrentShipContext.NodeStates[sectionName]
				checkedText := (checked = 1) ? "Checked" : ""

				; Add checkbox without long label
				labelTop := sectionName . " | " . costText . " pts."
				Gui, 17:Add, Checkbox, x%xpos% y%ypos% w200 h20 vNode_%sectionName% gCheckboxClicked %checkedText%, %labelTop%
				ypos += 20
				
				xpos_effect := xpos+20
				; Add effect text label below
				Gui, 17:Add, Text, x%xpos_effect% y%ypos% w180 h40 vNodeEffect_%sectionName% cWhite, %effectText%
				ypos += rowGap - 20

			}

			ypos += 10 ; Extra spacing between categories
			Gui, 17:Font , cWhite normal s10

		}


		xpos += colGap
	}

    ; Save + Back Buttons
	DeleteButtonX := 290
    SaveButtonX := 10
    BackButtonX := 150
	CopyButtonX := 440
	PasteButtonX := 515
	ScanButtonX := 590
    ButtonsY := 5

    Gui, 17:Font, cWhite s11, Segoe UI
	Gui, 17:Add, Button, x%DeleteButtonX% y%ButtonsY% w120 h30 gDelete_ellydium_tree, Delete Tree
    Gui, 17:Add, Button, x%SaveButtonX% y%ButtonsY% w120 h30 gSave_Build, Save
    Gui, 17:Add, Button, x%BackButtonX% y%ButtonsY% w120 h30 gExitEditTree, Back
	Gui, 17:Add, Button, x%CopyButtonX% y%ButtonsY% w60 h30 gButtonCopyStates, Copy
	Gui, 17:Add, Button, x%PasteButtonX% y%ButtonsY% w60 h30 gButtonPasteStates, Paste
	Gui, 17:Add, Button, x%ScanButtonX% y%ButtonsY% w80 h30 gScan_build, Scan build

    Gui, 17:Show, , Edit Ellydium Tree | Build: %Edit_Loadout_Loadout_selected%
	Gui, 13:Hide
	
    ; --- Update GUI colors and counters ---
    UpdatePointsAndColors()
}



UpdatePointsAndColors()
{
    global CurrentShipContext

    TotalPoints := 0
    BranchPoints := {}

    ; Initialize branch points
    Loop, 15
        BranchPoints[A_Index] := 0

    ; --- Step 1: Calculate points per branch and update NodeStates
    for sectionName, nodeData in CurrentShipContext.Nodes
    {
        GuiControlGet, state, 17:, Node_%sectionName%
        if (state = 1)
        {
            CurrentShipContext.NodeStates[sectionName] := 1
            cost := nodeData.Cost
            branch := nodeData.Branch
            if (cost = "")
                cost := 0
            TotalPoints += cost
            BranchPoints[branch] += cost
        }
        else
        {
            CurrentShipContext.NodeStates[sectionName] := 0
        }
    }

    ; --- Step 2: Calculate which branches are unlocked
    UnlockedBranches := {}
    fullyUnlocked := true

    Loop, 15
    {
        branchNum := A_Index
        needed := CurrentShipContext.BranchMinimums[branchNum]

        ; Sum of all points in previous branches only
        totalPrevPoints := 0
        Loop, % (branchNum - 1)
            totalPrevPoints += BranchPoints[A_Index]

        if (needed = "")
            UnlockedBranches[branchNum] := true
        else if (fullyUnlocked && totalPrevPoints >= needed)
            UnlockedBranches[branchNum] := true
        else
        {
            UnlockedBranches[branchNum] := false
            fullyUnlocked := false
        }
    }

    ; --- Step 3: Update total points display
    maxPoints := CurrentShipContext.MaxPoints
    GuiControl, 17:, TotalPointsCounter, Points: %TotalPoints% / %maxPoints%

    ; --- Step 4: Update branch labels
    Loop, 15
    {
        if (CurrentShipContext.BranchMinimums.HasKey(A_Index))
        {
            branchMin := CurrentShipContext.BranchMinimums[A_Index]
            currentPoints := 0
            Loop, % (A_Index - 1)
                currentPoints += BranchPoints[A_Index]
            branchTitle := "Branch " A_Index " (" currentPoints "/" branchMin ")"
            GuiControl, 17:, BranchTitle_%A_Index%, %branchTitle%
        }
    }

    ; --- Step 5: Update checkbox colors and texts
    for sectionName, nodeData in CurrentShipContext.Nodes
    {
        branch := nodeData.Branch
        available := UnlockedBranches[branch] && (TotalPoints <= CurrentShipContext.MaxPoints)

        GuiControlGet, state, 17:, Node_%sectionName%

        cleanName := (SubStr(sectionName, 1, 5) = "Node_") ? SubStr(sectionName, 6) : sectionName
        costText := nodeData.Cost != "" ? nodeData.Cost : "0"
        effectText := nodeData.Effect != "" ? nodeData.Effect : sectionName

		StringReplace, cleanName, cleanName, _, %A_Space%
        labelTop := "(" . cleanName . " | " . costText . " pts.)"
        labelBottom := effectText
        labelControl := "NodeEffect_" . sectionName
		

        ; --- Default values
        symbol := "◯"
        fontOpts := "s9 wNormal"
		fontOpts_effect := "s8 wNormal"
        color := "FFFFFF"

        ; --- Logic to determine appearance
        if (!available && state = 1)
        {
            symbol := "✘"
            fontOpts := "s9 wBold"
			fontOpts_effect := "s8 wNormal"
            color := "FF0000"
        }
        else if (!available && state = 0)
        {
            symbol := "✘"
            fontOpts := "s9 wNormal"
			fontOpts_effect := "s8"
            color := "808080"
        }
        else if (available && state = 1)
        {
            symbol := "⚫"
            fontOpts := "s9 wBold"
			fontOpts_effect := "s8 wNormal"
            color := "00FF00"
        }

        ; Apply updates only once
        Gui, 17:Font, %fontOpts%, Segoe UI
        GuiControl, 17:, Node_%sectionName%, %symbol% %labelTop% %symbol%
		GuiControl, Font, Node_%sectionName%
        GuiControl, 17:+c%color%, Node_%sectionName%

        Gui, 17:Font, %fontOpts_effect%, Segoe UI
        GuiControl, 17:, %labelControl%, %labelBottom%		
		GuiControl, Font, %labelControl%
        GuiControl, 17:+c%color%, %labelControl%
		
        GuiControl, 17:+Redraw, Node_%sectionName%
		GuiControl, 17:+Redraw, NodeEffect_%sectionName%
    }
}



RunEllydiumPixelAutomation()
{
    global CurrentShipContext

    if (!IsObject(CurrentShipContext) || CurrentShipContext.Nodes.Count() = 0)
    {
        MsgBox, 48, Error, No ship context loaded!
        return
    }

    ; Load colors
    normalOn := CurrentShipContext.NodeColors["Normal_ON"]
    normalOff := CurrentShipContext.NodeColors["Normal_OFF"]
    specOff := CurrentShipContext.NodeColors["Spec_OFF"]

    ; ------------------------
    ; Phase 1: Deactivate unwanted active nodes
    ; ------------------------
    for nodeName, nodeData in CurrentShipContext.Nodes
    {
        if (CurrentShipContext.NodeStates[nodeName] = 1)
            continue

        x := nodeData.x
        y := nodeData.y
		

        PixelSearch, outX, outY, x, y, x, y, %normalOn%, 60, Fast RGB
        if (outX != "")
        {
            ClickNode(nodeName)
            Sleep, 50
			Click, 100,100,0
        }
    }
	
    ; ------------------------
    ; Phase 2: Activate needed nodes with per-node retry limit
    ; ------------------------
    completedBranches := {}
    specModActivated := false
    nodeRetryCount := {}

    loop
    {
        progressMade := false

        Loop, 15
        {
            branchNum := A_Index
            if (completedBranches[branchNum])
                continue

            ; Check if all previous branches are complete
            unlocked := true
            Loop, % (branchNum - 1)
                if (!completedBranches.HasKey(A_Index))
                    unlocked := false

            if (!unlocked)
                continue

            branchComplete := true

            for nodeName, nodeData in CurrentShipContext.Nodes
            {
                if (nodeData.Branch != branchNum)
                    continue
                if (!CurrentShipContext.NodeStates[nodeName])
                    continue
                if (IsSpecMod(nodeName))
                    continue

                ; Track retry count
                if (!nodeRetryCount.HasKey(nodeName))
                    nodeRetryCount[nodeName] := 0
                if (nodeRetryCount[nodeName] >= 20)
                    continue  ; Skip node after 20 failed attempts

                x := nodeData.x
                y := nodeData.y

                PixelSearch, outX, outY, x, y, x, y, %normalOff%, 40, Fast RGB
                if (ErrorLevel = 0)
                {
                    ClickNode(nodeName)
                    Sleep, 50
                    Click, 100, 100, 0

                    nodeRetryCount[nodeName]++
                    branchComplete := false
                    progressMade := true
                }
            }

            if (branchComplete)
                completedBranches[branchNum] := true

            ; Try SpecMod only once
            if (!specModActivated && TryActivateSpecMod(specOff))
            {
                progressMade := true
                specModActivated := true
            }
        }

        if (!progressMade)
            break
    }

    ; ------------------------
    ; Phase 3: Final SpecMod retry
    ; ------------------------
    TryActivateSpecMod(specOff)

    ; ------------------------
    ; Phase 4: Final apply click
    ; ------------------------
    IniRead, ApplyX, %A_ScriptDir%\Settings\Coordinates.ini, Apply_Ellydium, x
    IniRead, ApplyY, %A_ScriptDir%\Settings\Coordinates.ini, Apply_Ellydium, y

    MouseMove, %ApplyX%, %ApplyY%, 10
    Sleep, 200
    Click
    Sleep, 500

    ; ------------------------
    ; Phase 5: Check for missed nodes
    ; ------------------------
	wronglyActive := []
	for nodeName, nodeData in CurrentShipContext.Nodes
	{
		if (CurrentShipContext.NodeStates[nodeName] = 1)
			continue
		if (IsSpecMod(nodeName))
			continue

		x := nodeData.x
		y := nodeData.y
		PixelSearch, outX, outY, x, y, x, y, %normalOn%, 60, Fast RGB
		if (ErrorLevel = 0)
			wronglyActive.Push(nodeName)
	}

	if (wronglyActive.Length())
	{
		list := ""
		for i, name in wronglyActive
			list .= name "`n"
		MsgBox, 48, Error, These nodes should NOT be active:`n`n%list%
		return
	}

    missed := []
    for nodeName, nodeData in CurrentShipContext.Nodes
    {
        if (!CurrentShipContext.NodeStates[nodeName])
            continue
        if (IsSpecMod(nodeName))
            continue

        x := nodeData.x
        y := nodeData.y
        PixelSearch, outX, outY, x, y, x, y, %normalOff%, 40, Fast RGB
        if (ErrorLevel = 0)
            missed.Push(nodeName)
    }

    if (missed.Length())
    {
        list := ""
        for i, name in missed
            list .= name "`n"
        ;MsgBox, 48, Warning, Some nodes were not activated:`n`n%list%
    }
    else
    {
    }
}



CheckNodeStatesFromSetupGUI()
{
    global CurrentShipContext, specOn, specOff, normalOn, normalOff, CurrentNodeState
	
	CurrentNodeState := {}
    if (!IsObject(CurrentShipContext) || CurrentShipContext.Nodes.Count() = 0)
    {
        MsgBox, 48, Error, No ship context loaded!
        return
    }

    normalOn := CurrentShipContext.NodeColors["Normal_ON"]
    normalOff := CurrentShipContext.NodeColors["Normal_OFF"]
    specOn := CurrentShipContext.NodeColors["Spec_ON"]
    specOff := CurrentShipContext.NodeColors["Spec_OFF"]

    ; ------------------ Step 1: Prepare ------------------
	Gui, 17: Hide
    MsgBox, 64, Step 1, Please disable ALL nodes and make sure ONLY SpecMod_1 is active.`n`nClick OK when ready to scan.
	WinActivate, ahk_class game_main_window
	; ------------------ Step 2: Check OFF state ------------------
	failedNodes := []
	for nodeName, nodeData in CurrentShipContext.Nodes
	{
		x := nodeData.x
		y := nodeData.y

		if (InStr(nodeName, "SpecMod_"))
		{
			if (nodeName = "SpecMod_1")
			{
				PixelSearch, outX, outY, x, y, x, y, %specOn%, 60, Fast RGB
				if (outX = "")
					failedNodes.Push(nodeName)
			}
			else
			{
				PixelSearch, outX, outY, x, y, x, y, %specOff%, 60, Fast RGB
				if (outX = "")
					failedNodes.Push(nodeName)
			}
		}
		else
		{
			PixelSearch, outX, outY, x, y, x, y, %normalOff%, 40, Fast RGB
			if (outX = "")
				failedNodes.Push(nodeName)
		}
	}

	if (failedNodes.Length())
	{
		list := ""
		for i, name in failedNodes
			list .= name "`n"
		MsgBox, 48, Error, These nodes did NOT match expected OFF state:`n`n%list%
	}



    ; ------------------ Step 3: Detection Phase ------------------
    MsgBox, 64, Step 2, Now activate each node once.`nThey will be marked green when detected.`nClick OK to start.

    detection := {}
    specOnCheck := {}, specOffCheck := {}

    Gui, 98:Destroy
    Gui, 98:+AlwaysOnTop
    Gui, 98:Color, Black
    Gui, 98:Font, cWhite s10, Segoe UI
    Gui, 98:Add, Text, x10 y10 w480 Center, Node Detection Progress (Activate each node once)

	; -------- Group + Sort Nodes --------
	branchGroups := {}
	categoryOrder := ["CPU", "Hull", "Shield", "Capacitor", "Engine", "Offence", "Defence", "Utility", "SpecMod"]

	for nodeName, nodeData in CurrentShipContext.Nodes
	{
		branch := nodeData.Branch
		if (!branchGroups.HasKey(branch))
			branchGroups[branch] := []

		branchGroups[branch].Push(nodeName)
	}

	; Sort each branch group by category order
	for branchNum, nodeList in branchGroups
	{
		sortable := []

		for index, nodeName in nodeList
		{
			; Extract category like "CPU" from "CPU_1"
			cat := SubStr(nodeName, 1, InStr(nodeName, "_") - 1)

			; Get sort index from categoryOrder
			sortIndex := 999
			for i, catName in categoryOrder
			{
				if (catName = cat)
				{
					sortIndex := i
					break
				}
			}

			; Also extract numeric part for secondary sort
			RegExMatch(nodeName, ".*_(\d+)", m)
			nodeIndex := m1

			sortable.Push({Name: nodeName, Order: sortIndex, Index: nodeIndex})
		}

		; Manual sort: bubble sort based on Order and Index
		Loop, % sortable.Length() - 1
		{
			Loop, % sortable.Length() - A_Index
			{
				i := A_Index
				a := sortable[i]
				b := sortable[i + 1]

				if (a.Order > b.Order || (a.Order = b.Order && a.Index > b.Index))
				{
					temp := sortable[i]
					sortable[i] := sortable[i + 1]
					sortable[i + 1] := temp
				}
			}
		}


		; Replace node list
		sortedList := []
		for _, entry in sortable
			sortedList.Push(entry.Name)

		branchGroups[branchNum] := sortedList
	}



	; -------- Build Detection GUI (Horizontal Branch Layout) --------
	xStart := 20
	yStart := 40
	xpos := xStart
	maxY := yStart

	for branchNum, sortedNodes in branchGroups
	{
		ypos := yStart

		Gui, 98:Add, Text, x%xpos% y%ypos% w160 Center cGray, Branch %branchNum%
		ypos += 22

		for _, nodeName in sortedNodes
		{
			Gui, 98:Add, Text, x%xpos% y%ypos% w160 vScan_%nodeName%,❓ - %nodeName% - 
			ypos += 20
		}

		; Update maxY for final window height
		if (ypos > maxY)
			maxY := ypos

		xpos += 170  ; Move to next column for next branch
	}

	; Place Finish button at bottom-left
	ButtonY := maxY+20
	Gui, 98:Add, Button, x10 y%ButtonY% w120 h30 gEndDetection, Finish

	; Dynamically size the window
	windowWidth := xpos + 20
	windowHeight := maxY + 60
	Gui, 98:Show, w%windowWidth% h%windowHeight% x20 y20, Node Scanner



    SetTimer, WatchNodes_Progress, 1000
    return

	; ------------------ Watcher ------------------
	WatchNodes_Progress:
	for nodeName, nodeData in CurrentShipContext.Nodes
	{
		x := nodeData.x
		y := nodeData.y
		isSpec := InStr(nodeName, "SpecMod_")
		status := "❓ - " ; fallback

		if (isSpec)
		{
			PixelSearch, offX, offY, x, y, x, y, %specOff%, 60, Fast RGB
			if (offX != "")
			{
				status := "❌ OFF - "
			}
			else
			{
				PixelSearch, onX, onY, x, y, x, y, %specOn%, 60, Fast RGB
				if (onX != "")
					status := "✅ ON - "
			}
		}
		else
		{
			; If already confirmed, keep it green
			if (CurrentNodeState[nodeName] = 1)
			{
				status := "✅ - "
			}
			else
			{
				PixelSearch, onX, onY, x, y, x, y, %normalOn%, 60, Fast RGB
				if (onX != "")
				{
					status := "✅ - "
					if IsGameFocused()
						CurrentNodeState[nodeName] := 1
				}
				else
				{
					status := "❌ - "
					if IsGameFocused() && !CurrentNodeState.HasKey(nodeName)
						CurrentNodeState[nodeName] := 0
				}
			}
		}
		
		if (InStr(status, "✅"))
			GuiControl, 98:+c00FF00, Scan_%nodeName%  ; Green
		else if (InStr(status, "❌"))
			GuiControl, 98:+cFF4444, Scan_%nodeName%  ; Red
		else
			GuiControl, 98:+cFFFFFF, Scan_%nodeName%  ; Default/fallback
			
		GuiControl, 98:, Scan_%nodeName%, %status%%nodeName%


	}
	return




    if (allDone)
    {
        SetTimer, WatchNodes_Progress, Off
        Gui, 98:Add, Text, x100 y+10 w300 Center cLime, ✅ All nodes detected!
    }
    return

    ; ------------------ Finish Button ------------------
    EndDetection:
    SetTimer, WatchNodes_Progress, Off
    Gui, 98:Destroy
    BuildSetupGUI()
    return
}



CopyNodeStates()
{
    global EllydiumCopiedStates, EllydiumCopiedShipID, CurrentShipContext

    if (!IsObject(CurrentShipContext) || CurrentShipContext.Nodes.Count() = 0)
    {
        MsgBox, 48, Error, No ship context loaded!
        return
    }

    EllydiumCopiedStates := {}
    for nodeName, state in CurrentShipContext.NodeStates
        EllydiumCopiedStates[nodeName] := state

    EllydiumCopiedShipID := CurrentShipContext.ShipName
    MsgBox, 64, Copied, Node state copied for ship: %EllydiumCopiedShipID%
}



PasteNodeStates()
{
    global EllydiumCopiedStates, EllydiumCopiedShipID, CurrentShipContext

    if (!IsObject(CurrentShipContext) || CurrentShipContext.Nodes.Count() = 0)
    {
        MsgBox, 48, Error, No ship context loaded!
        return
    }

    if (EllydiumCopiedShipID != CurrentShipContext.ShipName)
    {
        MsgBox, 48, Error, This copied state is for a different ship.
        return
    }

    shipName := CurrentShipContext.ShipName
    buildName := CurrentShipContext.LoadoutName
    if (buildName = "")
    {
        MsgBox, 48, Error, No build selected!
        return
    }

    iniFile := A_ScriptDir . "\Builds\" . shipName . ".ini"
    section := buildName . "|"

    ; Apply copied states to context and update GUI
    for nodeName, copiedState in EllydiumCopiedStates
    {
        if (!CurrentShipContext.Nodes.HasKey(nodeName))
            continue

        ; Update state
        CurrentShipContext.NodeStates[nodeName] := copiedState

        ; Update checkbox in GUI
        ctrlName := "Node_" . nodeName
        GuiControl, 17:, %ctrlName%, %copiedState%
    }

    ; Write to INI
    for nodeName, state in CurrentShipContext.NodeStates
    {
        IniWrite, %state%, %iniFile%, %section%, %nodeName%
    }

    ; Update counters and visuals
    UpdatePointsAndColors()

    MsgBox, 64, Done, Node states pasted and written to build:`n%buildName%
}




; --- Helper function: Check if section is a SpecMod ---



IsGameFocused()
{
    WinGetClass, winClass, A
    return (winClass = "game_main_window")
}



; Category title appearance
GetCategoryColor(category)
{
    if (category = "Hull")
        return "00FF00"
    else if (category = "Shield")
        return "3399FF"
    else if (category = "Capacitor")
        return "FFFF00"
    else if (category = "CPU")
        return "FFA500"
    else if (category = "Engine")
        return "CC66FF"
    else if (category = "Utility")
        return "00CCCC"
    else if (category = "Offence")
        return "FF3333"
    else if (category = "Defence")
        return "00FFFF"
    else if (category = "SpecMod")
        return "3399FF"
    return "FFFFFF"
}



IsSpecMod(sectionName)
{
    return InStr(sectionName, "SpecMod_")
}



ClickNode(sectionName)
{
    global CurrentShipContext
    x := CurrentShipContext.Nodes[sectionName].x
    y := CurrentShipContext.Nodes[sectionName].y
    Click, %x%, %y%
}



TryActivateSpecMod(specOffColor)
{
    global CurrentShipContext

    desiredSpec := ""
    for nodeName, state in CurrentShipContext.NodeStates
    {
        if (IsSpecMod(nodeName) && state = 1)
        {
            desiredSpec := nodeName
            break
        }
    }

    if (desiredSpec = "")
        return false  ; nothing to activate

    ; Check if it's already activated (no swap needed)
    node := CurrentShipContext.Nodes[desiredSpec]
    PixelSearch, dx, dy, node.x, node.y, node.x, node.y, %specOffColor%, 60, Fast RGB
    if (dx = "")  ; desired spec mod already ON
        return false

    ; Step 1: Click SpecMod 1 first
    for nodeName, nodeData in CurrentShipContext.Nodes
    {
        if (IsSpecMod(nodeName) && nodeData.Branch = 1)
        {
            PixelSearch, sx, sy, nodeData.x, nodeData.y, nodeData.x, nodeData.y, %specOffColor%, 60, Fast RGB
            if (sx != "")
            {
                Click, %sx% %sy%
                Sleep, 150
            }
            break
        }
    }

    ; Step 2: Click the desired SpecMod
    PixelSearch, dx, dy, node.x, node.y, node.x, node.y, %specOffColor%, 60, Fast RGB
    if (dx != "")
    {
        Click, %dx% %dy%
        Sleep, 150
        return true
    }

    return false
}




IsBranchUnlocked(branchNum)
{
    global CurrentShipContext

    ; Points collected in all previous branches
    totalPrevPoints := 0
    if (branchNum > 1)
    {
        Loop, % (branchNum - 1)
        {
            branchToCheck := A_Index
            for sectionName, state in CurrentShipContext.NodeStates
            {
                if (state = 1 && CurrentShipContext.Nodes[sectionName].Branch = branchToCheck)
                    totalPrevPoints += CurrentShipContext.Nodes[sectionName].Cost
            }
        }
    }

    neededPoints := CurrentShipContext.BranchMinimums[branchNum]
    return (totalPrevPoints >= neededPoints)
}



BuildColorSetupGUI()
{
    global CurrentShipContext
    global Disp_NormalOn, Disp_NormalOff, Disp_SpecOn, Disp_SpecOff

    Gui, 17:New
    Gui, 17:Color, Black
    Gui, 17:+AlwaysOnTop +Toolwindow
    Gui, 17:Font, cWhite s11, Segoe UI
    Gui, 17:Add, Text, x0 y10 w620 Center, Setup Node Colors

    xpos_start := 100
    ypos_start := 70
    colGap := 250
    rowGap := 120
    btnHeight := 40
    labelOffset := 10

    ; Read current color values
    normalOn := CurrentShipContext.NodeColors["Normal_ON"] ? CurrentShipContext.NodeColors["Normal_ON"] : "(Not set)"
    normalOff := CurrentShipContext.NodeColors["Normal_OFF"] ? CurrentShipContext.NodeColors["Normal_OFF"] : "(Not set)"
    specOn := CurrentShipContext.NodeColors["Spec_ON"] ? CurrentShipContext.NodeColors["Spec_ON"] : "(Not set)"
    specOff := CurrentShipContext.NodeColors["Spec_OFF"] ? CurrentShipContext.NodeColors["Spec_OFF"] : "(Not set)"

    ; --- Button + Label 1 ---
    x1 := xpos_start
    y1 := ypos_start
    y1Label := y1 + btnHeight + labelOffset
    Gui, 17:Add, Button, x%x1% y%y1% w180 h%btnHeight% gPickNormalOn, Set Normal Node ON
    Gui, 17:Add, Text, x%x1% y%y1Label% w180 Center vDisp_NormalOn, %normalOn%

    ; --- Button + Label 2 ---
    x2 := xpos_start + colGap
    y2 := ypos_start
    y2Label := y2 + btnHeight + labelOffset
    Gui, 17:Add, Button, x%x2% y%y2% w180 h%btnHeight% gPickNormalOff, Set Normal Node OFF
    Gui, 17:Add, Text, x%x2% y%y2Label% w180 Center vDisp_NormalOff, %normalOff%

    ; --- Button + Label 3 ---
    x3 := xpos_start
    y3 := ypos_start + rowGap
    y3Label := y3 + btnHeight + labelOffset
    Gui, 17:Add, Button, x%x3% y%y3% w180 h%btnHeight% gPickSpecOn, Set SpecMod Node ON
    Gui, 17:Add, Text, x%x3% y%y3Label% w180 Center vDisp_SpecOn, %specOn%

    ; --- Button + Label 4 ---
    x4 := xpos_start + colGap
    y4 := ypos_start + rowGap
    y4Label := y4 + btnHeight + labelOffset
    Gui, 17:Add, Button, x%x4% y%y4% w180 h%btnHeight% gPickSpecOff, Set SpecMod Node OFF
    Gui, 17:Add, Text, x%x4% y%y4Label% w180 Center vDisp_SpecOff, %specOff%

    ; --- Back Button ---
    Gui, 17:Add, Button, x230 y300 w180 h40 gShowMainMenu, Back

    Gui, 17:Show, x100 y100 w620 h400, Node Color Setup
}





PickColorAndSave(which) 
{
    global Edit_Loadout_Ship_selected
    global CurrentShipContext

    ; Step 1: Block mouse clicks temporarily
    InstallMouseBlocker()

    ; Step 2: Hide GUI
    Gui, 17:Hide
    Sleep, 300

    ; Step 3: Show tooltip
    ToolTip, Click anywhere to pick color...

    ; Step 4: Wait for mouse click
    KeyWait, LButton, D
    MouseGetPos, posX, posY

    ToolTip

    ; Step 5: Read color
    PixelGetColor, pickedColor, %posX%, %posY%, RGB
    pickedColor := Format("0x{:06X}", pickedColor & 0xFFFFFF)  ; Format properly

    ; Step 6: Save color to INI file and memory
    file := A_ScriptDir . "\Settings\Coordinates.ini"
    IniWrite, %pickedColor%, %file%, Setup_Colors, %which%
    CurrentShipContext.NodeColors[which] := pickedColor

    Sleep, 300

    ; Step 7: Remove mouse click blocker after picking color
    RemoveMouseBlocker()

    ; Step 8: Reopen Color Setup Menu
    BuildColorSetupGUI()
}





InstallMouseBlocker()
{
    ; Block physical mouse clicks by installing a small hook
    Hotkey, *LButton, DummyBlockClick, On
}




RemoveMouseBlocker()
{
    ; Remove the block
    Hotkey, *LButton, DummyBlockClick, Off
}



Scan_build:
{
    global CurrentShipContext

    if (!IsObject(CurrentShipContext) || CurrentShipContext.Nodes.Count() = 0)
    {
        MsgBox, 48, Error, No Ellydium tree is loaded.
        return
    }

    ; Minimize GUI
    Gui, 17:Minimize
    Sleep, 300
	WinActivate, ahk_class game_main_window
	Sleep, 50

    ; Load color references
    normalOn  := CurrentShipContext.NodeColors["Normal_ON"]
    normalOff := CurrentShipContext.NodeColors["Normal_OFF"]
    specOn    := CurrentShipContext.NodeColors["Spec_ON"]
    specOff   := CurrentShipContext.NodeColors["Spec_OFF"]

    ; Track nodes with unknown colors
    unknownNodes := []

    ; Scan each node
    for nodeName, nodeData in CurrentShipContext.Nodes
    {
        x := nodeData.x
        y := nodeData.y
        isSpec := IsSpecMod(nodeName)

        ; Determine correct color set
        colorOn  := isSpec ? specOn  : normalOn
        colorOff := isSpec ? specOff : normalOff

        ; Try to match ON color
        PixelSearch, outX1, outY1, x, y, x, y, %colorOn%, 60, Fast RGB
        if (ErrorLevel = 0)
        {
            CurrentShipContext.NodeStates[nodeName] := 1
            GuiControl, 17:, Node_%nodeName%, 1
            continue
        }

        ; Try to match OFF color
        PixelSearch, outX2, outY2, x, y, x, y, %colorOff%, 40, Fast RGB
        if (ErrorLevel = 0)
        {
            CurrentShipContext.NodeStates[nodeName] := 0
            GuiControl, 17:, Node_%nodeName%, 0
            continue
        }

        ; Neither matched → unknown
        unknownNodes.Push(nodeName)
    }

    ; Restore GUI
    Gui, 17:Show
    UpdatePointsAndColors()

    ; Show unknown nodes if any
    if (unknownNodes.Length())
    {
        msg := "The following nodes did not match any known color:`n`n"
        for i, name in unknownNodes
            msg .= name . "`n"
        MsgBox, 48, Color Scan Warning, %msg%
    }
    else
    {

    }
}
return





DummyBlockClick:
return



CheckNodeStatesFromSetupGUI:
CheckNodeStatesFromSetupGUI()
return



Save_Build:
{
    global CurrentShipContext, Edit_Loadout_Ship_selected, Edit_Loadout_Loadout_selected

    if (Edit_Loadout_Loadout_selected = "")
    {
        MsgBox, 48, Error, No build selected!
        return
    }

    buildFile := A_ScriptDir . "\Builds\" . Edit_Loadout_Ship_selected . ".ini"
    sectionName := Edit_Loadout_Loadout_selected "|"

    ; Write node states to .ini
	for controlName, active in CurrentShipContext.NodeStates
	{
		if (SubStr(controlName, 1, 5) = "Node_")
			realNodeName := SubStr(controlName, 6)
		else
			realNodeName := controlName

		IniWrite, %active%, %buildFile%, %sectionName%, %realNodeName%
	}

    MsgBox, 64, Saved, Build saved successfully!
}
return



Delete_ellydium_tree:
MsgBox, 36, Confirm Deletion, Are you sure you want to delete all Ellydium nodes from this build?
IfMsgBox, No
    return  ; cancel deletion

buildFile := A_ScriptDir . "\Builds\" . Edit_Loadout_Ship_selected . ".ini"

for _, prefix in ["CPU_", "Capacitor_", "Engine_", "Hull_", "Shield_", "Offence_", "Defence_", "SpecMod_", "Utility_"]
{
    Loop, 15
    {
        key := prefix . A_Index
        IniDelete, %buildFile%, %Edit_Loadout_Loadout_selected%|, %key%
    }
}

MsgBox, 64, Deleted, Ellydium tree entries removed from build.`nReturning to Loadout Editor...
Goto, Edit_Loadout_Gui
return



Setup_Ellydium:
    Gui, 6:Destroy
    LoadEllydiumShipData(Edit_Loadout_Ship_selected)
    BuildSetupGUI()
return



CategorySelect:
    GuiControlGet, BtnName, , %A_GuiControl%
    ShowCategory(BtnName)
return



ShowColorSetupMenu:
    ; When user clicks "Setup Node Colors" button
    Gui, 17:Destroy
    ; Build the color picking GUI
    BuildColorSetupGUI()
return



ShowMainMenu:
    ; Simply rebuild the Setup GUI
	Gui, 17:Destroy
    BuildSetupGUI()
return


PickNormalOn:
    PickColorAndSave("Normal_ON")
return

PickNormalOff:
    PickColorAndSave("Normal_OFF")
return

PickSpecOn:
    PickColorAndSave("Spec_ON")
return

PickSpecOff:
    PickColorAndSave("Spec_OFF")
return



Edit_Ellydium_tree:
    ; Only try if a loadout is selected
    if (Edit_Loadout_Loadout_selected != "None")
    {
		Gui, 13:show
		
        ; Load the full ship data + build
		
		result := LoadEllydiumShipData(Edit_Loadout_Ship_selected, Edit_Loadout_Loadout_selected)
		if (!result)
		{
			Gui, 13:Hide
			Gui, 17:Destroy
			Gui, 6:Destroy
			Goto, Edit_Loadout_Gui
			return
		}

        
		; Open the build editor GUI
        BuildEllydiumTreeGUI()
		
        ; Hide or destroy old GUIs (optional depending on your structure)
        Gui, 13:Hide
    }
    else
    {
        
    }
return



SetCoord17:
    global CurrentShipContext
    ctrlVar := A_GuiControl
    StringTrimLeft, ctrlName, ctrlVar, 4

	InstallMouseBlocker()

    Gui, 17:Hide
    Sleep, 300

    KeyWait, LButton, D
    MouseGetPos, posX, posY

    ; Save into memory
    if (CurrentShipContext.Nodes.HasKey(ctrlName))
    {
        CurrentShipContext.Nodes[ctrlName]["x"] := posX
        CurrentShipContext.Nodes[ctrlName]["y"] := posY
    }

    ; Correct file path
    setupFile := A_ScriptDir . "\Builds\Ellydium\" . CurrentShipContext.ShipName . ".ini"

    ; Write to ini
    IniWrite, %posX%, %setupFile%, %ctrlName%, x
    IniWrite, %posY%, %setupFile%, %ctrlName%, y

    tempCategory := selectedCategory
    Sleep, 300
    ShowCategory(tempCategory)
	RemoveMouseBlocker()
return



CheckboxClicked:
{
    GuiControlGet, state, , %A_GuiControl%
    sectionName := A_GuiControl
    isNowChecked := (state = 1)

    ; Enforce exclusivity BEFORE applying the new state
    if (isNowChecked)
    {
        if (IsSpecMod(sectionName))
            UncheckOtherCategory("SpecMod_", sectionName)
        else if (InStr(sectionName, "Defence_"))
            UncheckOtherCategory("Defence_", sectionName)
        else if (InStr(sectionName, "Offence_"))
            UncheckOtherCategory("Offence_", sectionName)
    }

    ; Now update state
    GuiControl,, %A_GuiControl%, %isNowChecked%
    CurrentShipContext.NodeStates[sectionName] := isNowChecked

    ; Let UpdatePointsAndColors() handle coloring and font
    UpdatePointsAndColors()
}
return



UncheckOtherCategory(prefix, keepThis)
{
    global CurrentShipContext

    for sectionName, _ in CurrentShipContext.NodeStates
    {
        if (sectionName = keepThis)
            continue
        if (InStr(sectionName, prefix))
        {
            GuiControl,, Node_%sectionName%, 0
            CurrentShipContext.NodeStates[sectionName] := 0
        }
    }
}



ExitProgram:
    ; Simply close the current GUI and go back (or destroy, depending what you want)
    Gui, 17:Destroy

    ; You can optionally return to a main menu or do whatever you want here
    goto, Edit_Loadout_Gui

return


ExitEditTree:
    ; Close the Ellydium Tree GUI and go back to the previous menu
    Gui, 17:Destroy  ; Destroy the current GUI (Edit Ellydium Tree)
    goto, Edit_Loadout_Gui
return



ButtonCopyStates:
    CopyNodeStates()
return

ButtonPasteStates:
    PasteNodeStates()
return



^F8::
GuiClose:
Exit:
Gui, 1:Submit, nohide
IniWrite,%Ship1_checked%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Checked1
IniWrite,%Ship2_checked%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Checked2
IniWrite,%Ship3_checked%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Checked3
IniWrite,%Ship4_checked%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Checked4 
IniWrite,%Ship1%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Ship1
IniWrite,%Ship2%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Ship2
IniWrite,%Ship3%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Ship3
IniWrite,%Ship4%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Ship4 
IniWrite,%Builds_Ship1_selected%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Build1
IniWrite,%Builds_Ship2_selected%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Build2
IniWrite,%Builds_Ship3_selected%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Build3
IniWrite,%Builds_Ship4_selected%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Build4
IniWrite,%Unequip_Ships_checked%, %A_ScriptDir%\Settings\Preferences.ini,Last|,Unequip
2GuiClose:
3GuiClose:
4GuiClose:
5GuiClose:
6GuiClose:
8GuiClose:
16GuiClose:
17GuiClose:
Setup_cancel:
ExitApp
return


F8::
Ship_loaded := "Tai'Kin"
Build_Ship_loaded := "High Strafe"
IniRead,ClickX,%A_ScriptDir%\Settings\ShipList.ini,%Ship_loaded%|,x_ellydium
IniRead,ClickY,%A_ScriptDir%\Settings\ShipList.ini,%Ship_loaded%|,y_ellydium
Click, %ClickX% %ClickY%

Click, %ClickX%-200, %ClickY%, 0
LoadEllydiumShipData(Ship_loaded, Build_Ship_loaded)

Sleep, 500
RunEllydiumPixelAutomation()
return
