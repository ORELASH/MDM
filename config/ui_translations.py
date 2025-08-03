"""
UI Translations for MultiDBManager
Multi-language support with English as default and Hebrew option
"""

# Language configurations
LANGUAGES = {
    "English": {"code": "en", "flag": "🇺🇸", "rtl": False},
    "עברית": {"code": "he", "flag": "🇮🇱", "rtl": True}
}

# Translations dictionary - English to Hebrew
UI_TRANSLATIONS = {
    # Main titles
    "📊 Dashboard": "📊 לוח בקרה",
    "📊 MultiDBManager Dashboard": "📊 לוח בקרה MultiDBManager",
    "🖥️ Server Management": "🖥️ ניהול שרתים", 
    "👥 User Management": "👥 ניהול משתמשים",
    "🌐 Global Users": "🌐 משתמשים גלובליים",
    "🌐 Global Users Management": "🌐 ניהול משתמשים גלובלי",
    "💾 Local User Storage": "💾 אחסון משתמשים מקומי",
    "🔔 Notifications": "🔔 התראות",
    "🔗 LDAP Sync": "🔗 סינכרון LDAP",
    "🎭 Group-Role Mapping": "🎭 מיפוי קבוצות-תפקידים",
    "🔧 Module Manager": "🔧 מנהל מודולים",
    "🚨 Alert System": "🚨 מערכת התראות",
    "💾 Backup System": "💾 מערכת גיבויים",
    "📋 Logs Viewer": "📋 מציג לוגים",
    "⚙️ Settings": "⚙️ הגדרות",
    
    # Navigation and UI
    "### Universal Multi-Database Management Tool": "### כלי ניהול מסדי נתונים אוניברסלי",
    "Navigation": "ניווט",
    "Select Page:": "בחר עמוד:",
    "System Info": "מידע מערכת",
    "Version": "גרסה",
    "Mode": "מצב", 
    "Open Access": "גישה פתוחה",
    
    # Dashboard sections
    "System Overview and Monitoring": "סקירת מערכת וניטור",
    "Database Server Connection Management": "ניהול חיבורי שרתי מסדי נתונים",
    "Database Users and Permissions Management": "ניהול משתמשי מסד נתונים והרשאות",
    
    # Server management
    "📋 Registered Servers": "📋 שרתים רשומים",
    "➕ Add New Server": "➕ הוסף שרת חדש",
    "✏️ Edit Server": "✏️ ערוך שרת",
    "📊 Cluster Monitoring": "📊 ניטור קלאסטר",
    "⚙️ Server Settings": "⚙️ הגדרות שרת",
    
    # Database components
    "📋 Database Tables": "📋 טבלאות מסד נתונים",
    "👥 Database Users": "👥 משתמשי מסד נתונים", 
    "🔑 Database Roles": "🔑 תפקידי מסד נתונים",
    "👤 Database Users": "👤 משתמשי מסד נתונים",
    "👥 Cluster Users, Roles & Groups": "👥 משתמשים, תפקידים וקבוצות",
    
    # Dashboard sections
    "📈 Query Performance": "📈 ביצועי שאילתות",
    "💿 Storage Utilization": "💿 ניצול אחסון",
    "📋 Recent Activity": "📋 פעילות אחרונה",
    "⚡ Quick Actions": "⚡ פעולות מהירות",
    "👥 Users & Roles Summary": "👥 סיכום משתמשים ותפקידים",
    
    # Buttons and actions
    "Add Server": "הוסף שרת",
    "Edit": "ערוך",
    "Delete": "מחק",
    "Test Connection": "בדוק חיבור",
    "Scan Database": "סרוק מסד נתונים",
    "Save": "שמור",
    "Cancel": "בטל",
    "Connect": "התחבר",
    "Disconnect": "התנתק",
    
    # Status messages
    "Connected": "מחובר",
    "Disconnected": "מנותק",
    "Active": "פעיל",
    "Inactive": "לא פעיל",
    "Online": "מקוון",
    "Offline": "לא מקוון",
    "Running": "רץ",
    "Stopped": "עצור",
    
    # Database types
    "PostgreSQL": "PostgreSQL",
    "MySQL": "MySQL", 
    "Redis": "Redis",
    "Redshift": "Redshift",
    
    # Common terms
    "Name": "שם",
    "Host": "מארח",
    "Port": "פורט",
    "Database": "מסד נתונים",
    "Username": "שם משתמש",
    "Password": "סיסמה",
    "Type": "סוג",
    "Status": "סטטוס",
    "Environment": "סביבה",
    "Created": "נוצר",
    "Updated": "עודכן",
    "Last Login": "כניסה אחרונה",
    
    # Error messages
    "Connection failed": "החיבור נכשל",
    "Invalid credentials": "פרטי הזדהות שגויים",
    "Server not found": "השרת לא נמצא",
    "Database error": "שגיאת מסד נתונים",
    "Access denied": "הגישה נדחתה",
    
    # Success messages
    "Connection successful": "החיבור הצליח",
    "Server added successfully": "השרת נוסף בהצלחה", 
    "Server updated successfully": "השרת עודכן בהצלחה",
    "Server deleted successfully": "השרת נמחק בהצלחה",
    "Scan completed": "הסריקה הושלמה",
}

def translate(text: str, language: str = "English") -> str:
    """
    Translate text based on selected language
    Args:
        text: Text to translate
        language: Target language ("English" or "עברית")
    Returns:
        Translated text or original if translation not found
    """
    if language == "עברית":
        return UI_TRANSLATIONS.get(text, text)
    return text  # Return original text for English

def get_available_languages() -> dict:
    """Get all available languages"""
    return LANGUAGES.copy()

def get_all_translations() -> dict:
    """Get all available translations"""
    return UI_TRANSLATIONS.copy()

def is_rtl_language(language: str) -> bool:
    """Check if language requires RTL layout"""
    return LANGUAGES.get(language, {}).get("rtl", False)