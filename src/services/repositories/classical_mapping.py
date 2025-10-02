#!/usr/bin/env python3
"""PAKE System - Classical Mapping Configuration
Classical mapping to connect domain models to database schema.

This module uses SQLAlchemy's classical mapping (imperative mapping) to bridge
the gap between pure domain models and the database. This approach inverts
the dependency: the ORM layer depends on the domain model, not the other way around.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Table, Column, Integer, String, Text, Boolean, DateTime, Float,
    ForeignKey, Index, UniqueConstraint, CheckConstraint, JSON, MetaData
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import mapper, relationship

from ..domain.models import (
    User,
    SearchHistory,
    SavedSearch,
    ServiceRegistry,
    ServiceHealthCheck,
    ServiceMetrics,
    APIGatewayRoute,
    SystemAlert,
)

logger = logging.getLogger(__name__)

# Create metadata for all tables
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    }
)


# User table definition
users_table = Table(
    'users', metadata,
    Column('id', PostgresUUID(as_uuid=False), primary_key=True),
    Column('username', String(50), unique=True, nullable=False),
    Column('email', String(255), unique=True, nullable=False),
    Column('REDACTED_SECRET_hash', String(255), nullable=False),
    Column('full_name', String(255)),
    Column('is_active', Boolean, default=True),
    Column('is_admin', Boolean, default=False),
    Column('preferences', JSON),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
    Column('last_login', DateTime),
    
    # Indexes
    Index('ix_users_email', 'email'),
    Index('ix_users_username', 'username'),
    Index('ix_users_is_active', 'is_active'),
    Index('ix_users_created_at', 'created_at'),
)


# Search History table definition
search_history_table = Table(
    'search_history', metadata,
    Column('id', PostgresUUID(as_uuid=False), primary_key=True),
    Column('user_id', PostgresUUID(as_uuid=False), nullable=True),  # Nullable for anonymous
    Column('query', Text, nullable=False),
    Column('sources', JSON, nullable=False),
    Column('results_count', Integer, default=0),
    Column('execution_time_ms', Float),
    Column('cache_hit', Boolean, default=False),
    Column('quality_score', Float),
    Column('query_metadata', JSON),
    Column('created_at', DateTime, default=datetime.utcnow),
    
    # Indexes
    Index('ix_search_history_user_id', 'user_id'),
    Index('ix_search_history_created_at', 'created_at'),
    Index('ix_search_history_cache_hit', 'cache_hit'),
    Index('ix_search_history_query', 'query'),
)


# Saved Search table definition
saved_searches_table = Table(
    'saved_searches', metadata,
    Column('id', PostgresUUID(as_uuid=False), primary_key=True),
    Column('user_id', PostgresUUID(as_uuid=False), nullable=False),
    Column('name', String(255), nullable=False),
    Column('query', Text, nullable=False),
    Column('sources', JSON, nullable=False),
    Column('filters', JSON),
    Column('is_public', Boolean, default=False),
    Column('tags', JSON),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
    
    # Indexes
    Index('ix_saved_searches_user_id', 'user_id'),
    Index('ix_saved_searches_is_public', 'is_public'),
    Index('ix_saved_searches_created_at', 'created_at'),
    Index('ix_saved_searches_name', 'name'),
)


# Service Registry table definition
service_registry_table = Table(
    'service_registry', metadata,
    Column('service_id', PostgresUUID(as_uuid=True), primary_key=True),
    Column('service_name', String(255), unique=True, nullable=False),
    Column('service_version', String(50), nullable=False),
    Column('service_type', String(50), nullable=False),
    Column('environment', String(50), nullable=False),
    Column('base_url', String(500), nullable=False),
    Column('health_check_url', String(500), nullable=False),
    Column('health_check_interval_seconds', Integer, default=30),
    Column('health_timeout_seconds', Integer, default=5),
    Column('resource_requirements', JSON),
    Column('endpoints', JSON),
    Column('dependencies', JSON),
    Column('labels', JSON),
    Column('status', String(50), default='HEALTHY'),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
    Column('deployed_at', DateTime),
    
    # Indexes
    Index('ix_service_registry_name', 'service_name'),
    Index('ix_service_registry_env_type', 'environment', 'service_type'),
    Index('ix_service_registry_status', 'status'),
    Index('ix_service_registry_created_at', 'created_at'),
)


# Service Health Check table definition
service_health_checks_table = Table(
    'service_health_checks', metadata,
    Column('health_check_id', PostgresUUID(as_uuid=True), primary_key=True),
    Column('service_id', PostgresUUID(as_uuid=True), ForeignKey('service_registry.service_id'), nullable=False),
    Column('status', String(50), nullable=False),
    Column('response_time_ms', Float, nullable=False),
    Column('error_message', Text),
    Column('check_type', String(50), default='HTTP'),
    Column('timestamp', DateTime, default=datetime.utcnow),
    
    # Indexes
    Index('ix_health_checks_service_timestamp', 'service_id', 'timestamp'),
    Index('ix_health_checks_status', 'status'),
    Index('ix_health_checks_timestamp', 'timestamp'),
)


# Service Metrics table definition
service_metrics_table = Table(
    'service_metrics', metadata,
    Column('metric_id', PostgresUUID(as_uuid=True), primary_key=True),
    Column('service_id', PostgresUUID(as_uuid=True), ForeignKey('service_registry.service_id'), nullable=False),
    Column('metric_name', String(255), nullable=False),
    Column('metric_value', Float, nullable=False),
    Column('metric_labels', JSON),
    Column('timestamp', DateTime, default=datetime.utcnow),
    
    # Indexes
    Index('ix_metrics_service_name_timestamp', 'service_id', 'metric_name', 'timestamp'),
    Index('ix_metrics_timestamp', 'timestamp'),
    Index('ix_metrics_name', 'metric_name'),
)


# API Gateway Route table definition
api_gateway_routes_table = Table(
    'api_gateway_routes', metadata,
    Column('route_id', PostgresUUID(as_uuid=True), primary_key=True),
    Column('path', String(500), nullable=False),
    Column('method', String(10), nullable=False),
    Column('target_service', String(255), nullable=False),
    Column('target_path', String(500), nullable=False),
    Column('description', Text),
    Column('authentication_required', Boolean, default=True),
    Column('rate_limit', JSON),
    Column('is_active', Boolean, default=True),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
    
    # Indexes and constraints
    Index('ix_routes_path_method', 'path', 'method'),
    Index('ix_routes_target_service', 'target_service'),
    Index('ix_routes_active', 'is_active'),
    UniqueConstraint('path', 'method', name='uq_routes_path_method'),
)


# System Alert table definition
system_alerts_table = Table(
    'system_alerts', metadata,
    Column('alert_id', PostgresUUID(as_uuid=True), primary_key=True),
    Column('alert_name', String(255), nullable=False),
    Column('severity', String(50), nullable=False),
    Column('status', String(50), default='ACTIVE'),
    Column('message', Text, nullable=False),
    Column('description', Text),
    Column('service_name', String(255)),
    Column('labels', JSON),
    Column('acknowledged_by', String(255)),
    Column('acknowledged_at', DateTime),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('resolved_at', DateTime),
    
    # Indexes and constraints
    Index('ix_alerts_severity_status', 'severity', 'status'),
    Index('ix_alerts_service', 'service_name'),
    Index('ix_alerts_created_at', 'created_at'),
    CheckConstraint("severity IN ('critical', 'high', 'medium', 'low', 'info')", name='ck_alerts_severity'),
    CheckConstraint("status IN ('active', 'acknowledged', 'resolved')", name='ck_alerts_status'),
)


def start_mappers():
    """Initialize all mappers to connect domain models to database tables"""
    try:
        # Map User domain model to users table
        mapper(User, users_table)
        
        # Map SearchHistory domain model to search_history table
        mapper(SearchHistory, search_history_table)
        
        # Map SavedSearch domain model to saved_searches table
        mapper(SavedSearch, saved_searches_table)
        
        # Map ServiceRegistry domain model to service_registry table
        mapper(ServiceRegistry, service_registry_table)
        
        # Map ServiceHealthCheck domain model to service_health_checks table
        mapper(ServiceHealthCheck, service_health_checks_table)
        
        # Map ServiceMetrics domain model to service_metrics table
        mapper(ServiceMetrics, service_metrics_table)
        
        # Map APIGatewayRoute domain model to api_gateway_routes table
        mapper(APIGatewayRoute, api_gateway_routes_table)
        
        # Map SystemAlert domain model to system_alerts table
        mapper(SystemAlert, system_alerts_table)
        
        logger.info("All domain model mappers initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing mappers: {e}")
        raise


def create_all_tables(engine):
    """Create all tables in the database"""
    try:
        metadata.create_all(engine)
        logger.info("All database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def drop_all_tables(engine):
    """Drop all tables from the database"""
    try:
        metadata.drop_all(engine)
        logger.info("All database tables dropped successfully")
    except Exception as e:
        logger.error(f"Error dropping database tables: {e}")
        raise


# Initialize mappers when module is imported
start_mappers()
