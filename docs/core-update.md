# Обновление ядра

Ядро — подмодуль `core/mihomo`, смотрит в наш форк [Chebobakov/mihomo](https://github.com/Chebobakov/mihomo) и закреплён на теге. Форк нужен потому, что ядро — это апстрим [MetaCubeX/mihomo](https://github.com/MetaCubeX/mihomo) плюс патчи [chenx-dust/mihomo](https://github.com/chenx-dust/mihomo) (ветка `FlClash`), без которых не собирается обвязка `core/*.go`. Автор этих патчей делает force-push: коммит, на который мы смотрели, может пропасть. Наши теги в нашем форке не пропадут.

Стратегия проекта — жёсткий форк: интерфейс заморожен, обновляется только ядро. Значит, это единственная процедура, которую придётся повторять регулярно.

## Как устроена версия

| Где | Что |
|---|---|
| `core/mihomo` (подмодуль) | коммит, на который указывает тег в `Chebobakov/mihomo` |
| `build_config.yaml` → `core_version` | имя этого тега, например `v1.19.32-tenvpn.1` |
| сборка | хук `plugins/setup` добавляет `-X github.com/metacubex/mihomo/constant.Version=<core_version>` в ldflags |
| рантайм | ядро отвечает `{"meta":true,"version":"v1.19.32-tenvpn.1"}`, в «О программе» видна эта же строка |
| CI | шаг «Check core tag» проверяет, что тег `core_version` в форке указывает ровно на коммит подмодуля |

Схема тега: `v<версия апстрима>-tenvpn.<N>`. `N` растёт, если на ту же версию апстрима легли новые патчи.

## Процедура

1. Подтянуть апстрим и патчи автора в форк ядра (в отдельном клоне, не в подмодуле):

   ```bash
   git clone https://github.com/Chebobakov/mihomo.git && cd mihomo
   git remote add patched https://github.com/chenx-dust/mihomo.git
   git remote add upstream https://github.com/MetaCubeX/mihomo.git
   git fetch patched FlClash && git fetch upstream --tags
   git log --oneline patched/FlClash -25          # что поменялось в патчах
   git describe --tags patched/FlClash            # на какой версии апстрима они лежат
   ```

   Варианты: взять `patched/FlClash` целиком (обычный путь) или перенести патчи на свежий тег апстрима самим (`git rebase --onto vX.Y.Z <старая база> tenvpn`), если автор отстал.

2. Поставить тег и запушить ветку и тег:

   ```bash
   git checkout -B tenvpn patched/FlClash
   git tag v1.19.33-tenvpn.1
   git push origin tenvpn v1.19.33-tenvpn.1
   ```

3. В репозитории клиента передвинуть подмодуль и версию:

   ```bash
   git -C core/mihomo fetch origin --tags
   git -C core/mihomo checkout v1.19.33-tenvpn.1
   # build_config.yaml: core_version: v1.19.33-tenvpn.1
   cd core && go mod tidy && cd ..   # если поменялся go.mod ядра
   git add core/mihomo core/go.mod core/go.sum build_config.yaml
   git commit -m "chore(core): bump mihomo to v1.19.33-tenvpn.1"
   ```

4. Проверить локально хотя бы обвязку ядра и одну платформу:

   ```bash
   cd core && CGO_ENABLED=0 go vet . && cd ..
   dart setup.dart windows --targets zip
   ```

   Затем — протокольную матрицу (раздел ниже) против свежей подписки.

5. Тег клиента `vX.Y.Z` → CI соберёт APK, установщик Windows и iOS без подписи.

## Протокольная матрица после обновления

Минимум, без которого версию ядра не выпускаем: Reality, Hysteria2, gRPC, xhttp с xmux (`reuse-settings`), AmneziaWG 2.0 (диапазоны `H1–H4`, `S3/S4`). Быстрее всего — собрать ядро отдельным бинарником из подмодуля и прогнать задержки через `external-controller`:

```bash
cd core/mihomo
go build -tags with_gvisor -ldflags "-X github.com/metacubex/mihomo/constant.Version=$(git describe --tags)" -o /tmp/mihomo .
/tmp/mihomo -t -d <каталог> -f config.yaml     # конфиг принимается целиком, включая amnezia-wg-option
```

Потом — то же в приложении на телефоне (подключение, сайты, внешний IP). Как это делалось в сессии 1 — `docs/session-1-report.md`, раздел «Протокольная матрица».

## Если тег автора исчез

Ничего не делать: наш тег в нашем форке живёт отдельно. Новые патчи автора забираются шагом 1, когда понадобятся.
