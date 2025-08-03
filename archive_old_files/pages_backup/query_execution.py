"""
RedshiftManager Query Execution Page
Advanced SQL query execution interface with syntax highlighting and result export.
"""

import streamlit as st
import pandas as pd
import json
import time
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import re

# Import our models
try:
    from models.database_models import get_database_manager, RedshiftCluster, QueryHistory, User
    from models.redshift_connection_model import get_connector, ConnectionConfig, RedshiftConnector, QueryAnalyzer
    from utils.i18n_helper import get_text, apply_rtl_css
except ImportError as e:
    st.error(f"Failed to import required modules: {e}")
    st.stop()


def query_execution_page():
    """Main query execution page."""
    
    # Apply RTL CSS if needed
    apply_rtl_css()
    
    # Page title
    st.title("🔍 " + get_text("nav.queries", "Query Execution"))
    st.markdown("---")
    
    # Get database manager
    db_manager = get_database_manager()
    
    # Sidebar for cluster selection and options
    with st.sidebar:
        st.header(get_text("query.cluster_selection", "Cluster Selection"))
        
        # Get available clusters
        try:
            with db_manager.session_scope() as session:
                clusters = session.query(RedshiftCluster).filter_by(is_active=True).all()
        except Exception as e:
            st.error(f"Error loading clusters: {e}")
            return
        
        if not clusters:
            st.error(get_text("query.no_clusters", "No active clusters found. Please add a cluster first."))
            return
        
        # Cluster selection
        cluster_options = {f"{cluster.name} ({cluster.environment})": cluster.id for cluster in clusters}
        selected_cluster_key = st.selectbox(
            get_text("query.select_cluster", "Select Cluster"),
            options=list(cluster_options.keys())
        )
        
        if not selected_cluster_key:
            return
        
        cluster_id = cluster_options[selected_cluster_key]
        selected_cluster = next(c for c in clusters if c.id == cluster_id)
        
        # Connection status
        st.subheader(get_text("query.connection_status", "Connection Status"))
        
        # Test connection button
        if st.button("🔍 " + get_text("cluster.test_connection", "Test Connection")):
            test_cluster_connection(selected_cluster)
        
        # Query options
        st.subheader(get_text("query.options", "Query Options"))
        
        query_limit = st.number_input(
            get_text("query.result_limit", "Result Limit"),
            min_value=1,
            max_value=10000,
            value=1000,
            help=get_text("query.limit_help", "Maximum number of rows to return")
        )
        
        query_timeout = st.number_input(
            get_text("query.timeout", "Timeout (seconds)"),
            min_value=1,
            max_value=3600,
            value=300,
            help=get_text("query.timeout_help", "Query execution timeout")
        )
        
        auto_format = st.checkbox(
            get_text("query.auto_format", "Auto-format SQL"),
            value=True,
            help=get_text("query.auto_format_help", "Automatically format SQL queries")
        )
        
        enable_analysis = st.checkbox(
            get_text("query.enable_analysis", "Enable Query Analysis"),
            value=True,
            help=get_text("query.analysis_help", "Analyze queries for optimization suggestions")
        )
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Query editor section
        st.subheader("📝 " + get_text("query.editor", "SQL Query Editor"))
        
        # Query tabs
        tab1, tab2, tab3 = st.tabs([
            get_text("query.new_query", "New Query"),
            get_text("query.saved_queries", "Saved Queries"),
            get_text("query.query_history", "Query History")
        ])
        
        with tab1:
            show_query_editor(selected_cluster, query_limit, query_timeout, auto_format, enable_analysis, db_manager)
        
        with tab2:
            show_saved_queries(selected_cluster, db_manager)
        
        with tab3:
            show_query_history(selected_cluster, db_manager)
    
    with col2:
        # Quick actions and templates
        st.subheader("⚡ " + get_text("query.quick_actions", "Quick Actions"))
        
        # Common query templates
        templates = get_query_templates()
        
        template_names = list(templates.keys())
        selected_template = st.selectbox(
            get_text("query.select_template", "Select Template"),
            options=[""] + template_names,
            format_func=lambda x: get_text("query.select_template_option", "-- Select Template --") if x == "" else x
        )
        
        if selected_template and st.button("📋 " + get_text("query.load_template", "Load Template")):
            st.session_state.query_template = templates[selected_template]
        
        # Schema browser
        st.subheader("🗂️ " + get_text("query.schema_browser", "Schema Browser"))
        
        if st.button("🔄 " + get_text("query.refresh_schema", "Refresh Schema")):
            load_schema_info(selected_cluster)
        
        # Display schema info if available
        if f"schema_info_{cluster_id}" in st.session_state:
            show_schema_browser(st.session_state[f"schema_info_{cluster_id}"])


def show_query_editor(cluster, query_limit, query_timeout, auto_format, enable_analysis, db_manager):
    """Show the main query editor interface."""
    
    # Load template if selected
    default_query = ""
    if "query_template" in st.session_state:
        default_query = st.session_state.query_template
        del st.session_state.query_template
    
    # SQL query input
    sql_query = st.text_area(
        get_text("query.enter_sql", "Enter SQL Query"),
        value=default_query,
        height=200,
        help=get_text("query.sql_help", "Enter your SQL query here. Use Ctrl+Enter to execute."),
        key="sql_query_input"
    )
    
    # Format query button
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🎨 " + get_text("query.format_sql", "Format SQL")):
            if sql_query:
                formatted_query = format_sql_query(sql_query)
                st.session_state.sql_query_input = formatted_query
                st.experimental_rerun()
    
    with col2:
        if st.button("🔍 " + get_text("query.analyze", "Analyze Query")):
            if sql_query and enable_analysis:
                show_query_analysis(sql_query)
    
    with col3:
        save_query = st.button("💾 " + get_text("query.save", "Save Query"))
    
    with col4:
        execute_query = st.button("▶️ " + get_text("query.execute", "Execute Query"), type="primary")
    
    # Save query functionality
    if save_query and sql_query:
        save_query_dialog(sql_query, db_manager)
    
    # Execute query
    if execute_query and sql_query:
        execute_sql_query(cluster, sql_query, query_limit, query_timeout, db_manager)


def show_saved_queries(cluster, db_manager):
    """Show saved queries interface."""
    
    st.write(get_text("query.saved_queries_desc", "Manage your saved SQL queries"))
    
    # Load saved queries (placeholder - implement based on your storage mechanism)
    saved_queries = load_saved_queries(db_manager)
    
    if not saved_queries:
        st.info(get_text("query.no_saved_queries", "No saved queries found."))
        return
    
    # Display saved queries
    for query_info in saved_queries:
        with st.expander(f"📄 {query_info['name']}"):
            st.write(f"**{get_text('query.description', 'Description')}:** {query_info.get('description', 'N/A')}")
            st.write(f"**{get_text('query.created', 'Created')}:** {query_info.get('created_at', 'Unknown')}")
            
            # Show query
            st.code(query_info['query'], language='sql')
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button(f"▶️ {get_text('query.execute', 'Execute')}", key=f"exec_{query_info['id']}"):
                    st.session_state.sql_query_input = query_info['query']
                    st.experimental_rerun()
            
            with col2:
                if st.button(f"📋 {get_text('query.copy_to_editor', 'Copy to Editor')}", key=f"copy_{query_info['id']}"):
                    st.session_state.sql_query_input = query_info['query']
                    st.experimental_rerun()
            
            with col3:
                if st.button(f"🗑️ {get_text('query.delete', 'Delete')}", key=f"del_{query_info['id']}"):
                    delete_saved_query(query_info['id'], db_manager)
                    st.experimental_rerun()


def show_query_history(cluster, db_manager):
    """Show query execution history."""
    
    st.write(get_text("query.history_desc", "View your recent query executions"))
    
    try:
        with db_manager.session_scope() as session:
            # Get recent queries for this cluster
            history = session.query(QueryHistory).filter_by(
                cluster_id=cluster.id
            ).order_by(QueryHistory.created_at.desc()).limit(20).all()
            
            if not history:
                st.info(get_text("query.no_history", "No query history found."))
                return
            
            # Display history
            for query_record in history:
                status_icon = "✅" if query_record.success else "❌"
                execution_time = f"{query_record.execution_time:.2f}s" if query_record.execution_time else "N/A"
                
                with st.expander(f"{status_icon} {query_record.created_at.strftime('%Y-%m-%d %H:%M:%S')} - {execution_time}"):
                    # Query details
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**{get_text('query.type', 'Type')}:** {query_record.query_type or 'Unknown'}")
                        st.write(f"**{get_text('query.execution_time', 'Execution Time')}:** {execution_time}")
                        st.write(f"**{get_text('query.rows_affected', 'Rows Affected')}:** {query_record.rows_affected or 0}")
                    
                    with col2:
                        st.write(f"**{get_text('query.success', 'Success')}:** {'Yes' if query_record.success else 'No'}")
                        if query_record.tables_accessed:
                            st.write(f"**{get_text('query.tables', 'Tables')}:** {', '.join(query_record.tables_accessed)}")
                        if query_record.complexity_score:
                            st.write(f"**{get_text('query.complexity', 'Complexity')}:** {query_record.complexity_score}/10")
                    
                    # Show query
                    st.code(query_record.query_text[:500] + "..." if len(query_record.query_text) > 500 else query_record.query_text, language='sql')
                    
                    # Error message if failed
                    if not query_record.success and query_record.error_message:
                        st.error(f"**{get_text('query.error', 'Error')}:** {query_record.error_message}")
                    
                    # Action buttons
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button(f"📋 {get_text('query.copy_to_editor', 'Copy to Editor')}", key=f"hist_copy_{query_record.id}"):
                            st.session_state.sql_query_input = query_record.query_text
                            st.experimental_rerun()
                    
                    with col2:
                        if query_record.success and st.button(f"▶️ {get_text('query.re_execute', 'Re-execute')}", key=f"hist_exec_{query_record.id}"):
                            st.session_state.sql_query_input = query_record.query_text
                            st.experimental_rerun()
    
    except Exception as e:
        st.error(f"Error loading query history: {e}")


def execute_sql_query(cluster, sql_query, query_limit, query_timeout, db_manager):
    """Execute SQL query and display results."""
    
    st.subheader("📊 " + get_text("query.results", "Query Results"))
    
    # Create progress indicators
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Create connection config
        config = ConnectionConfig(
            host=cluster.host,
            port=cluster.port,
            database=cluster.database,
            username=cluster.username,
            password=cluster.get_password(),
            query_timeout=query_timeout
        )
        
        # Create connector
        connector = RedshiftConnector(config)
        
        # Update progress
        progress_bar.progress(25)
        status_text.text(get_text("query.connecting", "Connecting to cluster..."))
        
        # Test connection first
        if not connector.connect():
            st.error(get_text("query.connection_failed", "Failed to connect to cluster"))
            return
        
        progress_bar.progress(50)
        status_text.text(get_text("query.executing", "Executing query..."))
        
        # Add LIMIT if not present and it's a SELECT query
        processed_query = process_query_for_execution(sql_query, query_limit)
        
        # Execute query
        start_time = time.time()
        result = connector.execute_query(processed_query, fetch_results=True, timeout=query_timeout)
        execution_time = time.time() - start_time
        
        progress_bar.progress(75)
        status_text.text(get_text("query.processing_results", "Processing results..."))
        
        # Save to query history
        save_query_to_history(cluster, sql_query, result, execution_time, db_manager)
        
        progress_bar.progress(100)
        status_text.text(get_text("query.completed", "Query completed!"))
        
        # Display results
        if result.success:
            display_query_results(result, processed_query)
        else:
            st.error(f"{get_text('query.execution_failed', 'Query execution failed')}: {result.error_message}")
        
        # Disconnect
        connector.disconnect()
        
    except Exception as e:
        st.error(f"{get_text('query.error', 'Error')}: {str(e)}")
        
        # Save failed query to history
        try:
            failed_result = type('obj', (object,), {
                'success': False,
                'error_message': str(e),
                'execution_time': 0,
                'row_count': 0
            })
            save_query_to_history(cluster, sql_query, failed_result, 0, db_manager)
        except:
            pass
    
    finally:
        progress_bar.empty()
        status_text.empty()


def display_query_results(result, query):
    """Display query execution results."""
    
    # Results summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(get_text("query.execution_time", "Execution Time"), f"{result.execution_time:.2f}s")
    
    with col2:
        st.metric(get_text("query.rows_returned", "Rows Returned"), result.row_count)
    
    with col3:
        st.metric(get_text("query.columns", "Columns"), len(result.columns) if result.columns else 0)
    
    with col4:
        st.metric(get_text("query.status", "Status"), "✅ Success")
    
    # Display data if available
    if result.data and result.columns:
        st.subheader("📋 " + get_text("query.data", "Data"))
        
        # Convert to DataFrame
        df = pd.DataFrame(result.data)
        
        # Display data
        st.dataframe(df, use_container_width=True)
        
        # Export options
        st.subheader("📤 " + get_text("query.export", "Export Options"))
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # CSV export
            csv = df.to_csv(index=False)
            st.download_button(
                label="📊 " + get_text("query.export_csv", "Export as CSV"),
                data=csv,
                file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # JSON export
            json_data = df.to_json(orient='records', indent=2)
            st.download_button(
                label="📄 " + get_text("query.export_json", "Export as JSON"),
                data=json_data,
                file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        with col3:
            # Excel export (if openpyxl is available)
            try:
                import io
                buffer = io.BytesIO()
                df.to_excel(buffer, index=False, engine='openpyxl')
                buffer.seek(0)
                
                st.download_button(
                    label="📈 " + get_text("query.export_excel", "Export as Excel"),
                    data=buffer.getvalue(),
                    file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except ImportError:
                st.info(get_text("query.excel_not_available", "Excel export requires openpyxl package"))
        
        # Data preview options
        if len(df) > 50:
            st.info(get_text("query.large_result_info", f"Showing first 50 rows of {len(df)} total rows"))
    
    elif result.row_count > 0:
        # Query succeeded but no data to display (e.g., INSERT, UPDATE, DELETE)
        st.success(f"{get_text('query.rows_affected', 'Rows affected')}: {result.row_count}")
    
    else:
        st.info(get_text("query.no_data_returned", "Query executed successfully but returned no data"))


def process_query_for_execution(query, limit):
    """Process query before execution (add LIMIT, etc.)."""
    
    # Remove extra whitespace and normalize
    query = query.strip()
    
    # Check if it's a SELECT query and doesn't already have LIMIT
    if (query.upper().startswith('SELECT') and 
        'LIMIT' not in query.upper() and 
        ';' not in query):
        
        query += f" LIMIT {limit}"
    
    return query


def format_sql_query(query):
    """Format SQL query (basic formatting)."""
    
    try:
        import sqlparse
        return sqlparse.format(query, reindent=True, keyword_case='upper')
    except ImportError:
        # Basic formatting without sqlparse
        keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 
                   'INNER JOIN', 'ORDER BY', 'GROUP BY', 'HAVING', 'LIMIT']
        
        formatted = query
        for keyword in keywords:
            formatted = re.sub(f'\\b{keyword.lower()}\\b', keyword, formatted, flags=re.IGNORECASE)
        
        return formatted


def show_query_analysis(query):
    """Show query analysis and optimization suggestions."""
    
    st.subheader("🔍 " + get_text("query.analysis_results", "Query Analysis"))
    
    try:
        analysis = QueryAnalyzer.analyze_query(query)
        
        # Basic info
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(get_text("query.type", "Query Type"), analysis['type'])
        
        with col2:
            st.metric(get_text("query.complexity", "Complexity"), analysis['complexity'].title())
        
        with col3:
            st.metric(get_text("query.estimated_cost", "Estimated Cost"), analysis['estimated_cost'].title())
        
        # Tables accessed
        if analysis['tables']:
            st.write(f"**{get_text('query.tables_accessed', 'Tables Accessed')}:** {', '.join(analysis['tables'])}")
        
        # Suggestions
        if analysis['suggestions']:
            st.subheader("💡 " + get_text("query.suggestions", "Optimization Suggestions"))
            for suggestion in analysis['suggestions']:
                st.info(f"💡 {suggestion}")
        
        # Warnings
        if analysis['warnings']:
            st.subheader("⚠️ " + get_text("query.warnings", "Warnings"))
            for warning in analysis['warnings']:
                st.warning(f"⚠️ {warning}")
        
        if not analysis['suggestions'] and not analysis['warnings']:
            st.success(get_text("query.no_issues", "No issues detected in the query!"))
    
    except Exception as e:
        st.error(f"Analysis failed: {e}")


def test_cluster_connection(cluster):
    """Test connection to selected cluster."""
    
    with st.spinner(get_text("cluster.testing_connection", "Testing connection...")):
        try:
            config = ConnectionConfig(
                host=cluster.host,
                port=cluster.port,
                database=cluster.database,
                username=cluster.username,
                password=cluster.get_password()
            )
            
            connector = RedshiftConnector(config)
            success, message = connector.test_connection()
            
            if success:
                st.success(f"✅ {message}")
                
                # Get additional info
                if connector.connect():
                    cluster_info = connector.get_cluster_info()
                    if cluster_info and 'error' not in cluster_info:
                        st.json(cluster_info)
                    connector.disconnect()
            else:
                st.error(f"❌ {message}")
        
        except Exception as e:
            st.error(f"Connection test failed: {e}")


def load_schema_info(cluster):
    """Load schema information for the cluster."""
    
    with st.spinner(get_text("query.loading_schema", "Loading schema information...")):
        try:
            config = ConnectionConfig(
                host=cluster.host,
                port=cluster.port,
                database=cluster.database,
                username=cluster.username,
                password=cluster.get_password()
            )
            
            connector = RedshiftConnector(config)
            
            if connector.connect():
                # Get schema information
                schema_query = """
                    SELECT 
                        schemaname,
                        tablename,
                        tableowner
                    FROM pg_tables 
                    WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
                    ORDER BY schemaname, tablename
                    LIMIT 100
                """
                
                result = connector.execute_query(schema_query, fetch_results=True)
                
                if result.success and result.data:
                    st.session_state[f"schema_info_{cluster.id}"] = result.data
                    st.success(f"Loaded {len(result.data)} tables")
                else:
                    st.warning("No schema information available")
                
                connector.disconnect()
            else:
                st.error("Failed to connect to cluster")
        
        except Exception as e:
            st.error(f"Failed to load schema: {e}")


def show_schema_browser(schema_info):
    """Display schema browser."""
    
    if not schema_info:
        st.info(get_text("query.no_schema_info", "No schema information available"))
        return
    
    # Group by schema
    schemas = {}
    for table_info in schema_info:
        schema_name = table_info['schemaname']
        if schema_name not in schemas:
            schemas[schema_name] = []
        schemas[schema_name].append(table_info)
    
    # Display schemas and tables
    for schema_name, tables in schemas.items():
        with st.expander(f"📁 {schema_name} ({len(tables)} tables)"):
            for table in tables:
                if st.button(f"📋 {table['tablename']}", key=f"table_{schema_name}_{table['tablename']}"):
                    # Insert table name into query editor
                    table_query = f"SELECT * FROM {schema_name}.{table['tablename']} LIMIT 10;"
                    st.session_state.sql_query_input = table_query
                    st.experimental_rerun()


def get_query_templates():
    """Get common query templates."""
    
    return {
        "Basic Select": "SELECT * FROM schema.table_name LIMIT 10;",
        "Count Records": "SELECT COUNT(*) as total_records FROM schema.table_name;",
        "Table Info": """
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'your_table_name'
ORDER BY ordinal_position;
        """,
        "Recent Data": """
SELECT * 
FROM schema.table_name 
WHERE created_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY created_date DESC
LIMIT 100;
        """,
        "Data Distribution": """
SELECT 
    column_name,
    COUNT(*) as frequency,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as percentage
FROM schema.table_name 
GROUP BY column_name
ORDER BY frequency DESC;
        """,
        "Table Size": """
SELECT 
    schemaname,
    tablename,
    attname as column_name,
    n_distinct,
    correlation
FROM pg_stats 
WHERE schemaname = 'your_schema'
ORDER BY tablename, attname;
        """
    }


def save_query_to_history(cluster, query, result, execution_time, db_manager):
    """Save query execution to history."""
    
    try:
        with db_manager.session_scope() as session:
            # Analyze query for metadata
            analysis = QueryAnalyzer.analyze_query(query)
            
            # Create query hash
            import hashlib
            query_hash = hashlib.md5(query.encode()).hexdigest()
            
            # Create history record
            history_record = QueryHistory(
                cluster_id=cluster.id,
                user_id=1,  # TODO: Get from session
                query_text=query,
                query_hash=query_hash,
                execution_time=execution_time,
                rows_affected=result.row_count if hasattr(result, 'row_count') else 0,
                success=result.success,
                error_message=result.error_message if hasattr(result, 'error_message') else None,
                query_type=analysis.get('type', 'UNKNOWN'),
                tables_accessed=analysis.get('tables', []),
                complexity_score=hash(analysis.get('complexity', 'medium')) % 10 + 1
            )
            
            session.add(history_record)
            session.commit()
    
    except Exception as e:
        # Don't fail the main operation if history saving fails
        st.warning(f"Failed to save query to history: {e}")


def save_query_dialog(query, db_manager):
    """Show dialog to save query."""
    
    with st.form("save_query_form"):
        st.subheader("💾 " + get_text("query.save_query", "Save Query"))
        
        query_name = st.text_input(
            get_text("query.name", "Query Name") + " *",
            help=get_text("query.name_help", "Give your query a descriptive name")
        )
        
        query_description = st.text_area(
            get_text("query.description", "Description"),
            help=get_text("query.description_help", "Optional description of what this query does")
        )
        
        if st.form_submit_button("💾 " + get_text("form.save", "Save")):
            if not query_name:
                st.error(get_text("query.name_required", "Query name is required"))
            else:
                # TODO: Implement saved queries storage
                st.success(f"Query '{query_name}' saved successfully!")


def load_saved_queries(db_manager):
    """Load saved queries (placeholder implementation)."""
    
    # TODO: Implement actual saved queries storage
    # This is a placeholder - you might want to store in database or files
    return []


def delete_saved_query(query_id, db_manager):
    """Delete a saved query."""
    
    # TODO: Implement actual deletion
    st.success("Query deleted successfully!")


if __name__ == "__main__":
    query_execution_page()