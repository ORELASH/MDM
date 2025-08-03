"""
RedshiftManager Cluster Management Page
Comprehensive cluster management interface for Amazon Redshift connections.
"""

import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime
import json

# Import our models
try:
    from models.database_models import get_database_manager, RedshiftCluster, ConnectionStatusType
    from models.redshift_connection_model import ConnectionConfig, RedshiftConnector, SSLMode
    from models.encryption_model import get_encryption_manager
    from utils.i18n_helper import get_text, apply_rtl_css, get_streamlit_helper
except ImportError as e:
    st.error(f"Failed to import required modules: {e}")
    st.stop()


def cluster_management_page():
    """Main cluster management page."""
    
    # Apply RTL CSS if needed
    apply_rtl_css()
    
    # Page title
    st.title("🔌 " + get_text("nav.clusters", "Cluster Management"))
    st.markdown("---")
    
    # Get database manager
    db_manager = get_database_manager()
    
    # Sidebar for actions
    with st.sidebar:
        st.header(get_text("cluster.actions", "Cluster Actions"))
        
        action = st.selectbox(
            get_text("cluster.select_action", "Select Action"),
            [
                get_text("cluster.view_all", "View All Clusters"),
                get_text("cluster.add", "Add Cluster"),
                get_text("cluster.edit", "Edit Cluster"),
                get_text("cluster.delete", "Delete Cluster")
            ]
        )
    
    # Main content area
    if action == get_text("cluster.view_all", "View All Clusters"):
        show_all_clusters(db_manager)
    elif action == get_text("cluster.add", "Add Cluster"):
        add_cluster_form(db_manager)
    elif action == get_text("cluster.edit", "Edit Cluster"):
        edit_cluster_form(db_manager)
    elif action == get_text("cluster.delete", "Delete Cluster"):
        delete_cluster_form(db_manager)


def show_all_clusters(db_manager):
    """Display all clusters in a table."""
    
    st.subheader("📋 " + get_text("cluster.all_clusters", "All Clusters"))
    
    try:
        with db_manager.session_scope() as session:
            clusters = session.query(RedshiftCluster).all()
            
            if not clusters:
                st.info(get_text("cluster.no_clusters", "No clusters configured yet. Add your first cluster!"))
                return
            
            # Create DataFrame for display
            cluster_data = []
            for cluster in clusters:
                cluster_data.append({
                    "ID": cluster.id,
                    get_text("cluster.name", "Name"): cluster.name,
                    get_text("cluster.host", "Host"): cluster.host,
                    get_text("cluster.port", "Port"): cluster.port,
                    get_text("cluster.database", "Database"): cluster.database,
                    get_text("cluster.environment", "Environment"): cluster.environment,
                    get_text("cluster.status", "Status"): cluster.status.value,
                    get_text("cluster.last_test", "Last Test"): cluster.last_connection_test.strftime("%Y-%m-%d %H:%M") if cluster.last_connection_test else "Never",
                    get_text("cluster.active", "Active"): "✅" if cluster.is_active else "❌"
                })
            
            df = pd.DataFrame(cluster_data)
            st.dataframe(df, use_container_width=True)
            
            # Test all connections button
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.button("🔍 " + get_text("cluster.test_all", "Test All Connections")):
                    test_all_connections(session, clusters)
            
            with col2:
                if st.button("📊 " + get_text("cluster.cluster_stats", "Cluster Statistics")):
                    show_cluster_statistics(clusters)
    
    except Exception as e:
        st.error(f"Error loading clusters: {e}")


def add_cluster_form(db_manager):
    """Form to add a new cluster."""
    
    st.subheader("➕ " + get_text("cluster.add", "Add New Cluster"))
    
    with st.form("add_cluster_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input(
                get_text("cluster.name", "Cluster Name") + " *",
                help=get_text("cluster.name_help", "A unique name for this cluster")
            )
            
            host = st.text_input(
                get_text("cluster.host", "Host") + " *",
                help=get_text("cluster.host_help", "Redshift cluster endpoint")
            )
            
            port = st.number_input(
                get_text("cluster.port", "Port"),
                value=5439,
                min_value=1,
                max_value=65535
            )
            
            database = st.text_input(
                get_text("cluster.database", "Database") + " *",
                value="dev",
                help=get_text("cluster.database_help", "Default database name")
            )
        
        with col2:
            username = st.text_input(
                get_text("cluster.username", "Username") + " *",
                help=get_text("cluster.username_help", "Database user with appropriate permissions")
            )
            
            password = st.text_input(
                get_text("cluster.password", "Password") + " *",
                type="password",
                help=get_text("cluster.password_help", "Password will be encrypted and stored securely")
            )
            
            ssl_mode = st.selectbox(
                get_text("cluster.ssl_mode", "SSL Mode"),
                options=[mode.value for mode in SSLMode],
                index=3  # Default to 'require'
            )
            
            environment = st.selectbox(
                get_text("cluster.environment", "Environment"),
                options=["development", "staging", "production"],
                help=get_text("cluster.environment_help", "Environment type for this cluster")
            )
        
        # Advanced settings
        with st.expander("🔧 " + get_text("cluster.advanced_settings", "Advanced Settings")):
            col3, col4 = st.columns(2)
            
            with col3:
                connection_timeout = st.number_input(
                    get_text("cluster.connection_timeout", "Connection Timeout (seconds)"),
                    value=30,
                    min_value=1,
                    max_value=300
                )
                
                query_timeout = st.number_input(
                    get_text("cluster.query_timeout", "Query Timeout (seconds)"),
                    value=300,
                    min_value=1,
                    max_value=3600
                )
            
            with col4:
                max_connections = st.number_input(
                    get_text("cluster.max_connections", "Max Connections"),
                    value=10,
                    min_value=1,
                    max_value=100
                )
                
                verify_ssl = st.checkbox(
                    get_text("cluster.verify_ssl", "Verify SSL Certificate"),
                    value=True
                )
        
        description = st.text_area(
            get_text("cluster.description", "Description"),
            help=get_text("cluster.description_help", "Optional description for this cluster")
        )
        
        # Form submission
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col2:
            test_connection = st.form_submit_button(
                "🔍 " + get_text("cluster.test_connection", "Test Connection")
            )
        
        with col3:
            submit = st.form_submit_button(
                "💾 " + get_text("form.save", "Save Cluster")
            )
        
        # Handle form submission
        if test_connection or submit:
            if not all([name, host, database, username, password]):
                st.error(get_text("form.required_fields", "Please fill in all required fields (marked with *)"))
                return
            
            # Create connection config for testing
            config = ConnectionConfig(
                host=host,
                port=port,
                database=database,
                username=username,
                password=password,
                ssl_mode=SSLMode(ssl_mode),
                connect_timeout=connection_timeout,
                query_timeout=query_timeout,
                max_connections=max_connections,
                verify_ssl=verify_ssl
            )
            
            if test_connection:
                test_single_connection(config)
            
            if submit:
                success = save_cluster(
                    db_manager, name, host, port, database, username, password,
                    ssl_mode, environment, connection_timeout, query_timeout,
                    max_connections, verify_ssl, description
                )
                
                if success:
                    st.success(get_text("cluster.saved_successfully", "Cluster saved successfully!"))
                    st.experimental_rerun()


def edit_cluster_form(db_manager):
    """Form to edit an existing cluster."""
    
    st.subheader("✏️ " + get_text("cluster.edit", "Edit Cluster"))
    
    try:
        with db_manager.session_scope() as session:
            clusters = session.query(RedshiftCluster).all()
            
            if not clusters:
                st.info(get_text("cluster.no_clusters_to_edit", "No clusters available to edit."))
                return
            
            # Select cluster to edit
            cluster_options = {f"{cluster.name} ({cluster.host})": cluster.id for cluster in clusters}
            selected_cluster_key = st.selectbox(
                get_text("cluster.select_to_edit", "Select cluster to edit"),
                options=list(cluster_options.keys())
            )
            
            if selected_cluster_key:
                cluster_id = cluster_options[selected_cluster_key]
                cluster = session.query(RedshiftCluster).filter_by(id=cluster_id).first()
                
                if cluster:
                    # Pre-populate form with existing values
                    show_edit_form(db_manager, cluster)
    
    except Exception as e:
        st.error(f"Error loading clusters: {e}")


def show_edit_form(db_manager, cluster):
    """Show the edit form with pre-populated values."""
    
    with st.form("edit_cluster_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input(
                get_text("cluster.name", "Cluster Name") + " *",
                value=cluster.name
            )
            
            host = st.text_input(
                get_text("cluster.host", "Host") + " *",
                value=cluster.host
            )
            
            port = st.number_input(
                get_text("cluster.port", "Port"),
                value=cluster.port,
                min_value=1,
                max_value=65535
            )
            
            database = st.text_input(
                get_text("cluster.database", "Database") + " *",
                value=cluster.database
            )
        
        with col2:
            username = st.text_input(
                get_text("cluster.username", "Username") + " *",
                value=cluster.username
            )
            
            # Password field (don't show existing password)
            password = st.text_input(
                get_text("cluster.password", "Password") + " *",
                type="password",
                help=get_text("cluster.password_edit_help", "Leave empty to keep existing password")
            )
            
            ssl_mode = st.selectbox(
                get_text("cluster.ssl_mode", "SSL Mode"),
                options=[mode.value for mode in SSLMode],
                index=list(SSLMode).index(SSLMode(cluster.ssl_mode))
            )
            
            environment = st.selectbox(
                get_text("cluster.environment", "Environment"),
                options=["development", "staging", "production"],
                index=["development", "staging", "production"].index(cluster.environment)
            )
        
        # Advanced settings
        with st.expander("🔧 " + get_text("cluster.advanced_settings", "Advanced Settings")):
            col3, col4 = st.columns(2)
            
            with col3:
                connection_timeout = st.number_input(
                    get_text("cluster.connection_timeout", "Connection Timeout (seconds)"),
                    value=cluster.connection_timeout,
                    min_value=1,
                    max_value=300
                )
                
                query_timeout = st.number_input(
                    get_text("cluster.query_timeout", "Query Timeout (seconds)"),
                    value=cluster.query_timeout,
                    min_value=1,
                    max_value=3600
                )
            
            with col4:
                max_connections = st.number_input(
                    get_text("cluster.max_connections", "Max Connections"),
                    value=cluster.max_connections,
                    min_value=1,
                    max_value=100
                )
                
                is_active = st.checkbox(
                    get_text("cluster.active", "Active"),
                    value=cluster.is_active
                )
        
        description = st.text_area(
            get_text("cluster.description", "Description"),
            value=cluster.description or ""
        )
        
        # Form submission
        col1, col2 = st.columns(2)
        
        with col1:
            update = st.form_submit_button(
                "💾 " + get_text("form.update", "Update Cluster")
            )
        
        with col2:
            test_connection = st.form_submit_button(
                "🔍 " + get_text("cluster.test_connection", "Test Connection")
            )
        
        # Handle form submission
        if update or test_connection:
            # Use existing password if not provided
            final_password = password if password else cluster.get_password()
            
            if not all([name, host, database, username, final_password]):
                st.error(get_text("form.required_fields", "Please fill in all required fields"))
                return
            
            # Create connection config
            config = ConnectionConfig(
                host=host,
                port=port,
                database=database,
                username=username,
                password=final_password,
                ssl_mode=SSLMode(ssl_mode),
                connect_timeout=connection_timeout,
                query_timeout=query_timeout,
                max_connections=max_connections
            )
            
            if test_connection:
                test_single_connection(config)
            
            if update:
                success = update_cluster(
                    db_manager, cluster.id, name, host, port, database,
                    username, final_password, ssl_mode, environment,
                    connection_timeout, query_timeout, max_connections,
                    is_active, description
                )
                
                if success:
                    st.success(get_text("cluster.updated_successfully", "Cluster updated successfully!"))
                    st.experimental_rerun()


def delete_cluster_form(db_manager):
    """Form to delete an existing cluster."""
    
    st.subheader("🗑️ " + get_text("cluster.delete", "Delete Cluster"))
    st.warning(get_text("cluster.delete_warning", "⚠️ Deleting a cluster will remove all associated data and cannot be undone!"))
    
    try:
        with db_manager.session_scope() as session:
            clusters = session.query(RedshiftCluster).all()
            
            if not clusters:
                st.info(get_text("cluster.no_clusters_to_delete", "No clusters available to delete."))
                return
            
            # Select cluster to delete
            cluster_options = {f"{cluster.name} ({cluster.host})": cluster.id for cluster in clusters}
            selected_cluster_key = st.selectbox(
                get_text("cluster.select_to_delete", "Select cluster to delete"),
                options=list(cluster_options.keys())
            )
            
            if selected_cluster_key:
                cluster_id = cluster_options[selected_cluster_key]
                cluster = session.query(RedshiftCluster).filter_by(id=cluster_id).first()
                
                if cluster:
                    # Show cluster details
                    with st.expander("📋 " + get_text("cluster.details", "Cluster Details")):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**{get_text('cluster.name', 'Name')}:** {cluster.name}")
                            st.write(f"**{get_text('cluster.host', 'Host')}:** {cluster.host}")
                            st.write(f"**{get_text('cluster.database', 'Database')}:** {cluster.database}")
                        
                        with col2:
                            st.write(f"**{get_text('cluster.environment', 'Environment')}:** {cluster.environment}")
                            st.write(f"**{get_text('cluster.status', 'Status')}:** {cluster.status.value}")
                            st.write(f"**{get_text('cluster.created', 'Created')}:** {cluster.created_at.strftime('%Y-%m-%d %H:%M')}")
                    
                    # Confirmation
                    st.error(get_text("cluster.confirm_delete", "Type 'DELETE' to confirm deletion:"))
                    confirmation = st.text_input(
                        get_text("cluster.confirmation", "Confirmation"),
                        placeholder="DELETE"
                    )
                    
                    if st.button("🗑️ " + get_text("cluster.delete_permanently", "Delete Permanently"), type="primary"):
                        if confirmation == "DELETE":
                            success = delete_cluster(db_manager, cluster_id)
                            if success:
                                st.success(get_text("cluster.deleted_successfully", "Cluster deleted successfully!"))
                                st.experimental_rerun()
                        else:
                            st.error(get_text("cluster.confirmation_required", "Please type 'DELETE' to confirm"))
    
    except Exception as e:
        st.error(f"Error loading clusters: {e}")


def test_single_connection(config: ConnectionConfig):
    """Test a single connection configuration."""
    
    with st.spinner(get_text("cluster.testing_connection", "Testing connection...")):
        try:
            connector = RedshiftConnector(config)
            success, message = connector.test_connection()
            
            if success:
                st.success(f"✅ {get_text('cluster.connection_successful', 'Connection successful!')}: {message}")
                
                # Get additional cluster info if connection works
                try:
                    cluster_info = connector.get_cluster_info()
                    if cluster_info and 'error' not in cluster_info:
                        with st.expander("ℹ️ " + get_text("cluster.connection_info", "Connection Information")):
                            st.json(cluster_info)
                except Exception as e:
                    st.warning(f"Connection successful but couldn't get cluster info: {e}")
            else:
                st.error(f"❌ {get_text('cluster.connection_failed', 'Connection failed')}: {message}")
        
        except Exception as e:
            st.error(f"❌ {get_text('cluster.connection_error', 'Connection error')}: {e}")


def test_all_connections(session, clusters):
    """Test all cluster connections."""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = []
    
    for i, cluster in enumerate(clusters):
        status_text.text(f"Testing {cluster.name}...")
        
        try:
            config = ConnectionConfig(
                host=cluster.host,
                port=cluster.port,
                database=cluster.database,
                username=cluster.username,
                password=cluster.get_password(),
                ssl_mode=SSLMode(cluster.ssl_mode),
                connect_timeout=cluster.connection_timeout,
                query_timeout=cluster.query_timeout,
                max_connections=cluster.max_connections
            )
            
            connector = RedshiftConnector(config)
            success, message = connector.test_connection()
            
            # Update cluster status
            cluster.status = ConnectionStatusType.ACTIVE if success else ConnectionStatusType.ERROR
            cluster.last_connection_test = datetime.utcnow()
            cluster.connection_test_result = message
            
            results.append({
                "Cluster": cluster.name,
                "Status": "✅ Success" if success else "❌ Failed",
                "Message": message
            })
            
        except Exception as e:
            cluster.status = ConnectionStatusType.ERROR
            cluster.last_connection_test = datetime.utcnow()
            cluster.connection_test_result = str(e)
            
            results.append({
                "Cluster": cluster.name,
                "Status": "❌ Error",
                "Message": str(e)
            })
        
        progress_bar.progress((i + 1) / len(clusters))
    
    # Commit changes
    session.commit()
    
    # Show results
    status_text.text("Test completed!")
    st.dataframe(pd.DataFrame(results), use_container_width=True)


def show_cluster_statistics(clusters):
    """Show cluster statistics."""
    
    st.subheader("📊 " + get_text("cluster.statistics", "Cluster Statistics"))
    
    # Basic stats
    total_clusters = len(clusters)
    active_clusters = sum(1 for c in clusters if c.is_active)
    connected_clusters = sum(1 for c in clusters if c.status == ConnectionStatusType.ACTIVE)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(get_text("cluster.total", "Total Clusters"), total_clusters)
    
    with col2:
        st.metric(get_text("cluster.active", "Active"), active_clusters)
    
    with col3:
        st.metric(get_text("cluster.connected", "Connected"), connected_clusters)
    
    with col4:
        health_percentage = (connected_clusters / total_clusters * 100) if total_clusters > 0 else 0
        st.metric(get_text("cluster.health", "Health"), f"{health_percentage:.1f}%")
    
    # Environment breakdown
    env_counts = {}
    for cluster in clusters:
        env_counts[cluster.environment] = env_counts.get(cluster.environment, 0) + 1
    
    if env_counts:
        st.subheader(get_text("cluster.by_environment", "Clusters by Environment"))
        env_df = pd.DataFrame(list(env_counts.items()), columns=["Environment", "Count"])
        st.bar_chart(env_df.set_index("Environment"))


def save_cluster(db_manager, name, host, port, database, username, password,
                ssl_mode, environment, connection_timeout, query_timeout,
                max_connections, verify_ssl, description):
    """Save a new cluster to the database."""
    
    try:
        with db_manager.session_scope() as session:
            # Check if cluster name already exists
            existing = session.query(RedshiftCluster).filter_by(name=name).first()
            if existing:
                st.error(get_text("cluster.name_exists", "A cluster with this name already exists"))
                return False
            
            # Create new cluster
            cluster = RedshiftCluster(
                name=name,
                host=host,
                port=port,
                database=database,
                username=username,
                ssl_mode=ssl_mode,
                environment=environment,
                connection_timeout=connection_timeout,
                query_timeout=query_timeout,
                max_connections=max_connections,
                description=description,
                status=ConnectionStatusType.INACTIVE
            )
            
            # Set encrypted password
            cluster.set_password(password)
            
            session.add(cluster)
            session.commit()
            
            return True
    
    except Exception as e:
        st.error(f"Error saving cluster: {e}")
        return False


def update_cluster(db_manager, cluster_id, name, host, port, database,
                  username, password, ssl_mode, environment,
                  connection_timeout, query_timeout, max_connections,
                  is_active, description):
    """Update an existing cluster in the database."""
    
    try:
        with db_manager.session_scope() as session:
            cluster = session.query(RedshiftCluster).filter_by(id=cluster_id).first()
            
            if not cluster:
                st.error(get_text("cluster.not_found", "Cluster not found"))
                return False
            
            # Update fields
            cluster.name = name
            cluster.host = host
            cluster.port = port
            cluster.database = database
            cluster.username = username
            cluster.ssl_mode = ssl_mode
            cluster.environment = environment
            cluster.connection_timeout = connection_timeout
            cluster.query_timeout = query_timeout
            cluster.max_connections = max_connections
            cluster.is_active = is_active
            cluster.description = description
            
            # Update password if provided
            if password:
                cluster.set_password(password)
            
            session.commit()
            return True
    
    except Exception as e:
        st.error(f"Error updating cluster: {e}")
        return False


def delete_cluster(db_manager, cluster_id):
    """Delete a cluster from the database."""
    
    try:
        with db_manager.session_scope() as session:
            cluster = session.query(RedshiftCluster).filter_by(id=cluster_id).first()
            
            if not cluster:
                st.error(get_text("cluster.not_found", "Cluster not found"))
                return False
            
            session.delete(cluster)
            session.commit()
            return True
    
    except Exception as e:
        st.error(f"Error deleting cluster: {e}")
        return False


if __name__ == "__main__":
    cluster_management_page()