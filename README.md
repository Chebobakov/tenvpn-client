# TENVPN — клиент

Приложение сервиса **TENVPN** для Android, Windows и iOS. Подключается по подписке TENVPN: VLESS (Reality, gRPC, WebSocket, xhttp с xmux), Hysteria2, AmneziaWG.

Это жёсткий форк [FlClash-Patched](https://github.com/chenx-dust/FlClash-Patched) (chenx-dust), который, в свою очередь, форк [FlClash](https://github.com/chen08209/FlClash) (chen08209). Ядро — [mihomo](https://github.com/MetaCubeX/mihomo) с патчами chenx-dust, наша копия — [Chebobakov/mihomo](https://github.com/Chebobakov/mihomo). Спасибо авторам всех трёх проектов.

Исходный снимок: FlClash-Patched `v0.9.1` (коммит `aaf0755d`, 04.10.2026), ядро mihomo `v1.19.32` + 20 патчей chenx-dust (`f63b4a0a`).

## Лицензия

[GPL-3.0](LICENSE), как у всех трёх апстримов. Исходники приложения и ядра открыты; каждый релиз собирается в GitHub Actions из этого репозитория.

## Документы

| Файл | О чём |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | слои приложения, карта ключевых файлов |
| [docs/core-update.md](docs/core-update.md) | как обновить ядро mihomo |
| [docs/session-0-report.md](docs/session-0-report.md) | выбор базы, проверка подписки |
| [docs/session-1-report.md](docs/session-1-report.md) | форк, ребрендинг, CI, протокольная матрица |
| [CHANGELOG.md](CHANGELOG.md) | изменения по версиям |

Файлы `AGENTS.md`, `CLAUDE.md`, `.agents/` — документация апстрима для агентов, по-прежнему верна в части устройства кода.

## Сборка

Нужны Flutter 3.47.x (CI — 3.47.6), Go 1.26+, Rust (rustup подтянет версию из `plugins/rust_api/rust/rust-toolchain.toml`), JDK 17, Android SDK с платформой `android-37.2` и NDK `30.0.16248370` (версии — в `android/gradle/libs.versions.toml`).

```bash
git clone --recursive https://github.com/Chebobakov/tenvpn-client.git
cd tenvpn-client
dart setup.dart android --env stable          # APK в dist/
dart setup.dart windows --env stable          # установщик .exe и portable .zip в dist/
dart setup.dart ios --no-codesign             # только на macOS
```

`setup.dart` сам скачивает гео-базы (`assets/data/*`, ~100 МБ) — раньше это был отдельный шаг `dart run tool/geodata.dart`. **Если собирать в обход `setup.dart`** (`flutter build`, `flutter run`), гео-базы нужно положить самому — иначе ядро не стартует: `Unable to load asset: assets/data/GeoIP.metadb`, в интерфейсе «not initialized». Самый короткий способ — один раз прогнать `dart setup.dart <платформа>`.

Подпись Android: без ключа релизная сборка подписывается debug-ключом и получает суффикс `.dev`. С ключом — задать переменные окружения (или те же ключи в `android/local.properties`):

```bash
export ANDROID_KEYSTORE_FILE=/path/to/tenvpn-release.jks
export ANDROID_KEYSTORE_PASSWORD=...  ANDROID_KEY_ALIAS=tenvpn  ANDROID_KEY_PASSWORD=...
```

### Ловушки Windows-хоста

Android в CI собирается на Linux, как у апстримов. Собирать APK на Windows можно, но только после правок ниже. Каждая стоила отдельной итерации сборки.

1. **libclang для Rust-хелпера.** Хук `plugins/rust_api` ищет `libclang.dll` в `lib/` NDK. В NDK 28 его нет вовсе, в NDK 30 он лежит в `bin/`.
2. **Встроенные заголовки clang.** libclang на Windows ищет их относительно вызывающего процесса, bindgen падает на `fatal error: 'stdbool.h' file not found`. `BINDGEN_EXTRA_CLANG_ARGS` не помогает (его перебивает таргетная переменная сборщика). Помогает копия `lib/clang/<N>/include` в `sysroot/usr/include`.
3. **Обёртки clang без расширения.** Go-сборщик зовёт `aarch64-linux-android24-clang` и т. п., а на Windows это bash-скрипты: «%1 не является приложением Win32». Лечится жёсткими ссылками на `clang.exe` — clang берёт таргет из имени файла.

   Все три правки делает один скрипт (идемпотентный, оригиналы обёрток остаются как `*.sh.bak`):

   ```bash
   bash tool/fix_windows_ndk.sh "$ANDROID_HOME/ndk/30.0.16248370"
   ```

4. **`sdkmanager` из cmdline-tools 23 сломан**: Gradle не может доставить NDK/платформу (`NTSTATUS 0xC0000409`, «Package ndk not found»). Ставить новым CLI: `"$ANDROID_HOME/cmdline-tools/latest/bin/android.exe" sdk install ndk/30.0.16248370 platforms/android-37.2`.
5. **Каталог `Pub\Cache\bin` должен быть в PATH** — иначе `setup.dart` не найдёт упаковщик `flutter_distributor`, который сам же только что поставил: `export PATH="$PATH:$LOCALAPPDATA/Pub/Cache/bin"`.
6. **Длинные пути git.** Упаковщик ставится в pub-кеш через git; без `core.longpaths` часть файлов не выписывается и сборка падает с `Method not found: 'AppPackagePublisherFirebaseHosting'`. Лечится `git config --global core.longpaths true` (или в конкретном чекауте pub-кеша + `git checkout -- .`).
7. **Установщик `.exe`** собирает Inno Setup 6 — на раннерах GitHub он есть, локально его надо поставить; без него собирайте только `--targets zip`.
8. **Не запускать две сборки одновременно** и не трогать дерево (включая `git fetch` в подмодуле ядра) во время сборки: хук пересчитывает отпечатки входов и падает с «File modified during build».

## CI

`.github/workflows/build.yaml`:

- каждый пуш — проверки: анализ Dart, `go vet` обвязки ядра, тег ядра совпадает с подмодулем;
- тег `v*` (или ручной запуск) — сборки: Android (ubuntu), Windows x64 (windows-2022, Inno Setup), iOS без подписи (macos); по тегу файлы прикладываются к GitHub Release.

Секреты репозитория для подписи APK: `ANDROID_KEYSTORE_B64` (keystore в base64), `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`. Без них релиз не собирается — debug-подписанный APK наружу не уходит.

## Глубокие ссылки

`tenvpn://install-config?url=<ссылка на подписку>` — добавить подписку. Для совместимости принимаются и `clash://`, `clashmeta://`, `mihomo://` с тем же форматом.
