from distutils.core import setup
import sys
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine tuning.
#build_exe_options = {"packages": ["PyQt5.QtNetwork","PyQt5.QtWebKit","PyQt5.QtPrintSupport"]}
packages = ["PyQt5.QtNetwork","PyQt5.QtWebKit","PyQt5.QtPrintSupport"]
include_files = ['Monitor_Screen_32xSM.png']

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
if sys.platform == "win32":
    base = "Win32GUI"
    
setup(name='Maestro',
      version='1.12',
      description='Maestro Schedule Mapper',
	  options = {"build_exe": { 'packages' : packages, 'include_files': include_files}},
      executables = [Executable("MaestroApp.py", base=base)]
      )
