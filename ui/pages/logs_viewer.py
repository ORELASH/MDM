#!/usr/bin/env python3
"""
ממשק צפייה ומסנן לוגים מתקדם
Advanced log viewer and filtering interface
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# Import the logging system
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core.logging_system import logger_system, get_logger

# Page config
st.set_page_config(
    page_title="מערכת צפייה בלוגים",
    page_icon="📋",
    layout="wide"
)

def init_session_state():
    """אתחול session state"""
    if 'log_refresh_auto' not in st.session_state:
        st.session_state.log_refresh_auto = False
    if 'selected_log_entry' not in st.session_state:
        st.session_state.selected_log_entry = None

def show_log_statistics():
    """הצגת סטטיסטיקות לוגים"""
    st.subheader("📊 סטטיסטיקות לוגים")
    
    stats = logger_system.get_log_statistics()
    
    if not stats:
        st.warning("❌ לא ניתן לטעון סטטיסטיקות לוגים")
        return
    
    # מטריקות עיקריות
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "סך הכל לוגים",
            f"{stats.get('total_logs', 0):,}",
            help="מספר כולל של רשומות לוג במערכת"
        )
    
    with col2:
        st.metric(
            "לוגים ב-24 שעות",
            f"{stats.get('last_24h', 0):,}",
            help="מספר לוגים שנוצרו ביום האחרון"
        )
    
    with col3:
        st.metric(
            "שגיאות השבוע",
            f"{stats.get('errors_last_week', 0):,}",
            help="מספר שגיאות בשבוע האחרון"
        )
    
    with col4:
        error_rate = 0
        if stats.get('total_logs', 0) > 0:
            error_count = stats.get('by_level', {}).get('ERROR', 0) + stats.get('by_level', {}).get('CRITICAL', 0)
            error_rate = (error_count / stats['total_logs']) * 100
        
        st.metric(
            "אחוז שגיאות",
            f"{error_rate:.2f}%",
            help="אחוז השגיאות מכלל הלוגים"
        )
    
    # גרפים
    col1, col2 = st.columns(2)
    
    with col1:
        # התפלגות לפי רמות
        if stats.get('by_level'):
            df_levels = pd.DataFrame(list(stats['by_level'].items()), columns=['Level', 'Count'])
            
            fig = px.pie(
                df_levels,
                values='Count',
                names='Level',
                title="התפלגות לוגים לפי רמות",
                color_discrete_map={
                    'DEBUG': '#6c757d',
                    'INFO': '#17a2b8',
                    'WARNING': '#ffc107',
                    'ERROR': '#dc3545',
                    'CRITICAL': '#6f42c1'
                }
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # התפלגות לפי logger
        if stats.get('by_logger'):
            df_loggers = pd.DataFrame(list(stats['by_logger'].items()), columns=['Logger', 'Count'])
            
            fig = px.bar(
                df_loggers,
                x='Count',
                y='Logger',
                orientation='h',
                title="התפלגות לוגים לפי מודולים",
                color='Count',
                color_continuous_scale='viridis'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

def show_log_filters():
    """הצגת מסנני לוגים"""
    st.subheader("🔍 מסנני לוגים")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # טווח תאריכים
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        
        date_range = st.date_input(
            "טווח תאריכים",
            value=(start_date.date(), end_date.date()),
            help="בחר טווח תאריכים לסינון"
        )
        
        # טווח שעות
        time_range = st.slider(
            "טווח שעות",
            min_value=0,
            max_value=23,
            value=(0, 23),
            help="בחר טווח שעות ביום"
        )
    
    with col2:
        # רמת לוג
        log_levels = ['כל הרמות', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        selected_level = st.selectbox(
            "רמת לוג",
            log_levels,
            help="בחר רמת לוג לסינון"
        )
        
        # Logger
        logger_options = ['כל המודולים', 'operations', 'queries', 'user_actions', 'system']
        selected_logger = st.selectbox(
            "מודול",
            logger_options,
            help="בחר מודול לסינון"
        )
    
    with col3:
        # חיפוש חופשי
        search_text = st.text_input(
            "חיפוש בהודעות",
            placeholder="הקלד טקסט לחיפוש...",
            help="חיפוש חופשי בתוכן ההודעות"
        )
        
        # מספר תוצאות
        limit = st.number_input(
            "מספר תוצאות",
            min_value=10,
            max_value=10000,
            value=1000,
            step=50,
            help="מספר מקסימלי של תוצאות להציג"
        )
    
    # כפתורי פעולה
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        search_button = st.button("🔍 חפש לוגים", type="primary")
    
    with col2:
        if st.button("🔄 רענן"):
            st.rerun()
    
    with col3:
        auto_refresh = st.checkbox("רענון אוטומטי", value=st.session_state.log_refresh_auto)
        st.session_state.log_refresh_auto = auto_refresh
    
    with col4:
        if st.button("🧹 נקה מסננים"):
            st.session_state.clear()
            st.rerun()
    
    return {
        'date_range': date_range,
        'time_range': time_range,
        'level': selected_level if selected_level != 'כל הרמות' else None,
        'logger': selected_logger if selected_logger != 'כל המודולים' else None,
        'search_text': search_text,
        'limit': limit,
        'search_clicked': search_button
    }

def format_log_entry(log_entry: Dict) -> str:
    """פורמט רשומת לוג להצגה"""
    timestamp = log_entry.get('timestamp', '')
    level = log_entry.get('level', '')
    logger_name = log_entry.get('logger', '')
    message = log_entry.get('message', '')
    
    # צבעים לפי רמה
    color_map = {
        'DEBUG': '#6c757d',
        'INFO': '#17a2b8',
        'WARNING': '#ffc107',
        'ERROR': '#dc3545',
        'CRITICAL': '#6f42c1'
    }
    
    color = color_map.get(level, '#000000')
    
    return f"""
    <div style="border-left: 4px solid {color}; padding: 10px; margin: 5px 0; background-color: #f8f9fa;">
        <strong style="color: {color};">[{level}]</strong> 
        <span style="color: #6c757d;">{timestamp}</span> - 
        <strong>{logger_name}</strong>
        <br>
        <span style="margin-top: 5px; display: block;">{message}</span>
    </div>
    """

def show_log_details(log_entry: Dict):
    """הצגת פרטי רשומת לוג מפורטת"""
    st.subheader("🔍 פרטי לוג מפורטים")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**מידע כללי:**")
        st.write(f"• **זמן:** {log_entry.get('timestamp', 'N/A')}")
        st.write(f"• **רמה:** {log_entry.get('level', 'N/A')}")
        st.write(f"• **מודול:** {log_entry.get('logger', 'N/A')}")
        st.write(f"• **פונקציה:** {log_entry.get('function', 'N/A')}")
        st.write(f"• **שורה:** {log_entry.get('line', 'N/A')}")
        st.write(f"• **Process ID:** {log_entry.get('process', 'N/A')}")
        st.write(f"• **Thread ID:** {log_entry.get('thread', 'N/A')}")
    
    with col2:
        st.write("**Context:**")
        if log_entry.get('user_id'):
            st.write(f"• **משתמש:** {log_entry['user_id']}")
        if log_entry.get('session_id'):
            st.write(f"• **Session:** {log_entry['session_id']}")
        if log_entry.get('cluster_id'):
            st.write(f"• **אשכול:** {log_entry['cluster_id']}")
        if log_entry.get('operation'):
            st.write(f"• **פעולה:** {log_entry['operation']}")
        if log_entry.get('duration_ms'):
            st.write(f"• **משך זמן:** {log_entry['duration_ms']} ms")
    
    # הודעה
    st.write("**הודעה:**")
    st.code(log_entry.get('message', 'N/A'), language='text')
    
    # Exception אם קיים
    if log_entry.get('exception_type'):
        st.write("**שגיאה:**")
        st.error(f"**{log_entry['exception_type']}:** {log_entry.get('exception_message', '')}")
        
        if log_entry.get('traceback'):
            with st.expander("Stack Trace"):
                st.code(log_entry['traceback'], language='python')
    
    # Extra data אם קיים
    if log_entry.get('extra_data'):
        try:
            extra_data = json.loads(log_entry['extra_data'])
            if extra_data:
                st.write("**נתונים נוספים:**")
                st.json(extra_data)
        except:
            pass

def show_log_timeline():
    """הצגת timeline של לוגים"""
    st.subheader("📈 Timeline לוגים")
    
    try:
        # שליפת נתונים ל-timeline
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=24)
        
        df = logger_system.get_logs(
            start_date=start_date,
            end_date=end_date,
            limit=5000
        )
        
        if df.empty:
            st.info("אין נתונים להצגה")
            return
        
        # המרת timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.floor('H')
        
        # קיבוץ לפי שעה ורמה
        timeline_data = df.groupby(['hour', 'level']).size().reset_index(name='count')
        
        # יצירת גרף
        fig = px.line(
            timeline_data,
            x='hour',
            y='count',
            color='level',
            title="נפח לוגים לפי שעה ורמה (24 שעות אחרונות)",
            color_discrete_map={
                'DEBUG': '#6c757d',
                'INFO': '#17a2b8',
                'WARNING': '#ffc107',
                'ERROR': '#dc3545',
                'CRITICAL': '#6f42c1'
            }
        )
        
        fig.update_layout(
            xaxis_title="זמן",
            yaxis_title="מספר לוגים",
            height=400,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"שגיאה בהצגת timeline: {e}")

def search_logs(filters: Dict) -> pd.DataFrame:
    """חיפוש לוגים לפי מסננים"""
    try:
        # הכנת פרמטרים
        start_date = None
        end_date = None
        
        if isinstance(filters['date_range'], tuple) and len(filters['date_range']) == 2:
            start_date = datetime.combine(filters['date_range'][0], datetime.min.time())
            end_date = datetime.combine(filters['date_range'][1], datetime.max.time())
            
            # הוספת מסנן שעות
            if filters['time_range']:
                start_hour, end_hour = filters['time_range']
                # כאן נוכל להוסיף לוגיקה מורכבת יותר לטיפול בשעות
        
        # חיפוש בבסיס הנתונים
        df = logger_system.get_logs(
            start_date=start_date,
            end_date=end_date,
            level=filters['level'],
            logger=filters['logger'],
            limit=filters['limit']
        )
        
        # חיפוש טקסט אם הוגדר
        if filters['search_text'] and not df.empty:
            search_text = filters['search_text'].lower()
            mask = df['message'].str.lower().str.contains(search_text, na=False)
            df = df[mask]
        
        return df
        
    except Exception as e:
        st.error(f"שגיאה בחיפוש לוגים: {e}")
        return pd.DataFrame()

def show_log_table(df: pd.DataFrame):
    """הצגת טבלת לוגים"""
    if df.empty:
        st.info("לא נמצאו לוגים התואמים למסננים")
        return
    
    st.subheader(f"📋 תוצאות חיפוש ({len(df)} לוגים)")
    
    # הגדרת עמודות להצגה
    display_columns = ['timestamp', 'level', 'logger', 'message', 'operation', 'user_id']
    available_columns = [col for col in display_columns if col in df.columns]
    
    # סינון עמודות
    selected_columns = st.multiselect(
        "בחר עמודות להצגה",
        available_columns,
        default=available_columns[:4],
        help="בחר אילו עמודות להציג בטבלה"
    )
    
    if not selected_columns:
        st.warning("בחר לפחות עמודה אחת להצגה")
        return
    
    # הכנת הנתונים להצגה
    display_df = df[selected_columns].copy()
    
    # פורמט טיימסטמפ
    if 'timestamp' in display_df.columns:
        display_df['timestamp'] = pd.to_datetime(display_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # הצגת הטבלה עם אפשרות בחירה
    selected_rows = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row"
    )
    
    # הצגת פרטי הלוג שנבחר
    if selected_rows and len(selected_rows.selection.rows) > 0:
        selected_idx = selected_rows.selection.rows[0]
        selected_log = df.iloc[selected_idx].to_dict()
        
        with st.expander("פרטי הלוג שנבחר", expanded=True):
            show_log_details(selected_log)

def export_logs(df: pd.DataFrame):
    """ייצוא לוגים"""
    if df.empty:
        return
    
    st.subheader("📥 ייצוא לוגים")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # ייצוא CSV
        csv = df.to_csv(index=False)
        st.download_button(
            label="💾 ייצוא CSV",
            data=csv,
            file_name=f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    with col2:
        # ייצוא JSON
        json_data = df.to_json(orient='records', date_format='iso')
        st.download_button(
            label="💾 ייצוא JSON",
            data=json_data,
            file_name=f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    with col3:
        # ייצוא Excel
        try:
            from io import BytesIO
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Logs')
            
            st.download_button(
                label="💾 ייצוא Excel",
                data=buffer.getvalue(),
                file_name=f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except ImportError:
            st.info("ייצוא Excel דורש התקנת openpyxl")

def main():
    """פונקציה ראשית"""
    st.title("📋 מערכת צפייה וניתוח לוגים")
    st.markdown("---")
    
    # אתחול
    init_session_state()
    
    # יצירת tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 סטטיסטיקות",
        "🔍 חיפוש לוגים", 
        "📈 Timeline",
        "⚙️ הגדרות"
    ])
    
    with tab1:
        show_log_statistics()
    
    with tab2:
        # מסננים
        filters = show_log_filters()
        
        # חיפוש אם נלחץ הכפתור או בטעינה ראשונה
        if filters['search_clicked'] or 'logs_df' not in st.session_state:
            with st.spinner("חיפוש לוגים..."):
                st.session_state.logs_df = search_logs(filters)
        
        # הצגת תוצאות
        if 'logs_df' in st.session_state:
            show_log_table(st.session_state.logs_df)
            
            # ייצוא
            if not st.session_state.logs_df.empty:
                export_logs(st.session_state.logs_df)
    
    with tab3:
        show_log_timeline()
    
    with tab4:
        st.subheader("⚙️ הגדרות מערכת הלוגים")
        
        # הצגת קונפיגורציה נוכחית
        st.write("**קונפיגורציה נוכחית:**")
        config_json = json.dumps(logger_system.config, indent=2, ensure_ascii=False)
        st.code(config_json, language='json')
        
        # כלי ניהול
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🧹 נקה לוגים ישנים"):
                with st.spinner("מנקה לוגים ישנים..."):
                    logger_system.cleanup_old_logs()
                st.success("לוגים ישנים נוקו בהצלחה")
        
        with col2:
            if st.button("📊 רענן סטטיסטיקות"):
                st.cache_data.clear()
                st.success("סטטיסטיקות רוענו")
    
    # רענון אוטומטי
    if st.session_state.log_refresh_auto:
        time.sleep(30)
        st.rerun()

if __name__ == "__main__":
    main()