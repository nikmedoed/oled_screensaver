import locale
from typing import Dict


DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES: tuple[str, ...] = ("en", "ru")


def _normalized(lang: str | None) -> str | None:
    if not lang:
        return None
    code = lang.replace("_", "-").split("-")[0].lower()
    if code in SUPPORTED_LANGUAGES:
        return code
    if code.startswith("ru"):
        return "ru"
    if code.startswith("en"):
        return "en"
    return None


def normalize_language_code(value: str | None) -> str:
    code = _normalized(value)
    return code if code else DEFAULT_LANGUAGE


def detect_system_language(default: str = DEFAULT_LANGUAGE) -> str:
    """Detects system language based on locale info; falls back to default."""
    candidates: list[str | None] = []
    try:
        loc = locale.getdefaultlocale()
        if isinstance(loc, tuple) and loc:
            candidates.append(loc[0])
    except Exception:
        pass

    try:
        current = locale.getlocale()
        if isinstance(current, tuple) and current:
            candidates.append(current[0])
    except Exception:
        pass

    for cand in candidates:
        code = _normalized(cand)
        if code:
            return code
    return default


TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        "common.enabled": "ENABLED",
        "common.disabled": "DISABLED",
        "settings.dialog_title": "Settings",
        "settings.title": "Settings",
        "settings.cancel": "Cancel",
        "settings.save": "Save",
        "settings.timeout_label": "Idle timeout before lock (seconds)",
        "settings.mouse_check_label": "Mouse activity check interval (ms)",
        "settings.cursor_hide_label": "Hide cursor after (ms, 0 = never)",
        "settings.pause_minutes_label": "Pause auto-lock durations (comma separated minutes)",
        "settings.pause_minutes_error_empty": "Enter at least one value.",
        "settings.pause_minutes_error_invalid": "Enter whole numbers separated by commas.",
        "settings.error_fix_minutes": "Fix the minutes list before saving.",
        "settings.error_numeric": "Check numeric values.",
        "settings.visual_section_label": "Visual activity detection zone",
        "settings.visual_detect_toggle": "Detect",
        "settings.visual_show_toggle": "Show",
        "settings.visual_margin.top": "Top margin (%)",
        "settings.visual_margin.bottom": "Bottom margin (%)",
        "settings.visual_margin.left": "Left margin (%)",
        "settings.visual_margin.right": "Right margin (%)",
        "settings.visual_threshold_label": "Visual activity threshold (%)",
        "settings.language_label": "Language",
        "settings.error_zone_value": "Invalid value for zone '{zone}'.",
        "settings.error_zone_sum_vertical": "Top and bottom margins must not exceed 100% total.",
        "settings.error_zone_sum_horizontal": "Left and right margins must not exceed 100% total.",
        "language.name.en": "English",
        "language.name.ru": "Russian",
        "tray.autolock_state": "Auto-lock {state}",
        "tray.delay_until": ">> until {time} ({label})",
        "tray.lock_manually": "Toggle lock manually",
        "tray.disable_autolock": "Disable auto-lock",
        "tray.enable_autolock": "Enable auto-lock",
        "tray.settings": "Settings",
        "tray.exit": "Exit",
        "tray.pause_label": "Pause for {duration}",
    },
    "ru": {
        "common.enabled": "ВКЛЮЧЕНА",
        "common.disabled": "ВЫКЛЮЧЕНА",
        "settings.dialog_title": "Настройки",
        "settings.title": "Настройки",
        "settings.cancel": "Отмена",
        "settings.save": "Сохранить",
        "settings.timeout_label": "Таймаут бездействия до блокировки (сек)",
        "settings.mouse_check_label": "Частота проверки мыши (мс)",
        "settings.cursor_hide_label": "Скрывать курсор через (мс, 0 = не скрывать)",
        "settings.pause_minutes_label": "Минуты для паузы автоблокировки (через запятую)",
        "settings.pause_minutes_error_empty": "Укажите хотя бы одно значение.",
        "settings.pause_minutes_error_invalid": "Введите целые числа через запятую.",
        "settings.error_fix_minutes": "Исправьте список минут перед сохранением.",
        "settings.error_numeric": "Проверьте числовые значения.",
        "settings.visual_section_label": "Зона отслеживания визуальной активности",
        "settings.visual_detect_toggle": "Отслеживать",
        "settings.visual_show_toggle": "Показать",
        "settings.visual_margin.top": "Отступ сверху (%)",
        "settings.visual_margin.bottom": "Отступ снизу (%)",
        "settings.visual_margin.left": "Отступ слева (%)",
        "settings.visual_margin.right": "Отступ справа (%)",
        "settings.visual_threshold_label": "Порог визуальной активности (%)",
        "settings.language_label": "Язык",
        "settings.error_zone_value": "Неверное значение для зоны '{zone}'.",
        "settings.error_zone_sum_vertical": "Сумма верхнего и нижнего отступов не должна превышать 100%.",
        "settings.error_zone_sum_horizontal": "Сумма левого и правого отступов не должна превышать 100%.",
        "language.name.en": "Английский",
        "language.name.ru": "Русский",
        "tray.autolock_state": "Автоблокировка {state}",
        "tray.delay_until": ">> до {time} ({label})",
        "tray.lock_manually": "Переключить блокировку",
        "tray.disable_autolock": "Отключить автоблокировку",
        "tray.enable_autolock": "Включить автоблокировку",
        "tray.settings": "Настройки",
        "tray.exit": "Выход",
        "tray.pause_label": "Пауза на {duration}",
    },
}


class Translator:
    def __init__(self, language: str = DEFAULT_LANGUAGE):
        self.language = normalize_language_code(language)

    def set_language(self, language: str) -> None:
        self.language = normalize_language_code(language)

    def translate(self, key: str, **kwargs) -> str:
        template = (
            TRANSLATIONS.get(self.language, {}).get(key)
            or TRANSLATIONS[DEFAULT_LANGUAGE].get(key)
            or key
        )
        try:
            return template.format(**kwargs)
        except Exception:
            return template


def language_display_names(active_language: str) -> Dict[str, str]:
    translator = Translator(active_language)
    return {
        code: translator.translate(f"language.name.{code}")
        for code in SUPPORTED_LANGUAGES
    }
