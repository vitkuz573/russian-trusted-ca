# russian-trusted-ca

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Linux-lightgrey)

CLI-утилита для установки и удаления корневых сертификатов Минцифры России (Russian Trusted Root CA / Sub CA) в системное хранилище доверенных центров сертификации.

Полезна для доступа к российским государственным сайтам и банкам (например, `online.sberbank.ru`, `gosuslugi.ru`), которые используют сертификаты, выпущенные российским удостоверяющим центром, не включённым по умолчанию в большинство дистрибутивов Linux.

> **Важно:** системная установка корневого CA влияет на безопасность всей системы. Если вам нужен доступ только к конкретным сайтам, сначала рассмотрите [безопасные альтернативы](#безопасные-альтернативы-системной-установке). [English version](README_EN.md).

## Содержание

- [Возможности](#возможности)
- [Требования](#требования)
- [Установка](#установка)
- [Использование](#использование)
- [Пример](#пример)
- [Проверка подлинности сертификатов](#проверка-подлинности-сертификатов)
- [Риски](#риски)
- [Безопасные альтернативы системной установке](#безопасные-альтернативы-системной-установке)
- [Разработка](#разработка)
- [Автор](#автор)
- [Лицензия](#лицензия)

## Возможности

- автоматическая загрузка сертификатов с официального CDN Госуслуг;
- проверка подлинности загруженных сертификатов по субъекту и SHA-256 fingerprint через `openssl`;
- поддержка дистрибутивов:
  - Arch Linux (`ca-certificates` / `update-ca-trust`);
  - Debian/Ubuntu (`ca-certificates` / `update-ca-certificates`);
  - Fedora и совместимые системы (`update-ca-trust`).
- проверка TLS-соединения с произвольным хостом через системное хранилище или scoped bundle;
- scoped-установка в профиль Firefox / Chromium через NSS без изменения системного хранилища;
- аудит установленных сертификатов по fingerprint;
- список установленных системных CA.

## Требования

- Linux;
- Python 3.9 или новее;
- `curl`;
- `openssl`;
- `sudo` для записи в системные директории сертификатов;
- `certutil` из пакета `nss-tools` для установки в профиль браузера (NSS).

## Установка

```bash
git clone https://github.com/vitkuz573/russian-trusted-ca.git
cd russian-trusted-ca
pip install -e .
```

Для разработки:

```bash
pip install -e ".[dev]"
```

## Использование

### Установить сертификаты в систему

```bash
russian-trusted-ca install
```

Переустановка:

```bash
russian-trusted-ca install --force
```

Установка с резервной копией существующих сертификатов:

```bash
russian-trusted-ca install --backup
```

Резервные копии сохраняются в `~/.local/share/russian-trusted-ca/backups/<timestamp>/`.

### Удалить сертификаты из системы

```bash
russian-trusted-ca uninstall
```

### Проверить статус

```bash
russian-trusted-ca status
```

### Аудит установленных сертификатов

Проверяет, что установленные файлы совпадают с известными fingerprint:

```bash
russian-trusted-ca audit
```

Если fingerprint не совпадают, автоматически переустановить:

```bash
russian-trusted-ca audit --fix
```

### Список установленных системных CA

```bash
russian-trusted-ca list
russian-trusted-ca list --filter "Russian Trusted"
```

### Проверить соединение с хостом

Через системное хранилище:

```bash
russian-trusted-ca check online.sberbank.ru
```

Через scoped bundle:

```bash
russian-trusted-ca check online.sberbank.ru \
  --bundle ~/.local/share/russian-trusted-ca/russian-trusted-ca-bundle.pem
```

### Собрать scoped CA bundle

```bash
russian-trusted-ca bundle
```

По умолчанию bundle сохраняется в:
`~/.local/share/russian-trusted-ca/russian-trusted-ca-bundle.pem`.

Другой путь:

```bash
russian-trusted-ca bundle -o ./russian-trusted-ca-bundle.pem
```

Вывести путь по умолчанию:

```bash
russian-trusted-ca bundle --print-path
```

Использовать bundle с `curl`:

```bash
curl --cacert ~/.local/share/russian-trusted-ca/russian-trusted-ca-bundle.pem \
     https://online.sberbank.ru/
```

### Установить CA только в профиль браузера (NSS)

Это ограничивает доверие профилем браузера, не затрагивая системное хранилище.

```bash
russian-trusted-ca nss-install
```

Конкретный профиль:

```bash
russian-trusted-ca nss-install --profile ~/.pki/nssdb
```

Установить свежий bundle и сразу импортировать в найденные профили:

```bash
russian-trusted-ca bundle --install-nss
```

Удалить из профилей:

```bash
russian-trusted-ca nss-uninstall
```

### Запуск как Python-модуль

```bash
python -m russian_trusted_ca status
```

## Пример

До установки:

```bash
$ russian-trusted-ca check online.sberbank.ru
FAILED - SSL error: CERTIFICATE_VERIFY_FAILED
```

После установки:

```bash
$ russian-trusted-ca check online.sberbank.ru
OK - TLS TLSv1.2 with Sberbank of Russia (*.online.sberbank.ru)
```

## Проверка подлинности сертификатов

Сертификаты загружаются с официального CDN Госуслуг (`gu-st.ru/content/lending/`) и перед установкой проверяются через `openssl`:

- субъект сертификата должен соответствовать `Russian Trusted Root CA` / `Russian Trusted Sub CA`;
- SHA-256 fingerprint должен совпадать с заранее известным значением.

Это защищает от подмены файлов при загрузке, даже если TLS-соединение к CDN не может быть проверено стандартными средствами системы.

## Риски

Установка корневого сертификата — это привилегированная операция, влияющая на безопасность всей системы.

После установки Russian Trusted Root CA в системное хранилище:

- выпускающий центр сертификации сможет выпускать доверенные сертификаты для **любых** доменов;
- потенциально возможны MITM-атаки на HTTPS-соединения в рамках этой цепочки доверия;
- многие международные сервисы и браузеры не признают этот CA доверенным по умолчанию;
- удалить сертификаты можно в любой момент командой `russian-trusted-ca uninstall`.

Подробный разбор рисков, анализ полей сертификатов и локальный PoC MITM — в
[`SECURITY.md`](SECURITY.md).

Устанавливайте только если понимаете последствия и доверяете Минцифры России как удостоверяющему центру.

## Безопасные альтернативы системной установке

Если цель — получить доступ к конкретным сайтам без глобального доверия CA, используйте один из scoped-вариантов.

### 1. Утилита: собрать scoped bundle

```bash
russian-trusted-ca bundle
curl --cacert ~/.local/share/russian-trusted-ca/russian-trusted-ca-bundle.pem \
     https://online.sberbank.ru/
```

Доверие действует только для явно указанного вызова, системное хранилище не изменяется.

### 2. Python: scoped SSL-контекст

```python
import ssl
import urllib.request
from pathlib import Path

bundle = Path.home() / ".local/share/russian-trusted-ca/russian-trusted-ca-bundle.pem"
ctx = ssl.create_default_context(cafile=str(bundle))

req = urllib.request.Request("https://online.sberbank.ru/")
with urllib.request.urlopen(req, context=ctx) as resp:
    print(resp.status)
```

Этот контекст доверяет только переданному bundle; системное хранилище при этом не изменяется.

### 3. Браузер: импортировать CA только в профиль

Можно добавить сертификаты только в конкретный браузер, не в ОС:

- **Chromium / Google Chrome**: `Настройки → Конфиденциальность и безопасность → Безопасность → Управление сертификатами → Центры сертификации → Импорт`.
- **Firefox**: `Настройки → Приватность и защита → Сертификаты → Просмотр сертификатов → Центры сертификации → Импорт`.

При импорте выберите «Доверять при идентификации веб-сайтов» только если уверены в источнике.

Для NSS-совместимых браузеров можно использовать встроенную команду:

```bash
russian-trusted-ca nss-install
```

### 4. Отдельный браузерный профиль

Создайте профиль Chrome/Firefox только для работы с российскими госуслугами и импортируйте CA туда. Остальные профили и приложения останутся незатронуты.

### 5. Контейнер / виртуальная машина

Запустите браузер или скрипт внутри Docker/VM, установите CA внутри изолированного окружения, не трогая хост. Это защищает основную систему даже при компрометации CA.

### Когда использовать системную установку

Системная установка оправдана, если:

- нужен доступ сразу для множества приложений и системных сервисов;
- вы осознаёте риски и доверяете оператору CA;
- изоляция или per-request bundle не подходят.

## Разработка

```bash
pip install -e ".[dev]"
make lint
make test
make typecheck
```

## Автор

Vitaly Kuzyaev <vitkuz573@gmail.com>

## Лицензия

MIT
