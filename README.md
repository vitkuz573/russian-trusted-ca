# russian-trusted-ca

CLI-утилита для установки и удаления корневых сертификатов Минцифры России (Russian Trusted Root CA / Sub CA) в системное хранилище доверенных центров сертификации.

Полезна для доступа к российским государственным сайтам и банкам (например, `online.sberbank.ru`, `gosuslugi.ru`), которые используют сертификаты, выпущенные российским удостоверяющим центром, не включённым по умолчанию в большинство дистрибутивов Linux.

> **Важно:** системная установка корневого CA влияет на безопасность всей системы. Если вам нужен доступ только к конкретным сайтам, рассмотрите [безопасные альтернативы](#безопасные-альтернативы-системной-установке) вместо этой утилиты.

## Возможности

- автоматическая загрузка сертификатов с официального CDN Госуслуг;
- проверка подлинности загруженных сертификатов по субъекту и SHA-256 fingerprint через `openssl`;
- поддержка дистрибутивов:
  - Arch Linux (`ca-certificates` / `update-ca-trust`);
  - Debian/Ubuntu (`ca-certificates` / `update-ca-certificates`);
  - Fedora и совместимые системы (`update-ca-trust`).
- проверка TLS-соединения с произвольным хостом через системное хранилище сертификатов.

## Требования

- Linux;
- Python 3.9 или новее;
- `curl`;
- `openssl`;
- `sudo` для записи в системные директории сертификатов.

## Установка

```bash
git clone https://github.com/vitkuz573/russian-trusted-ca.git
cd russian-trusted-ca
pip install -e .
```

## Использование

### Установить сертификаты

```bash
russian-trusted-ca install
```

Для переустановки используйте `--force`:

```bash
russian-trusted-ca install --force
```

### Удалить сертификаты

```bash
russian-trusted-ca uninstall
```

### Проверить статус

```bash
russian-trusted-ca status
```

### Проверить соединение с хостом

```bash
russian-trusted-ca check online.sberbank.ru
russian-trusted-ca check gosuslugi.ru
```

Также можно запускать как Python-модуль:

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

Устанавливайте только если понимаете последствия и доверяете Минцифры России как удостоверяющему центру.

## Безопасные альтернативы системной установке

Если цель — получить доступ к конкретным сайтам без глобального доверия CA, используйте один из scoped-вариантов.

### 1. Утилита: собрать scoped bundle

```bash
russian-trusted-ca bundle
```

По умолчанию bundle сохраняется в:
`~/.local/share/russian-trusted-ca/russian-trusted-ca-bundle.pem`.

Можно указать другой путь:

```bash
russian-trusted-ca bundle -o ./russian-trusted-ca-bundle.pem
```

Полученный bundle можно использовать с `curl`:

```bash
curl --cacert ~/.local/share/russian-trusted-ca/russian-trusted-ca-bundle.pem \
     https://online.sberbank.ru/
```

Плюсы: доверие действует только для явно указанного вызова, системное хранилище не изменяется.

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

### 4. Отдельный браузерный профиль

Создайте профиль Chrome/Firefox только для работы с российскими госуслугами и импортируйте CA туда. Остальные профили и приложения останутся незатронуты.

### 5. Контейнер / виртуальная машина

Запустите браузер или скрипт внутри Docker/VM, установите CA внутри изолированного окружения, не трогая хост. Это защищает основную систему даже при компрометации CA.

### Когда использовать эту утилиту

Системная установка оправдана, если:

- нужен доступ сразу для множества приложений и системных сервисов;
- вы осознаёте риски и доверяете оператору CA;
- изоляция или per-request bundle не подходят.

## Разработка

```bash
pip install -e ".[dev]"
make lint
make test
```

## Автор

Vitaly Kuzyaev <vitkuz573@gmail.com>

## Лицензия

MIT
