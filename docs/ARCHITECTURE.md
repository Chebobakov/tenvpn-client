# tenvpn-client — архитектура

**Версия 1.0 · 18.09.2026 · сессия 0.** Документ описывает выбранную базу, её слои и карту ключевых файлов. Всё, что здесь написано, проверено сборкой и запуском на этой машине, а не вычитано из README кандидатов. Сравнение кандидатов и протокол проверок — в [session-0-report.md](session-0-report.md).

> С сессии 1 (05.10.2026) лежит в `docs/` репозитория `tenvpn-client`. Карта ниже снята на FlClash-Patched от 18.09; форк сделан со снимка v0.9.1 (04.10) — расхождения отмечены пометкой «v0.9.1». Пакет Kotlin в базе — `cc.chenx.flclash` (не `com.follow.clash`); мы сменили только `applicationId` на `com.tenvpn.app`, пространства имён Kotlin и каналов оставлены, чтобы не трогать JNI.

## 1. Выбранная база

**FlClash-Patched (chenx-dust)** — мягкий форк FlClash (chen08209), Flutter + mihomo, GPL-3.0.

Жёсткий критерий сессии — собирается на Android и Windows и работает с подпиской TENVPN — прошли оба форка FlClash. ClashMi выбыл: в его репозитории нет ядра. Дальше решала разница между двумя форками.

| Критерий | FlClash | FlClash-Patched | ClashMi |
|---|---|---|---|
| Сборка APK + Windows на этой машине | обе собрались | обе собрались | ядра в репозитории нет |
| Слепок ядра mihomo | апстрим ≈16.08.2026 | апстрим ≈10.09.2026 | — |
| iOS | проекта нет | есть `ios/` с `NECore` (Network Extension) | есть, но без ядра |
| Телеметрия | Firebase Crashlytics NDK + Analytics, `google-services.json` автора в репо | нет ни в gradle, ни в Dart | — |
| Гео-базы | лежат в репозитории (44 МБ) | качаются шагом сборки `dart run tool/geodata.dart` | — |
| Активность за 90 дней | 29 коммитов | 116 коммитов | — |

Возможности ядра одинаковые: reality, xhttp с xmux, hysteria2, amnezia-wg-option есть у обоих. Решили три вещи: **нет чужой телеметрии**, **есть проект iOS** (по плану это сессия 7, без него пришлось бы переносить NECore руками) и **ядро свежее на месяц**.

**Риски, которые принимаем осознанно:**

- автор Patched предупреждает: релизы частые, с force-push, совместимость с оригиналом не гарантируется. Для жёсткого форка это почти безвредно — слепок снимается один раз, дальше подмодуль ядра поднимаем сами. Патчи Patched наложены поверх FlClash, откат на оригинал остаётся возможным;
- первая сборка APK упала на хуке `rust_api` (`type 'Null' is not a subtype of type 'String'` при разборе `Cargo.toml`), повторный прогон без единой правки прошёл. Причину воспроизвести не удалось — закладывать в сессию 1 время на повторный прогон;
- `flutter build` без `dart run tool/geodata.dart` даёт приложение, которое не инициализирует ядро: `Unable to load asset: assets/data/GeoIP.metadb`. Шаг качает пять гео-файлов и обязателен в CI.

**В сессии 1 сверх обычного ребрендинга:** убрать диалог «Отказ от ответственности» и удалить осиротевший `android/app/google-services.json` (в gradle Firebase уже нет).

**Про «некоммерческое использование».** Оба кандидата показывают при первом запуске диалог «Отказ от ответственности» с текстом про запрет коммерческого использования (строка `disclaimerDesc` в `arb/intl_en.arb`). Это строка интерфейса, а не условие лицензии: файл `LICENSE` — чистый GPL-3.0, а GPL §7 запрещает добавлять к нему ограничения. То есть юридически это не Hiddify, где ограничение было в самой лицензии. Но диалог — часть продукта, и в сессии 1 он убирается вместе с остальным брендингом.

## 2. Слои

```
┌───────────────────────────────────────────────────────────────┐
│ UI (Flutter, lib/views, lib/pages, lib/widgets)               │
│   панель, профили, прокси, соединения, настройки, логи        │
├───────────────────────────────────────────────────────────────┤
│ Состояние (riverpod: lib/providers, lib/models, lib/manager)  │
│   config.json в shared_preferences + drift-база database.sqlite│
├───────────────────────────────────────────────────────────────┤
│ Слой ядра (lib/core/*) — CoreController выбирает реализацию   │
│   ├── Android: CoreLib  — libclash.so в процессе приложения   │
│   │             через MethodChannel + JNI (:core модуль)      │
│   └── Desktop: CoreService — отдельный процесс FlClashCore.exe│
│                 поверх named pipe (Windows) / unix socket     │
├───────────────────────────────────────────────────────────────┤
│ Ядро mihomo (core/, Go)                                       │
│   hub.go — хендлеры, method.go — диспетчер, lib.go — CGO      │
│   экспорты, server.go — IPC для десктопа                      │
└───────────────────────────────────────────────────────────────┘
```

Ключевое следствие для нас: **связь с ядром не через REST**, как было в августовской Python-реализации, а через FFI/JNI на Android и через собственный IPC-протокол на десктопе. `external-controller` ядра по умолчанию выключен и служит только отладке; включается настройкой и слушает исключительно loopback.

## 3. Карта ключевых файлов

### Слой ядра

| Файл | Что делает |
|---|---|
| `lib/core/controller.dart` | выбирает реализацию по платформе |
| `lib/core/interface.dart` | общий интерфейс `CoreHandlerInterface` |
| `lib/core/lib.dart` | Android: вызовы в libclash.so, синхронизация общего состояния |
| `lib/core/service.dart` | десктоп: сборка транспорта, лаунчера, RPC-клиента |
| `lib/core/desktop/transport.dart` | кадры IPC → события |
| `lib/core/desktop/rpc_client.dart` | корреляция запросов, таймауты |
| `lib/core/desktop/lifecycle.dart` | конечный автомат «запущено/остановлено» |
| `lib/core/desktop/launcher.dart` | запуск процесса ядра или привилегированного хелпера |
| `core/hub.go`, `core/method.go`, `core/lib.go`, `core/server.go` | Go-сторона |

### Подписка и конфиг

| Файл | Что делает |
|---|---|
| `lib/views/profiles/add.dart` | добавление профиля: по ссылке, из файла, QR |
| `lib/models/profile.dart` | `update()` качает подписку, читает `content-disposition` (имя) и `subscription-userinfo` (трафик/срок), `saveFile()` сохраняет **как есть** после валидации ядром |
| `lib/common/task.dart` → `_makeRealProfileTask` | патчит только верхнеуровневые ключи (порты, режим, DNS, tun, authentication, external-controller); секция `proxies` не переписывается |
| `lib/views/profiles/overwrite/` | переопределения профиля: `standard`, `custom`, `script` — сюда пойдёт наша группа «Авто» |
| `lib/common/request.dart` | HTTP-клиент, User-Agent настраивается (`globalState.ua`) |

### Интерфейс

| Файл | Что делает |
|---|---|
| `lib/views/dashboard/` | панель с виджетами (скорость, трафик, кнопки) |
| `lib/views/proxies/` | список серверов, тест задержки, сортировки |
| `lib/views/connection/`, `lib/views/logs.dart` | соединения и логи |
| `lib/views/config/` | настройки (сеть, DNS, tun, приложения) |
| `lib/common/link.dart` | приём deep link через `app_links` |
| `android/app/src/main/AndroidManifest.xml` | схемы deep link; у нас `tenvpn://`, `clash://`, `clashmeta://`, `mihomo://` (список для десктопа — `lib/common/protocol.dart`) |

### Сборка

| Файл | Что делает |
|---|---|
| `plugins/setup/` | хук сборки Go-ядра (`CoreBuilder`/`GoBuilder`), артефакты в `libclash/` |
| `plugins/rust_api/` | хук сборки Rust-хелпера (IPC-примитивы), ядро rquickjs требует bindgen |
| `android/gradle/libs.versions.toml` | v0.9.1: NDK 30.0.16248370, compileSdk 37.2 (на 18.09 было NDK 28.2 / SDK 36) |
| `plugins/rust_api/rust/rust-toolchain.toml` | Rust прибит к 1.95.0 + девять таргетов |
| `setup.dart` | полная сборка с упаковкой: `dart setup.dart android|windows|…`; v0.9.1: сам качает гео-базы (`tool/geodata.dart` теперь библиотека) |
| `build_config.yaml` | имена бинарников (`TENVPNCore`, `TENVPNHelperService`) и `core_version` — версия ядра, прошиваемая в ldflags |

## 4. Что мы делаем с этой базой

1. **Ребрендинг (сессия 1):** имя, иконки, схемы deep link, удаление диалога «Отказ от ответственности» и вычистка Firebase — плагин `com.google.firebase.crashlytics`, зависимости `firebase-crashlytics-ndk` и `firebase-analytics` в `android/app/build.gradle.kts`, файл `android/app/google-services.json`. Если базой станет Patched, в gradle этого нет, но осиротевший `google-services.json` там лежит — тоже удалить.
2. **Слой TENVPN (сессия 2):** подписка Remnawave приходит уже в mihomo-формате, поэтому свой генератор конфигов не нужен — нужен слой, который добавляет AWG-профиль из личной админки и группу «Авто» поверх подписки через механизм overwrite.
3. **Упрощение UI (сессия 3):** оставить панель с одной кнопкой и список серверов; вырезать настройки, логи, инструменты, редактор профилей.
4. **Пул нод (сессия 3):** база показывает группы из подписки как есть. Сейчас Remnawave отдаёт одну `select`-группу на восемь прокси; группу `url-test`/`fallback` по пулу добавляем сами через overwrite — менять панель для этого не нужно.

## 5. Объём кода, который придётся трогать

Всего в `lib/` около 52 тыс. строк (без сгенерированного). Из них интерфейс — `lib/views` 14,7 тыс. и `lib/widgets` 12,7 тыс.

| Раздел | Строк | Судьба |
|---|---|---|
| `views/profiles` | 4 400 | сократить до «вставил ссылку» |
| `views/config` | 2 400 | вырезать почти целиком |
| `views/proxies` | 2 100 | оставить, упростить карточки |
| `views/dashboard` | 1 800 | оставить одну кнопку и статус |
| `views/*.dart` (about, tools, hotkey, backup, developer, access…) | 3 700 | вырезать |
| `views/connection` | 270 | вырезать |

Оценка: под нож уходит примерно две трети экранов, слой ядра и состояние не трогаем.
