# AmneziaWG Decky Plugin

Self-contained плагин для управления AmneziaWG VPN из Game Mode Steam Deck.
Все нужные бинарники (`amneziawg-go`, `awg`, `awg-quick`) бандлятся внутрь плагина —
ничего не ставится в `/usr` или `/etc`, обновления SteamOS плагин не ломают.

## Установка

Два пути — выбирай удобный.

### Вариант A. Удалённо с компьютера (рекомендуемый)

В репо есть скрипт [scripts/install-remote.sh](scripts/install-remote.sh) — качает релиз, кладёт в плагины, перезапускает decky-loader:

```bash
./scripts/install-remote.sh <IP_ДЕКИ>
# или конкретную версию:
./scripts/install-remote.sh deck.local v2.0.0
```

Developer mode в Decky **не нужен** — он включает только UI-кнопку «Install from URL», а скрипт работает в обход неё.

Затем положи конфиг:
```bash
scp ./amnezia_for_awg.conf deck@<IP_ДЕКИ>:~/.config/amneziawg/
```

Имя файла должно матчить `^[A-Za-z0-9._-]+\.conf$`.

Если SSH ещё не настроен — на деке: `passwd` (один раз поставить пароль) и `sudo systemctl enable --now sshd`.

### Вариант B. Через UI Decky

1. Game Mode → `•••` → **Decky** → шестерёнка → **Developer** → **Enable Developer mode**
2. Decky → **Developer** → **Install Plugin from URL** → вставь:
   ```
   https://github.com/GordinRoman/decky-amnezia/releases/latest/download/AmneziaWG.zip
   ```
3. Положи конфиг в `~/.config/amneziawg/` (всё равно нужен SSH/файл-менеджер)

Готово. В Game Mode → `•••` → **AmneziaWG** → переключи тоггл.

## Почему обновления SteamOS не ломают плагин

| Что | Где живёт | Переживёт обновление? |
|---|---|---|
| Сам плагин (UI + Python + бинарники) | `/home/deck/homebrew/plugins/AmneziaWG/` | ✅ `/home` не трогается |
| Конфиги VPN | `/home/deck/.config/amneziawg/` | ✅ `/home` не трогается |
| Логи | `/tmp/amneziawg.log` | ❌ Чистится при ребуте, ротация 512KB × 2 |

Никаких системных пакетов через `pacman`, никаких записей в `/etc`, никакого
`steamos-readonly disable` не нужно.

## Как это работает под капотом

WireGuard и AmneziaWG обычно реализуются как **kernel module**. SteamOS такого модуля
не имеет, поэтому модули собирают через DKMS — но DKMS живёт в `/usr/lib/modules/`
и стирается при апдейте.

Этот плагин использует **userspace-реализацию** (`amneziawg-go`), которая создаёт
TUN-устройство и обрабатывает протокол в user space. Никакого kernel module не нужно.
`awg-quick` детектирует отсутствие модуля и автоматически делает fallback:

```bash
ip link add awg0 type amneziawg          # fails — no kernel module
amneziawg-go awg0                         # spawns userspace impl
```

Тред `amneziawg-go` форкается в фон и держит туннель.

Цена — чуть выше CPU и чуть ниже throughput по сравнению с kernel module
(на типичном VPN-трафике 50-100 Mbit/s разница незаметна).

## Использование

1. В Game Mode → `•••` → **AmneziaWG**
2. Если конфигов несколько — выбери в dropdown
3. Переключи тоггл — VPN включится/выключится
4. Статус опрашивается каждые 5 секунд

## Структура

```
~/homebrew/plugins/AmneziaWG/
├── plugin.json
├── main.py                ← Python-бэкенд плагина
├── dist/index.js          ← собранный фронтенд (React)
└── bin/
    ├── amneziawg-go       ← userspace-реализация (Go, статический)
    ├── awg                ← CLI (C, статический)
    └── awg-quick          ← bash-скрипт

~/.config/amneziawg/
└── *.conf                 ← твои конфиги

/tmp/amneziawg.log         ← логи
```

## Отладка

```bash
tail -f /tmp/amneziawg.log
```

Проверить статус туннеля вручную:
```bash
sudo ~/homebrew/plugins/AmneziaWG/bin/awg show
```

## Релиз новой версии

```bash
git tag v1.0.x
git push origin v1.0.x
```

[GitHub Actions](.github/workflows/release.yml):
1. Собирает `amneziawg-go` из исходников upstream в Arch-контейнере (`CGO_ENABLED=0` → статический бинарник без зависимости от libc)
2. Собирает `awg` из `amneziawg-tools` со статической линковкой (`LDFLAGS=-static`)
3. Берёт `awg-quick` как есть (bash-скрипт)
4. Билдит фронт через Rollup
5. Пакует всё в `AmneziaWG.zip` и публикует как GitHub Release

## Ручная сборка артефакта

Можно запустить workflow руками: **Actions → Build & Release → Run workflow**.
Тогда `AmneziaWG.zip` будет доступен как build artifact на странице run-а (без публикации релиза).
