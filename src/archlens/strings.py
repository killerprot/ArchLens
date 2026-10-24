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
    "optional": {"en": "Optional dependency", "ru": "Опциональная зависимость"},
    "protected_status": {"en": "Protected", "ru": "Защищён"},
    "blocked_status": {"en": "Blocked", "ru": "Заблокирован"},
    "protected_explain": {"en": "Protected package; removal is disabled.", "ru": "Защищённый пакет; удаление отключено."},
    "blocked_explain": {"en": "Another installed package depends on this package.", "ru": "Другой установленный пакет зависит от этого пакета."},
    "description": {"en": "Description", "ru": "Описание"},
    "direct_dependencies": {"en": "Direct dependencies", "ru": "Прямые зависимости"},
    "required_by": {"en": "Required by", "ru": "Требуется пакетами"},
    "why_installed": {"en": "Why installed", "ru": "Почему установлен"},
    "none": {"en": "None", "ru": "Нет"},
    "loading": {"en": "Loading package database...", "ru": "Загрузка базы пакетов..."},
    "load_error": {"en": "Could not load package database: {error}", "ru": "Не удалось загрузить базу пакетов: {error}"},
    "orphans_total": {"en": "{count} orphan packages ({optional} optional-only), safe candidates: {safe}, estimated size: {size}", "ru": "Пакетов-сирот: {count} (только опциональные: {optional}), безопасных кандидатов: {safe}, оценка: {size}"},
    "packages_loaded": {"en": "{count} packages", "ru": "Пакетов: {count}"},
    "no_selection": {"en": "Select a package to inspect it.", "ru": "Выберите пакет для просмотра."},
    "language": {"en": "Language", "ru": "Язык"},
    "tab_cache": {"en": "Cache", "ru": "Кэш"},
    "remove_selected": {"en": "Preview removal", "ru": "Предпросмотр удаления"},
    "protected": {"en": "This package is protected.", "ru": "Этот пакет защищён."},
    "dry_run": {"en": "Removal preview", "ru": "Предпросмотр удаления"},
    "confirm_remove": {"en": "Run removal with pkexec?", "ru": "Запустить удаление через pkexec?"},
    "dry_run_failed": {"en": "Dry-run failed: {error}", "ru": "Предпросмотр не удался: {error}"},
    "cache_total": {"en": "Cached packages: {count}, total size: {size}", "ru": "Пакетов в кэше: {count}, общий размер: {size}"},
    "clear_cache": {"en": "Keep latest 2 versions", "ru": "Оставить последние 2 версии"},
    "cache_cleanup": {"en": "Cache cleanup", "ru": "Очистка кэша"},
    "confirm_cache_cleanup": {"en": "Remove cached versions except the latest 2?", "ru": "Удалить версии из кэша, кроме двух последних?"},
}


def text(key: str, language: str = "en", **values: object) -> str:
    value = TEXT[key].get(language, TEXT[key]["en"])
    return value.format(**values)
