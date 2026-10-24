"""Translated user-facing strings."""

LANGUAGES = {"en": "English", "ru": "Русский"}

TEXT = {
    "app_title": {"en": "ArchLens", "ru": "ArchLens"},
    "tab_packages": {"en": "Packages", "ru": "Пакеты"},
    "tab_orphans": {"en": "Orphans", "ru": "Сироты"},
    "search": {"en": "Search packages...", "ru": "Поиск пакетов..."},
    "name": {"en": "Name", "ru": "Имя"},
    "version": {"en": "Version", "ru": "Версия"},
    "size": {"en": "Size", "ru": "Размер"},
    "freed": {"en": "Freed estimate", "ru": "Оценка освобождения"},
    "reason": {"en": "Reason", "ru": "Причина"},
    "date": {"en": "Install date", "ru": "Дата установки"},
    "explicit": {"en": "Explicit", "ru": "Явно установлен"},
    "dependency": {"en": "Dependency", "ru": "Зависимость"},
    "description": {"en": "Description", "ru": "Описание"},
    "direct_dependencies": {"en": "Direct dependencies", "ru": "Прямые зависимости"},
    "required_by": {"en": "Required by", "ru": "Требуется пакетами"},
    "why_installed": {"en": "Why installed", "ru": "Почему установлен"},
    "none": {"en": "None", "ru": "Нет"},
    "loading": {"en": "Loading package database...", "ru": "Загрузка базы пакетов..."},
    "load_error": {"en": "Could not load package database: {error}", "ru": "Не удалось загрузить базу пакетов: {error}"},
    "orphans_total": {"en": "{count} orphan packages, {size}", "ru": "Пакетов-сирот: {count}, размер: {size}"},
    "packages_loaded": {"en": "{count} packages", "ru": "Пакетов: {count}"},
    "no_selection": {"en": "Select a package to inspect it.", "ru": "Выберите пакет для просмотра."},
    "language": {"en": "Language", "ru": "Язык"},
}


def text(key: str, language: str = "en", **values: object) -> str:
    value = TEXT[key].get(language, TEXT[key]["en"])
    return value.format(**values)
