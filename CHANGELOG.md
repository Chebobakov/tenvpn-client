# Изменения

Формат — по версиям, свежее сверху. История апстрима до форка — в репозиториях [FlClash-Patched](https://github.com/chenx-dust/FlClash-Patched/blob/main/CHANGELOG.md) и [FlClash](https://github.com/chen08209/FlClash).

## [0.1.0] — 2026-10-05

Первая сборка TENVPN. Интерфейс и механика — FlClash-Patched v0.9.1 как есть, поменяно только то, что ниже.

- Имя приложения — TENVPN, `applicationId` / bundle id — `com.tenvpn.app`, свои иконки, свой ключ подписи Android.
- Глубокая ссылка `tenvpn://install-config?url=…`; `clash://`, `clashmeta://`, `mihomo://` по-прежнему принимаются, `flclash://` — нет.
- Ядро mihomo `v1.19.32-tenvpn.1` (апстрим v1.19.32 + патчи chenx-dust) из форка `Chebobakov/mihomo`; настоящая версия ядра прошивается при сборке и видна в API и в «О программе».
- Проверка обновлений смотрит в релизы этого репозитория, а не автора.
- Убраны: диалог «Отказ от ответственности» с запретом коммерческого использования (он не был частью лицензии GPL-3.0), резервное копирование в WebDAV (локальные бэкапы остались), ссылки на репозитории автора, `android/app/google-services.json`.
- Процессы на Windows: `TENVPN.exe`, `TENVPNCore.exe`, служба `TENVPNHelperService`; данные — в `%APPDATA%\TENVPN\tenvpn`.
- CI: Android (подписанный APK), Windows (установщик и portable zip), iOS (сборка без подписи) по тегу `v*`.
