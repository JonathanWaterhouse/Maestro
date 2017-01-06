import sys, os

from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine tuning.
#build_exe_options = {"packages": ["PyQt5.QtNetwork","PyQt5.QtWebKit","PyQt5.QtPrintSupport"]}
#packages = ["PyQt5.QtNetwork","PyQt5.QtWebKit","PyQt5.QtPrintSupport"]
packages = ["sys"]
include_files = []
for f in os.listdir(os.getcwd()):
    if f.endswith('.html') or f.endswith('.css') or f.endswith('.png') or f.endswith('.js'):
        include_files.append(f)

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
#if sys.platform == "win32":
#    base = "Win32GUI"
    
setup(name='Maestro',
      version='2.00',
      description='Maestro Schedule Mapper',
	  options = {"build_exe": { 'packages' : packages, 'include_files': include_files}},
      executables = [Executable("Maestro_routes.py", base=base)]
      )
