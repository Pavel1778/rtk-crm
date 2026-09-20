@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

REM ============================================================
REM  RTK CRM - Universal Launcher (Windows)
REM  Работает из любой директории, сам находит корень проекта
REM ============================================================

REM --- Определяем корень проекта ---
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
cd /d "%ROOT%"

REM --- Docker Compose команда ---
set "DC=docker-compose"
docker compose version >nul 2>&1
if !errorlevel! equ 0 set "DC=docker compose"

REM --- Заголовок ---
:header
cls
echo.
echo ============================================================
echo    RTK CRM - Local Launcher (Windows)
echo ============================================================
echo    Project: %ROOT%
echo ============================================================
echo.

REM --- Проверка Docker ---
where docker >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Docker не найден в PATH
    echo  - Установи Docker Desktop: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

docker info >nul 2>nul
if errorlevel 1 (
    echo [WARN] Docker Desktop не запущен. Пытаюсь запустить...
    if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
        start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        echo Ждём 30 секунд...
        timeout /t 30 /nobreak >nul
    )
    docker info >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] Docker Desktop так и не запустился
        echo  - Запусти его вручную и повтори
        pause
        exit /b 1
    )
)

REM --- Проверка docker-compose.yml ---
if not exist "%ROOT%\docker-compose.yml" (
    echo [ERROR] docker-compose.yml не найден
    pause
    exit /b 1
)

REM --- Автосоздание .env ---
if not exist "%ROOT%\backend\.env" (
    if exist "%ROOT%\backend\.env.example" (
        echo [INFO] Создаю backend\.env из .env.example
        copy /Y "%ROOT%\backend\.env.example" "%ROOT%\backend\.env" >nul
    )
)
if not exist "%ROOT%\frontend\.env" (
    if exist "%ROOT%\frontend\.env.example" (
        echo [INFO] Создаю frontend\.env из .env.example
        copy /Y "%ROOT%\frontend\.env.example" "%ROOT%\frontend\.env" >nul
    )
)

REM --- Меню ---
:menu
echo.
echo ============================================================
echo    Меню:
echo ============================================================
echo    1.  Запустить всё (start)
echo    2.  Остановить (stop)
echo    3.  Статус (status)
echo    4.  Логи (logs)
echo    5.  Перезапустить backend
echo    6.  Перезапустить frontend
echo    7.  Применить миграции
echo    8.  Запустить seed
echo    9.  Показать пользователей
echo    10. Сбросить пароль admin ^-^> admin123
echo    11. Shell внутрь backend
echo    12. Проверить подключение к БД
echo    13. Открыть браузер
echo    14. Полный сброс (down -v)
echo    0.  Выход
echo ============================================================
set /p CHOICE="Твой выбор: "

if "%CHOICE%"=="1"  goto start
if "%CHOICE%"=="2"  goto stop
if "%CHOICE%"=="3"  goto status
if "%CHOICE%"=="4"  goto logs
if "%CHOICE%"=="5"  goto restart_backend
if "%CHOICE%"=="6"  goto restart_frontend
if "%CHOICE%"=="7"  goto migrations
if "%CHOICE%"=="8"  goto seed
if "%CHOICE%"=="9"  goto users
if "%CHOICE%"=="10" goto reset_password
if "%CHOICE%"=="11" goto shell_backend
if "%CHOICE%"=="12" goto check_db
if "%CHOICE%"=="13" goto open_browser
if "%CHOICE%"=="14" goto reset_all
if "%CHOICE%"=="0"  goto end
echo Неверный выбор
goto menu

REM ============================================================
REM  START - запуск всего
REM ============================================================
:start
echo.
echo [INFO] Запускаю RTK CRM...
echo.

REM Проверка placeholder пароля
findstr /C:"НОВЫЙ_ПАРОЛЬ" "%ROOT%\docker-compose.yml" >nul 2>&1
if !errorlevel! equ 0 (
    echo [ERROR] DATABASE_URL содержит placeholder НОВЫЙ_ПАРОЛЬ
    echo  - Открой Supabase Dashboard ^-^> Settings ^-^> Database
    echo  - Скопируй connection string и замени пароль
    echo  - Файл: %ROOT%\docker-compose.yml
    pause
    goto menu
)

REM Останавливаем старые
%DC% down --remove-orphans >nul 2>&1

echo [INFO] Собираю и запускаю контейнеры (может занять 1-3 минуты)...
%DC% up -d --build
if errorlevel 1 (
    echo [ERROR] Не удалось запустить
    echo  - Проверь логи: %DC% logs
    pause
    goto menu
)

echo.
echo [INFO] Жду готовности backend...
set /a WAIT=0
:wait_loop
timeout /t 3 /nobreak >nul
docker logs rtk_backend 2>&1 | findstr /C:"Application startup complete" >nul
if !errorlevel! equ 0 goto backend_ready
set /a WAIT+=1
if !WAIT! geq 30 (
    echo [WARN] Backend не ответил за 90 секунд
    echo  - Смотри логи: %DC% logs backend
    goto menu
)
echo|set /p="."
goto wait_loop

:backend_ready
echo.
echo [OK] Backend готов

echo.
echo [INFO] Проверяю подключение к Supabase...
docker exec rtk_backend python -c "import asyncio; from app.db.session import engine; from sqlalchemy import text; asyncio.run((lambda: __import__('asyncio').get_event_loop().run_until_complete((lambda: __import__('asyncio').sleep(0))()))())" >nul 2>&1
REM Простой healthcheck через /health
curl -sS -m 5 http://localhost:8000/health >nul 2>&1
if !errorlevel! equ 0 (
    echo [OK] Backend отвечает на /health
) else (
    echo [WARN] /health не отвечает — проверь логи
)

echo.
echo [INFO] Проверяю пользователей...
docker exec rtk_backend python -c "import asyncio; from app.db.session import engine; from sqlalchemy import text; print(asyncio.run((lambda: 0)()))" >nul 2>&1
goto show_final

:show_final
echo.
echo [INFO] Список учётных записей:
echo.
docker exec rtk_backend python -c "import asyncio; from app.db.session import engine; from sqlalchemy import text; async def_run = None" 2>nul
docker exec rtk_backend python -c "
import asyncio
from app.db.session import engine
from sqlalchemy import text
async def c():
    async with engine.connect() as conn:
        r = await conn.execute(text('SELECT email, role FROM users ORDER BY id'))
        for row in r: print(f'  {row[0]:<25} [{row[1]}]')
asyncio.run(c())
" 2>nul

echo.
echo ============================================================
echo    RTK CRM ЗАПУЩЕН
echo ============================================================
echo    Frontend:  http://localhost:3000
echo    Backend:   http://localhost:8000/docs
echo    Keycloak:  http://localhost:8080  (admin/admin)
echo    Nginx:     http://localhost
echo ============================================================
echo.
pause
goto menu

REM ============================================================
REM  STOP
REM ============================================================
:stop
echo.
echo [INFO] Останавливаю...
%DC% down
echo [OK]
pause
goto menu

REM ============================================================
REM  STATUS
REM ============================================================
:status
echo.
echo === Контейнеры ===
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | findstr /R "rtk_ NAMES"
echo.
echo === Health backend ===
curl -sS -m 5 http://localhost:8000/health
echo.
echo.
echo === Пользователи ===
docker exec rtk_backend python -c "
import asyncio
from app.db.session import engine
from sqlalchemy import text
async def c():
    async with engine.connect() as conn:
        r = await conn.execute(text('SELECT email, role, is_active FROM users ORDER BY id'))
        for row in r: print(f'  {row[0]:<25} [{row[1]:<8}] active={row[2]}')
asyncio.run(c())
" 2>nul
echo.
pause
goto menu

REM ============================================================
REM  LOGS
REM ============================================================
:logs
echo.
echo Выбери контейнер:
echo   1. backend
echo   2. frontend
echo   3. keycloak
echo   4. nginx
echo   5. все
set /p LC="Выбор [1-5]: "
if "%LC%"=="1" docker logs rtk_backend -f --tail 50
if "%LC%"=="2" docker logs rtk_frontend -f --tail 50
if "%LC%"=="3" docker logs rtk_keycloak -f --tail 50
if "%LC%"=="4" docker logs rtk_nginx -f --tail 50
if "%LC%"=="5" %DC% logs -f --tail 30
goto menu

REM ============================================================
REM  RESTART
REM ============================================================
:restart_backend
echo [INFO] Перезапускаю backend...
%DC% restart backend
echo [OK]
pause
goto menu

:restart_frontend
echo [INFO] Перезапускаю frontend...
%DC% restart frontend
echo [OK]
pause
goto menu

REM ============================================================
REM  MIGRATIONS
REM ============================================================
:migrations
echo.
echo [INFO] Применяю миграции...
docker exec rtk_backend alembic upgrade head
if errorlevel 1 (
    echo [WARN] Alembic не сработал, пробую create_all...
    docker exec rtk_backend python -c "
import asyncio
from app.db.session import engine, Base
import app.models.entities
async def c():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
asyncio.run(c())
"
)
echo [OK]
pause
goto menu

REM ============================================================
REM  SEED
REM ============================================================
:seed
echo.
echo [INFO] Запускаю seed...
docker exec rtk_backend python -m app.seed
echo.
echo [INFO] Пользователи после seed:
docker exec rtk_backend python -c "
import asyncio
from app.db.session import engine
from sqlalchemy import text
async def c():
    async with engine.connect() as conn:
        r = await conn.execute(text('SELECT email, role FROM users ORDER BY id'))
        for row in r: print(f'  {row[0]:<25} [{row[1]}]')
asyncio.run(c())
" 2>nul
pause
goto menu

REM ============================================================
REM  USERS
REM ============================================================
:users
echo.
docker exec rtk_backend python -c "
import asyncio
from app.db.session import engine
from sqlalchemy import text
async def c():
    async with engine.connect() as conn:
        r = await conn.execute(text('SELECT email, role, is_active FROM users ORDER BY id'))
        for row in r: print(f'  {row[0]:<25} [{row[1]:<8}] active={row[2]}')
asyncio.run(c())
" 2>nul
echo.
pause
goto menu

REM ============================================================
REM  RESET PASSWORD
REM ============================================================
:reset_password
echo.
set /p EMAIL="Email [admin@rtk.ru]: "
if "%EMAIL%"=="" set EMAIL=admin@rtk.ru
set /p NEWPASS="Новый пароль [admin123]: "
if "%NEWPASS%"=="" set NEWPASS=admin123

echo [INFO] Сбрасываю пароль для %EMAIL%...

> "%TEMP%\reset_admin.py" echo import asyncio
>>"%TEMP%\reset_admin.py" echo from sqlalchemy import select
>>"%TEMP%\reset_admin.py" echo from app.db.session import SessionLocal
>>"%TEMP%\reset_admin.py" echo from app.models.entities import User
>>"%TEMP%\reset_admin.py" echo try:
>>"%TEMP%\reset_admin.py" echo     from app.auth.security import get_password_hash
>>"%TEMP%\reset_admin.py" echo except ImportError:
>>"%TEMP%\reset_admin.py" echo     try:
>>"%TEMP%\reset_admin.py" echo         from app.core.security import get_password_hash
>>"%TEMP%\reset_admin.py" echo     except ImportError:
>>"%TEMP%\reset_admin.py" echo         from app.services.auth import get_password_hash
>>"%TEMP%\reset_admin.py" echo async def main():
>>"%TEMP%\reset_admin.py" echo     async with SessionLocal() as db:
>>"%TEMP%\reset_admin.py" echo         r = await db.execute(select(User).where(User.email == "%EMAIL%"))
>>"%TEMP%\reset_admin.py" echo         u = r.scalar_one_or_none()
>>"%TEMP%\reset_admin.py" echo         if not u:
>>"%TEMP%\reset_admin.py" echo             print("Пользователь %EMAIL% не найден")
>>"%TEMP%\reset_admin.py" echo             return
>>"%TEMP%\reset_admin.py" echo         u.hashed_password = get_password_hash("%NEWPASS%")
>>"%TEMP%\reset_admin.py" echo         u.is_active = True
>>"%TEMP%\reset_admin.py" echo         await db.commit()
>>"%TEMP%\reset_admin.py" echo         print(f"OK: {u.email} -^> пароль '%NEWPASS%'")
>>"%TEMP%\reset_admin.py" echo asyncio.run(main())

docker cp "%TEMP%\reset_admin.py" rtk_backend:/tmp/reset_admin.py >nul
docker exec rtk_backend python /tmp/reset_admin.py
echo.
pause
goto menu

REM ============================================================
REM  SHELL BACKEND
REM ============================================================
:shell_backend
echo [INFO] Открываю shell внутри backend...
echo  - Выход: exit или Ctrl+D
docker exec -it rtk_backend sh
goto menu

REM ============================================================
REM  CHECK DB
REM ============================================================
:check_db
echo.
echo [INFO] Проверяю подключение к Supabase...
docker exec rtk_backend python -c "
import asyncio
from app.db.session import engine
from sqlalchemy import text
async def c():
    async with engine.connect() as conn:
        r = await conn.execute(text('SELECT current_database(), current_user, version()'))
        db, usr, ver = r.first()
        print(f'  DB:   {db}')
        print(f'  User: {usr}')
        print(f'  Версия: {ver[:60]}')
        r2 = await conn.execute(text(\"SELECT count(*) FROM pg_tables WHERE schemaname='public'\"))
        print(f'  Таблиц: {r2.scalar()}')
        r3 = await conn.execute(text('SELECT count(*) FROM users'))
        print(f'  Пользователей: {r3.scalar()}')
asyncio.run(c())
" 2>&1
echo.
pause
goto menu

REM ============================================================
REM  OPEN BROWSER
REM ============================================================
:open_browser
echo [INFO] Открываю браузер...
start http://localhost:3000
goto menu

REM ============================================================
REM  RESET ALL
REM ============================================================
:reset_all
echo.
echo [WARN] Это удалит все контейнеры и volume-ы.
echo        Данные в Supabase НЕ удаляются.
echo.
set /p CONFIRM="Продолжить? (yes/no): "
if /i "%CONFIRM%"=="yes" (
    %DC% down -v --remove-orphans
    echo [OK] Всё удалено. Запусти снова пункт 1.
) else (
    echo Отмена.
)
pause
goto menu

REM ============================================================
REM  END
REM ============================================================
:end
echo.
echo Пока!
endlocal
exit /b 0