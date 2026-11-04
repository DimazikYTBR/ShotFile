import datetime
import os
import re

version = re.search(r'VERSION = "([^"]+)"', open("shotfile.py", encoding="utf-8").read()).group(1)
parts = (version.split(".") + ["0", "0", "0", "0"])[:4]
tup = ", ".join(str(int(p)) if p.isdigit() else "0" for p in parts)
dotted = ".".join(str(int(p)) if p.isdigit() else "0" for p in parts)
run = os.environ.get("GITHUB_RUN_NUMBER")
today = datetime.date.today().strftime("%d.%m.%Y")
build = "%s (%s)" % (run, today) if run else "local %s" % today
repo = os.environ.get("GITHUB_REPOSITORY", "")

with open("build_info.py", "w", encoding="utf-8") as f:
    f.write("BUILD = %r\nREPO = %r\n" % (build, repo))

info = """VSVersionInfo(
  ffi=FixedFileInfo(filevers=(%s), prodvers=(%s), mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'ShotFile'),
      StringStruct('FileDescription', 'ShotFile screenshot saver'),
      StringStruct('FileVersion', '%s'),
      StringStruct('InternalName', 'ShotFile'),
      StringStruct('LegalCopyright', 'dimzoffc, yorvex'),
      StringStruct('OriginalFilename', 'ShotFile.exe'),
      StringStruct('ProductName', 'ShotFile'),
      StringStruct('ProductVersion', '%s')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""" % (tup, tup, dotted, dotted)
with open("version.txt", "w", encoding="utf-8") as f:
    f.write(info)

env_file = os.environ.get("GITHUB_ENV")
if env_file:
    with open(env_file, "a", encoding="utf-8") as f:
        f.write("APP_VERSION=%s\n" % version)
