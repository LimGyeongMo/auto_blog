@echo off
setlocal

set "FOLDER=%~1"
if "%FOLDER%"=="" set "FOLDER=.\images"

python main.py generate --folder "%FOLDER%" --mode openai --output blog_post.md

endlocal
