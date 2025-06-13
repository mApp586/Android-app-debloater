# Android-app-debloater
This is experimental app in which it lists all android app both internal and external apps using adb and able to uninstall system or bloatware apps.
# How to build for Windows
1. Download adb from https://dl.google.com/android/repository/platform-tools-latest-windows.zip
2. Extract it
3. Transfer all adb.exe and other related file to folder name 'adb' nearby main.py and other .py files
4. Then open cmd
5. First Install python and install customtkinter,pyinstaller through pip
6. Then enter in cmd `pyinstaller --onefile --noconsole -i "adb/icon.ico" --add-data "adb;adb" main.py` [add any icon.ico file in adb folder]
7. And your exe file is created and use it

 # Use with python
 1. run `python main.py` [make sure that python and other pip requirement mentioned follow]

# This Software made with AI
