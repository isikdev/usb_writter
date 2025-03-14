# Описание функционала скрипта

Вообще, в целом, что делает скрипт:

1) Создание контейнера и запись файлов с определённым оффсетом (оффсет регулируется длиной пароля)
2) Проверка ZIP архива после упаковки
3) Шифрование (AES модуль)
4) Проверка контейнера через hashum (насколько я помню, это отдельно от проверки самого ZIP).
5) Дешифрование
6) Упаковка в RAR.
7) Проверка RAR
8) Разделение частей архива на куски рандомного размера в определённом диапазоне, чтобы они выглядели, как обычные файлы, а не архивы
9) Создание PAR2 файлов
10) Примерно все те же функции, только в режиме диска/USB-флешки (заполнение шумом там идёт отдельно, и также используется disk  *penetrate* , чтобы разблокировать защиту файловой системы Windows).
11) Конфиги
12) constants.py - это сообщения логов, которые размещены в одном источнике для удобства

Это основное, возможно что-то упустил, но общее представление должно быть.

Цель скрипта - просто зашифровать и забекапить данные. 8 пункт - разделение частей на куски - это для заливки в облако, т.к. при заливке больших размеров или однотипных файлов могут теоретически возникнуть проблемы, хотя на практике не сталкивался... но т.к. это с целью холодного хранения на несколько лет, то лучше сделать в таком формате.

Т.е. создаётся ZIP контейнер - > шифруется -> дробится на куски.

И проверки целостности на каждом шаге, чтобы ничего не потерять в процессе.

Т.е. процесс в целом достаточно простой, остальное - это нюансы на каждом шаге.

# Руководство по тестированию и конфигурации

Запуск основного скрипта:

c:/coding/newcryptomostlatest/.venv/Scripts/python.exe c:/coding/newcryptomostlatest/crypto/controll.py

## Запуск тестов (PyTest)

### Базовое использование

Тесты необходимо запускать из корневой директории программы (где находится `cont`).

Для запуска тестов со всеми логами и прогресс-барами:

```bash
pytest -o log_cli=true -s
```

### Дополнительные параметры

#### Тестирование дисков

Для работы тестов, связанных с дисками, необходимо указать путь к диску:

```bash
pytest --disk_path E:
```

#### Настройка количества паролей

Чтобы указать количество дополнительных паролей в конфиге:

```bash
pytest --password_count=3
```

## Работа с тестовыми конфигурациями

### Структура конфигов

- Текстовые конфиги автоматически берутся из папки `tests/configs_txt`
- Для каждого конфига в `tests/configs_txt` необходимо создать соответствующий JSON-конфиг в папке `tests/configs_json` (для проверки корректности преобразования)
- Каждый тестовый конфиг должен содержать опции как для шифрования, так и для дешифрования

## Проверка целостности (Integrity Check)

### Настройка проверки

- Для проверки целостности при шифровании укажите параметр `хуш` или `hashsum_limit` в секторе шифрования/дешифрования
- Этот параметр определяет объём проверяемых данных
- Пример: при указании `10m`:
  - При шифровании: проверяется 10 мегабайт с каждой стороны от записанного слоя
  - При дешифровании: проверяется 10 мегабайт от начала контейнера
  - Проверка самого архива выполняется всегда
- Для проверки всего контейнера: укажите `hashsum_limit` больше или равным размеру контейнера

## Дополнительное сжатие (Extra Compress)

### Настройка

- В секторе шифрования укажите параметр `экстра` или `extra`
- Важно: параметр принимает только папки
- Параметр не применяется к отдельным файлам, Отдельные файлы игнорируются
