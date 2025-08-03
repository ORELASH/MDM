"""
RedshiftManager Internationalization Helper
Advanced internationalization support with RTL languages and Streamlit integration.
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional, Union, Callable
from pathlib import Path
from datetime import datetime, date, time
import locale
from dataclasses import dataclass, field
from enum import Enum
import threading
from functools import wraps

try:
    import streamlit as st
    import babel
    from babel import dates, numbers
    from babel.core import Locale
    from babel.support import Format
    import pytz
except ImportError as e:
    logging.warning(f"Optional dependencies missing: {e}")
    st = None
    babel = None

try:
    from ..models.configuration_model import get_configuration_manager
except ImportError:
    get_configuration_manager = None

# Configure logging
logger = logging.getLogger(__name__)


class TextDirection(Enum):
    """Text direction enumeration."""
    LTR = "ltr"  # Left-to-Right
    RTL = "rtl"  # Right-to-Left


class DateFormat(Enum):
    """Date format styles."""
    SHORT = "short"      # 12/31/99
    MEDIUM = "medium"    # Dec 31, 1999
    LONG = "long"        # December 31, 1999
    FULL = "full"        # Friday, December 31, 1999


class NumberFormat(Enum):
    """Number format styles."""
    DECIMAL = "decimal"
    CURRENCY = "currency"
    PERCENT = "percent"
    SCIENTIFIC = "scientific"


@dataclass
class LanguageInfo:
    """Language information and settings."""
    code: str
    name: str
    native_name: str
    direction: TextDirection
    date_format: str = "YYYY-MM-DD"
    time_format: str = "HH:mm"
    decimal_separator: str = "."
    thousands_separator: str = ","
    currency_symbol: str = "$"
    currency_position: str = "before"  # before, after
    pluralization_rules: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.pluralization_rules:
            # Default English pluralization
            self.pluralization_rules = {
                "one": "singular",
                "other": "plural"
            }


class TranslationManager:
    """Translation management system."""
    
    def __init__(self, translations_dir: str = "translations"):
        self.translations_dir = Path(translations_dir)
        self.translations: Dict[str, Dict[str, str]] = {}
        self.current_language = "en"
        self.fallback_language = "en"
        self._lock = threading.RLock()
        
        # Language definitions
        self.languages = {
            "en": LanguageInfo(
                code="en",
                name="English",
                native_name="English",
                direction=TextDirection.LTR
            ),
            "he": LanguageInfo(
                code="he",
                name="Hebrew",
                native_name="עברית",
                direction=TextDirection.RTL,
                date_format="DD/MM/YYYY",
                time_format="HH:mm",
                currency_symbol="₪",
                currency_position="after"
            )
        }
        
        # Load translations
        self._load_all_translations()
    
    def _load_all_translations(self) -> None:
        """Load all available translations."""
        try:
            if not self.translations_dir.exists():
                self.translations_dir.mkdir(parents=True, exist_ok=True)
                self._create_default_translations()
            
            for lang_code in self.languages.keys():
                self._load_language(lang_code)
                
        except Exception as e:
            logger.error(f"Failed to load translations: {e}")
            self._create_fallback_translations()
    
    def _load_language(self, lang_code: str) -> None:
        """Load translations for specific language."""
        try:
            lang_file = self.translations_dir / f"{lang_code}.json"
            
            if lang_file.exists():
                with open(lang_file, 'r', encoding='utf-8') as f:
                    self.translations[lang_code] = json.load(f)
                logger.debug(f"Loaded translations for {lang_code}")
            else:
                logger.warning(f"Translation file not found: {lang_file}")
                self.translations[lang_code] = {}
                
        except Exception as e:
            logger.error(f"Failed to load language {lang_code}: {e}")
            self.translations[lang_code] = {}
    
    def _create_default_translations(self) -> None:
        """Create default translation files."""
        
        # English translations
        en_translations = {
            # Common UI elements
            "app.title": "RedshiftManager",
            "app.welcome": "Welcome to RedshiftManager",
            "app.loading": "Loading...",
            "app.error": "Error",
            "app.success": "Success",
            "app.warning": "Warning",
            "app.info": "Information",
            
            # Navigation
            "nav.dashboard": "Dashboard",
            "nav.clusters": "Clusters",
            "nav.users": "Users",
            "nav.queries": "Queries",
            "nav.settings": "Settings",
            "nav.logout": "Logout",
            
            # Authentication
            "auth.login": "Login",
            "auth.username": "Username",
            "auth.password": "Password",
            "auth.remember_me": "Remember me",
            "auth.forgot_password": "Forgot password?",
            "auth.login_failed": "Login failed. Please check your credentials.",
            "auth.logout_success": "You have been logged out successfully.",
            
            # Cluster management
            "cluster.add": "Add Cluster",
            "cluster.edit": "Edit Cluster",
            "cluster.delete": "Delete Cluster",
            "cluster.test_connection": "Test Connection",
            "cluster.connection_successful": "Connection successful",
            "cluster.connection_failed": "Connection failed",
            "cluster.name": "Cluster Name",
            "cluster.host": "Host",
            "cluster.port": "Port",
            "cluster.database": "Database",
            "cluster.username": "Username",
            "cluster.password": "Password",
            
            # Query management
            "query.execute": "Execute Query",
            "query.history": "Query History",
            "query.results": "Query Results",
            "query.export": "Export Results",
            "query.cancel": "Cancel Query",
            "query.execution_time": "Execution Time",
            "query.rows_affected": "Rows Affected",
            
            # User management
            "user.add": "Add User",
            "user.edit": "Edit User",
            "user.delete": "Delete User",
            "user.roles": "User Roles",
            "user.permissions": "Permissions",
            "user.active": "Active",
            "user.inactive": "Inactive",
            
            # Forms
            "form.save": "Save",
            "form.cancel": "Cancel",
            "form.reset": "Reset",
            "form.required": "Required field",
            "form.invalid_email": "Invalid email address",
            "form.password_mismatch": "Passwords do not match",
            
            # Data types and formats
            "data.string": "Text",
            "data.number": "Number",
            "data.date": "Date",
            "data.boolean": "Yes/No",
            "data.null": "Empty",
            
            # Messages
            "msg.confirm_delete": "Are you sure you want to delete this item?",
            "msg.changes_saved": "Changes saved successfully",
            "msg.operation_failed": "Operation failed",
            "msg.no_data": "No data available",
            "msg.access_denied": "Access denied",
            
            # Settings
            "settings.general": "General Settings",
            "settings.security": "Security Settings",
            "settings.language": "Language",
            "settings.theme": "Theme",
            "settings.timezone": "Timezone"
        }
        
        # Hebrew translations
        he_translations = {
            # Common UI elements
            "app.title": "מנהל רדשיפט",
            "app.welcome": "ברוכים הבאים למנהל רדשיפט",
            "app.loading": "טוען...",
            "app.error": "שגיאה",
            "app.success": "הצלחה",
            "app.warning": "אזהרה",
            "app.info": "מידע",
            
            # Navigation
            "nav.dashboard": "לוח בקרה",
            "nav.clusters": "צברים",
            "nav.users": "משתמשים",
            "nav.queries": "שאילתות",
            "nav.settings": "הגדרות",
            "nav.logout": "יציאה",
            
            # Authentication
            "auth.login": "כניסה",
            "auth.username": "שם משתמש",
            "auth.password": "סיסמה",
            "auth.remember_me": "זכור אותי",
            "auth.forgot_password": "שכחת סיסמה?",
            "auth.login_failed": "כניסה נכשלה. אנא בדוק את פרטי הגישה.",
            "auth.logout_success": "יצאת בהצלחה מהמערכת.",
            
            # Cluster management
            "cluster.add": "הוסף צבר",
            "cluster.edit": "ערוך צבר",
            "cluster.delete": "מחק צבר",
            "cluster.test_connection": "בדוק חיבור",
            "cluster.connection_successful": "חיבור הצליח",
            "cluster.connection_failed": "חיבור נכשל",
            "cluster.name": "שם הצבר",
            "cluster.host": "שרת",
            "cluster.port": "פורט",
            "cluster.database": "מסד נתונים",
            "cluster.username": "שם משתמש",
            "cluster.password": "סיסמה",
            
            # Query management
            "query.execute": "הרץ שאילתה",
            "query.history": "היסטוריית שאילתות",
            "query.results": "תוצאות שאילתה",
            "query.export": "ייצא תוצאות",
            "query.cancel": "בטל שאילתה",
            "query.execution_time": "זמן ביצוע",
            "query.rows_affected": "שורות שהושפעו",
            
            # User management
            "user.add": "הוסף משתמש",
            "user.edit": "ערוך משתמש",
            "user.delete": "מחק משתמש",
            "user.roles": "תפקידי משתמש",
            "user.permissions": "הרשאות",
            "user.active": "פעיל",
            "user.inactive": "לא פעיל",
            
            # Forms
            "form.save": "שמור",
            "form.cancel": "בטל",
            "form.reset": "אפס",
            "form.required": "שדה חובה",
            "form.invalid_email": "כתובת אימייל לא תקינה",
            "form.password_mismatch": "הסיסמאות אינן זהות",
            
            # Data types and formats
            "data.string": "טקסט",
            "data.number": "מספר",
            "data.date": "תאריך",
            "data.boolean": "כן/לא",
            "data.null": "ריק",
            
            # Messages
            "msg.confirm_delete": "האם אתה בטוח שברצונך למחוק פריט זה?",
            "msg.changes_saved": "השינויים נשמרו בהצלחה",
            "msg.operation_failed": "הפעולה נכשלה",
            "msg.no_data": "אין נתונים זמינים",
            "msg.access_denied": "גישה נדחתה",
            
            # Settings
            "settings.general": "הגדרות כלליות",
            "settings.security": "הגדרות אבטחה",
            "settings.language": "שפה",
            "settings.theme": "ערכת נושא",
            "settings.timezone": "אזור זמן"
        }
        
        # Save translation files
        try:
            with open(self.translations_dir / "en.json", 'w', encoding='utf-8') as f:
                json.dump(en_translations, f, indent=2, ensure_ascii=False)
            
            with open(self.translations_dir / "he.json", 'w', encoding='utf-8') as f:
                json.dump(he_translations, f, indent=2, ensure_ascii=False)
            
            logger.info("Default translation files created")
            
        except Exception as e:
            logger.error(f"Failed to create translation files: {e}")
    
    def _create_fallback_translations(self) -> None:
        """Create minimal fallback translations."""
        self.translations = {
            "en": {"app.title": "RedshiftManager", "app.error": "Error"},
            "he": {"app.title": "מנהל רדשיפט", "app.error": "שגיאה"}
        }
    
    def get_text(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """Get translated text with variable substitution."""
        with self._lock:
            # Try current language first
            text = self._get_text_from_language(key, self.current_language)
            
            # Fall back to fallback language
            if text is None and self.current_language != self.fallback_language:
                text = self._get_text_from_language(key, self.fallback_language)
            
            # Use default or key if no translation found
            if text is None:
                text = default or key
            
            # Perform variable substitution
            if kwargs:
                try:
                    text = text.format(**kwargs)
                except (KeyError, ValueError) as e:
                    logger.warning(f"Translation substitution failed for '{key}': {e}")
            
            return text
    
    def _get_text_from_language(self, key: str, lang_code: str) -> Optional[str]:
        """Get text from specific language."""
        lang_translations = self.translations.get(lang_code, {})
        
        # Direct key lookup first
        if key in lang_translations:
            return lang_translations[key]
        
        # Support nested keys with dot notation
        keys = key.split('.')
        current = lang_translations
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        
        return current if isinstance(current, str) else None
    
    def set_language(self, lang_code: str) -> bool:
        """Set current language."""
        if lang_code in self.languages:
            with self._lock:
                self.current_language = lang_code
                logger.info(f"Language changed to: {lang_code}")
                return True
        else:
            logger.warning(f"Language not supported: {lang_code}")
            return False
    
    def get_language(self) -> str:
        """Get current language code."""
        return self.current_language
    
    def get_language_info(self, lang_code: Optional[str] = None) -> LanguageInfo:
        """Get language information."""
        code = lang_code or self.current_language
        return self.languages.get(code, self.languages[self.fallback_language])
    
    def get_available_languages(self) -> Dict[str, LanguageInfo]:
        """Get all available languages."""
        return self.languages.copy()
    
    def is_rtl(self, lang_code: Optional[str] = None) -> bool:
        """Check if language is right-to-left."""
        lang_info = self.get_language_info(lang_code)
        return lang_info.direction == TextDirection.RTL
    
    def add_translation(self, lang_code: str, key: str, value: str) -> None:
        """Add or update a translation."""
        with self._lock:
            if lang_code not in self.translations:
                self.translations[lang_code] = {}
            
            # Support nested keys
            keys = key.split('.')
            current = self.translations[lang_code]
            
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            
            current[keys[-1]] = value
    
    def save_translations(self, lang_code: str) -> bool:
        """Save translations to file."""
        try:
            lang_file = self.translations_dir / f"{lang_code}.json"
            with open(lang_file, 'w', encoding='utf-8') as f:
                json.dump(self.translations.get(lang_code, {}), f, 
                         indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Failed to save translations for {lang_code}: {e}")
            return False


class StreamlitHelper:
    """Streamlit-specific internationalization helpers."""
    
    def __init__(self, translation_manager: TranslationManager):
        self.tm = translation_manager
    
    def create_language_selector(self, key: str = "language_selector") -> str:
        """Create language selector widget."""
        if not st:
            return self.tm.get_language()
        
        languages = self.tm.get_available_languages()
        
        # Create options with native names
        options = {code: f"{info.native_name} ({info.name})" 
                  for code, info in languages.items()}
        
        # Get current selection
        current_lang = self.tm.get_language()
        current_index = list(options.keys()).index(current_lang) if current_lang in options else 0
        
        # Create selectbox
        selected_lang = st.selectbox(
            label=self.tm.get_text("settings.language"),
            options=list(options.keys()),
            format_func=lambda x: options[x],
            index=current_index,
            key=key
        )
        
        # Update language if changed
        if selected_lang != current_lang:
            self.tm.set_language(selected_lang)
            st.rerun()
        
        return selected_lang
    
    def apply_rtl_css(self) -> None:
        """Apply RTL CSS styling for right-to-left languages."""
        if not st:
            return
        
        if self.tm.is_rtl():
            rtl_css = """
            <style>
            .main .block-container {
                direction: rtl;
                text-align: right;
            }
            
            .stSelectbox > div > div {
                direction: rtl;
                text-align: right;
            }
            
            .stTextInput > div > div > input {
                direction: rtl;
                text-align: right;
            }
            
            .stTextArea > div > div > textarea {
                direction: rtl;
                text-align: right;
            }
            
            .stMarkdown {
                direction: rtl;
                text-align: right;
            }
            
            .stDataFrame {
                direction: ltr; /* Keep tables LTR for data readability */
            }
            
            .stButton > button {
                direction: rtl;
            }
            
            .sidebar .sidebar-content {
                direction: rtl;
                text-align: right;
            }
            
            /* Fix for Hebrew text rendering */
            * {
                font-family: "Segoe UI", Arial, sans-serif;
            }
            </style>
            """
            st.markdown(rtl_css, unsafe_allow_html=True)
    
    def localized_title(self, key: str, **kwargs) -> None:
        """Create localized title."""
        if st:
            st.title(self.tm.get_text(key, **kwargs))
    
    def localized_header(self, key: str, **kwargs) -> None:
        """Create localized header."""
        if st:
            st.header(self.tm.get_text(key, **kwargs))
    
    def localized_subheader(self, key: str, **kwargs) -> None:
        """Create localized subheader."""
        if st:
            st.subheader(self.tm.get_text(key, **kwargs))
    
    def localized_text(self, key: str, **kwargs) -> None:
        """Display localized text."""
        if st:
            st.text(self.tm.get_text(key, **kwargs))
    
    def localized_markdown(self, key: str, **kwargs) -> None:
        """Display localized markdown."""
        if st:
            st.markdown(self.tm.get_text(key, **kwargs))
    
    def localized_success(self, key: str, **kwargs) -> None:
        """Show localized success message."""
        if st:
            st.success(self.tm.get_text(key, **kwargs))
    
    def localized_error(self, key: str, **kwargs) -> None:
        """Show localized error message."""
        if st:
            st.error(self.tm.get_text(key, **kwargs))
    
    def localized_warning(self, key: str, **kwargs) -> None:
        """Show localized warning message."""
        if st:
            st.warning(self.tm.get_text(key, **kwargs))
    
    def localized_info(self, key: str, **kwargs) -> None:
        """Show localized info message."""
        if st:
            st.info(self.tm.get_text(key, **kwargs))


class Formatter:
    """Locale-aware formatting utilities."""
    
    def __init__(self, translation_manager: TranslationManager):
        self.tm = translation_manager
    
    def format_number(self, number: Union[int, float], 
                     format_type: NumberFormat = NumberFormat.DECIMAL,
                     currency_code: str = "USD") -> str:
        """Format number according to current locale."""
        try:
            if babel:
                lang_info = self.tm.get_language_info()
                locale_obj = Locale(lang_info.code)
                
                if format_type == NumberFormat.CURRENCY:
                    return numbers.format_currency(number, currency_code, locale=locale_obj)
                elif format_type == NumberFormat.PERCENT:
                    return numbers.format_percent(number, locale=locale_obj)
                elif format_type == NumberFormat.SCIENTIFIC:
                    return numbers.format_scientific(number, locale=locale_obj)
                else:
                    return numbers.format_decimal(number, locale=locale_obj)
            else:
                # Fallback formatting
                if format_type == NumberFormat.CURRENCY:
                    lang_info = self.tm.get_language_info()
                    if lang_info.currency_position == "before":
                        return f"{lang_info.currency_symbol}{number:,.2f}"
                    else:
                        return f"{number:,.2f} {lang_info.currency_symbol}"
                elif format_type == NumberFormat.PERCENT:
                    return f"{number:.1%}"
                else:
                    return f"{number:,}"
        except Exception as e:
            logger.warning(f"Number formatting failed: {e}")
            return str(number)
    
    def format_date(self, date_obj: Union[datetime, date], 
                   format_style: DateFormat = DateFormat.MEDIUM) -> str:
        """Format date according to current locale."""
        try:
            if babel and isinstance(date_obj, (datetime, date)):
                lang_info = self.tm.get_language_info()
                locale_obj = Locale(lang_info.code)
                
                return dates.format_date(date_obj, format=format_style.value, locale=locale_obj)
            else:
                # Fallback formatting
                lang_info = self.tm.get_language_info()
                if isinstance(date_obj, datetime):
                    date_obj = date_obj.date()
                
                if lang_info.code == "he":
                    return date_obj.strftime("%d/%m/%Y")
                else:
                    return date_obj.strftime("%Y-%m-%d")
        except Exception as e:
            logger.warning(f"Date formatting failed: {e}")
            return str(date_obj)
    
    def format_time(self, time_obj: Union[datetime, time]) -> str:
        """Format time according to current locale."""
        try:
            if babel and isinstance(time_obj, (datetime, time)):
                lang_info = self.tm.get_language_info()
                locale_obj = Locale(lang_info.code)
                
                if isinstance(time_obj, datetime):
                    return dates.format_time(time_obj, locale=locale_obj)
                else:
                    return dates.format_time(time_obj, locale=locale_obj)
            else:
                # Fallback formatting
                if isinstance(time_obj, datetime):
                    return time_obj.strftime("%H:%M")
                else:
                    return time_obj.strftime("%H:%M")
        except Exception as e:
            logger.warning(f"Time formatting failed: {e}")
            return str(time_obj)
    
    def format_datetime(self, datetime_obj: datetime,
                       date_format: DateFormat = DateFormat.MEDIUM) -> str:
        """Format datetime according to current locale."""
        try:
            if babel:
                lang_info = self.tm.get_language_info()
                locale_obj = Locale(lang_info.code)
                
                return dates.format_datetime(datetime_obj, format=date_format.value, locale=locale_obj)
            else:
                # Fallback formatting
                lang_info = self.tm.get_language_info()
                if lang_info.code == "he":
                    return datetime_obj.strftime("%d/%m/%Y %H:%M")
                else:
                    return datetime_obj.strftime("%Y-%m-%d %H:%M")
        except Exception as e:
            logger.warning(f"DateTime formatting failed: {e}")
            return str(datetime_obj)


# Global instances
_translation_manager: Optional[TranslationManager] = None
_streamlit_helper: Optional[StreamlitHelper] = None
_formatter: Optional[Formatter] = None


def get_translation_manager() -> TranslationManager:
    """Get global translation manager instance."""
    global _translation_manager
    if _translation_manager is None:
        _translation_manager = TranslationManager()
        
        # Set language from configuration if available
        if get_configuration_manager:
            config_lang = get_configuration_manager().get('ui.language', 'en')
            _translation_manager.set_language(config_lang)
    
    return _translation_manager


def get_streamlit_helper() -> StreamlitHelper:
    """Get global Streamlit helper instance."""
    global _streamlit_helper
    if _streamlit_helper is None:
        _streamlit_helper = StreamlitHelper(get_translation_manager())
    return _streamlit_helper


def get_formatter() -> Formatter:
    """Get global formatter instance."""
    global _formatter
    if _formatter is None:
        _formatter = Formatter(get_translation_manager())
    return _formatter


# Convenience functions
def get_text(key: str, default: Optional[str] = None, **kwargs) -> str:
    """Get translated text."""
    return get_translation_manager().get_text(key, default, **kwargs)


def set_language(lang_code: str) -> bool:
    """Set current language."""
    return get_translation_manager().set_language(lang_code)


def create_language_selector(key: str = "language_selector") -> str:
    """Create language selector widget."""
    return get_streamlit_helper().create_language_selector(key)


def apply_rtl_css() -> None:
    """Apply RTL CSS styling."""
    get_streamlit_helper().apply_rtl_css()


def format_number(number: Union[int, float], format_type: NumberFormat = NumberFormat.DECIMAL) -> str:
    """Format number according to current locale."""
    return get_formatter().format_number(number, format_type)


def format_date(date_obj: Union[datetime, date], format_style: DateFormat = DateFormat.MEDIUM) -> str:
    """Format date according to current locale."""
    return get_formatter().format_date(date_obj, format_style)


def format_time(time_obj: Union[datetime, time]) -> str:
    """Format time according to current locale."""
    return get_formatter().format_time(time_obj)


# Convenience alias
_ = get_text


# Decorator for automatic translation
def translate(key_prefix: str = ""):
    """Decorator to automatically translate function docstrings and return values."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # If result is a string and looks like a translation key, translate it
            if isinstance(result, str) and "." in result and not " " in result:
                translated = get_text(result)
                return translated if translated != result else result
            
            return result
        
        return wrapper
    return decorator


if __name__ == "__main__":
    # Example usage
    tm = get_translation_manager()
    
    # Test translations
    print(f"English: {tm.get_text('app.title')}")
    
    tm.set_language("he")
    print(f"Hebrew: {tm.get_text('app.title')}")
    
    # Test formatting
    formatter = get_formatter()
    
    now = datetime.now()
    print(f"Date (EN): {formatter.format_date(now)}")
    
    tm.set_language("he")
    print(f"Date (HE): {formatter.format_date(now)}")
    
    # Test number formatting
    number = 1234.56
    print(f"Number: {formatter.format_number(number)}")
    print(f"Currency: {formatter.format_number(number, NumberFormat.CURRENCY)}")
    print(f"Percent: {formatter.format_number(0.1234, NumberFormat.PERCENT)}")
    
    # Test RTL detection
    print(f"Is RTL: {tm.is_rtl()}")
    
    tm.set_language("en")
    print(f"Is RTL: {tm.is_rtl()}")