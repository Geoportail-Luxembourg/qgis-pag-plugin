@echo off
call "C:\Program Files\QGIS 3.6\bin\o4w_env.bat"
call "C:\Program Files\QGIS 3.6\bin\qt5_env.bat"
call "C:\Program Files\QGIS 3.6\bin\py3_env.bat"

@echo on
"C:\Program Files\QGIS 3.6\apps\Python37\Scripts\pyrcc5.bat" -o resources.py resources.qrc