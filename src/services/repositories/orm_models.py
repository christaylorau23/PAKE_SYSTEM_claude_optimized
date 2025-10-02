#!/usr/bin/env python3
"""PAKE System - ORM Models (Phase 2 Architectural Refactoring)
SQLAlchemy ORM models using classical mapping to decouple from domain models.
"""

from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean, Float, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class UserORM(Base):
    """SQLAlchemy ORM model for User"""
    __tablename__ = 'users'
    
    id = Column(String, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    tenant_id = Column(String(255), nullable=False)
    
    first_name = Column(String(100))
    last_name = Column(String(100))
    role = Column(String(50), default='user')
    status = Column(String(50), default='active')
    
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    last_login_at = Column(DateTime)
    
    metadata = Column(JSON)


class ContentORM(Base):
    """SQLAlchemy ORM model for Content"""
    __tablename__ = 'content_items'
    
    id = Column(String, primary_key=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String(50), nullable=False)
    source = Column(String(50), nullable=False)
    tenant_id = Column(String(255), nullable=False)
    
    processing_status = Column(String(50), default='pending')
    processing_metadata = Column(JSON)
    
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    processed_at = Column(DateTime)
    
    tags = Column(JSON)
    metadata = Column(JSON)
    
    source_url = Column(String(1000))
    source_id = Column(String(255))


class SearchHistoryORM(Base):
    """SQLAlchemy ORM model for Search History"""
    __tablename__ = 'search_history'
    
    id = Column(String, primary_key=True)
    user_id = Column(String(255), nullable=False)
    tenant_id = Column(String(255), nullable=False)
    query = Column(Text, nullable=False)
    
    results_count = Column(Integer, default=0)
    search_filters = Column(JSON)
    
    created_at = Column(DateTime, nullable=False)
    response_time_ms = Column(Float)


class SavedSearchORM(Base):
    """SQLAlchemy ORM model for Saved Search"""
    __tablename__ = 'saved_searches'
    
    id = Column(String, primary_key=True)
    user_id = Column(String(255), nullable=False)
    tenant_id = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    query = Column(Text, nullable=False)
    
    search_filters = Column(JSON)
    is_public = Column(Boolean, default=False)
    
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    last_run_at = Column(DateTime)
    
    run_count = Column(Integer, default=0)


class TenantORM(Base):
    """SQLAlchemy ORM model for Tenant"""
    __tablename__ = 'tenants'
    
    id = Column(String, primary_key=True)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=False)
    
    plan = Column(String(50), default='basic')
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    
    max_users = Column(Integer, default=10)
    max_content_items = Column(Integer, default=1000)
    max_storage_mb = Column(Integer, default=1000)
    
    settings = Column(JSON)


class SystemMetricsORM(Base):
    """SQLAlchemy ORM model for System Metrics"""
    __tablename__ = 'system_metrics'
    
    id = Column(String, primary_key=True)
    metric_name = Column(String(255), nullable=False)
    metric_value = Column(Float, nullable=False)
    tenant_id = Column(String(255))
    
    metric_type = Column(String(50), default='counter')
    tags = Column(JSON)
    
    recorded_at = Column(DateTime, nullable=False)


class TenantActivityORM(Base):
    """SQLAlchemy ORM model for Tenant Activity"""
    __tablename__ = 'tenant_activities'
    
    id = Column(String, primary_key=True)
    tenant_id = Column(String(255), nullable=False)
    user_id = Column(String(255))
    activity_type = Column(String(100), nullable=False)
    activity_description = Column(Text, nullable=False)
    
    metadata = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    created_at = Column(DateTime, nullable=False)


class TenantResourceUsageORM(Base):
    """SQLAlchemy ORM model for Tenant Resource Usage"""
    __tablename__ = 'tenant_resource_usage'
    
    id = Column(String, primary_key=True)
    tenant_id = Column(String(255), nullable=False)
    
    users_count = Column(Integer, default=0)
    content_items_count = Column(Integer, default=0)
    storage_used_mb = Column(Float, default=0.0)
    api_calls_count = Column(Integer, default=0)
    
    recorded_at = Column(DateTime, nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
