# RedshiftManager Utils Package
"""
Utility functions and helpers for RedshiftManager.
"""

__version__ = "1.0.0"

try:
    from .i18n_helper import (
        get_text,
        set_language,
        create_language_selector,
        apply_rtl_css,
        format_number,
        format_date,
        format_time,
        get_translation_manager,
        get_streamlit_helper
    )
    
    # Convenience alias
    _ = get_text
    
except ImportError as e:
    import logging
    logging.warning(f"i18n_helper could not be imported: {e}")
    
    # Fallback function
    def get_text(key, default=None, **kwargs):
        return default or key
    
    _ = get_text

__all__ = [
    'get_text',
    'set_language', 
    'create_language_selector',
    'apply_rtl_css',
    'format_number',
    'format_date',
    'format_time',
    'get_translation_manager',
    'get_streamlit_helper',
    '_'
]