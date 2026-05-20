# AmneziaWG Decky Plugin

Плагин для управления AmneziaWG VPN прямо из Game Mode Steam Deck.

## Установка

### 1. Установи AmneziaWG на деку

Decky не умеет ставить системные пакеты, поэтому `awg-quick` и `awg` нужно установить руками. Подключись к деке по SSH:

```bash
ssh deck@<IP_АДРЕС>
```

Затем:
```bash
sudo steamos-readonly disable
sudo pacman-key --init && sudo pacman-key --populate archlinux
sudo pacman -S base-devel git --noconfirm
# yay (AUR helper)
git clone https://aur.archlinux.org/yay.git /tmp/yay
cd /tmp/yay && makepkg -si --noconfirm
# Собственно AmneziaWG
yay -S amneziawg-tools --noconfirm
```

### 2. Положи конфиг

```bash
sudo mkdir -p /etc/amnezia/amneziawg/
sudo cp ~/amnezia_for_awg.conf /etc/amnezia/amneziawg/
```

Имя файла должно соответствовать `^[A-Za-z0-9._-]+\.conf$`.

### 3. Установи плагин через Decky

В Game Mode:

1. Кнопка `•••` → **Decky** → шестерёнка (Settings) → **Developer** → включи **Developer mode**.
2. Вернись в меню Decky → внизу появится **Developer** → **Install Plugin from URL**.
3. Вставь прямую ссылку на `.zip` из [GitHub Releases](https://github.com/GordinRoman/decky-amnezia/releases/latest) (правый клик по `AmneziaWG.zip` → Copy link).
4. Decky скачает архив, распакует в `~/homebrew/plugins/AmneziaWG` и перезагрузит плагины.

## Сборка релиза

Релизы собираются автоматически через GitHub Actions ([release.yml](.github/workflows/release.yml)):

```bash
git tag v1.0.0
git push origin v1.0.0
```

CI запустит `npm run build`, упакует `plugin.json`, `main.py`, `package.json`, `README.md` и `dist/index.js` в `AmneziaWG.zip` и опубликует его как GitHub Release.

Можно так же запустить workflow вручную через **Actions → Build & Release → Run workflow** — тогда zip будет доступен как build artifact (без публикации релиза).

## Использование

1. В Game Mode нажми `•••`
2. Найди плагин **AmneziaWG**
3. Если конфигов несколько — выбери нужный в dropdown
4. Переключи тоггл для подключения/отключения
5. Статус обновляется каждые 5 секунд

## Структура файлов на деке

```
/etc/amnezia/amneziawg/     ← конфиги (.conf)
~/homebrew/plugins/AmneziaWG ← код плагина
/tmp/amneziawg.log          ← логи плагина (ротация 512KB × 2)
```

## Отладка

```bash
tail -f /tmp/amneziawg.log
```
