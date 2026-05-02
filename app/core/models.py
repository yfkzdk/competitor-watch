"""Unified SQLAlchemy models for competitor-watch.

All tables and columns are aligned with the actual queries used in
app/services/ and src/ code. Schema version controlled via Alembic.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey, JSON,
    Index, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Competitor(Base):
    __tablename__ = "competitors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, unique=True)
    url = Column(String(500), nullable=False)
    category = Column(String(100), default="未分类")
    status = Column(String(50), default="active")
    priority = Column(String(20), default="medium")
    description = Column(Text, default="")
    type = Column(String(50), default="all")
    frequency = Column(String(20), default="15")
    market_share = Column(Float, default=0)
    price_index = Column(Float, default=90)
    user_rating = Column(Float, default=4.0)
    growth = Column(Float, default=0)
    feature_count = Column(Integer, default=0)
    innovation_velocity = Column(Float, default=0)
    security_mentions = Column(Integer, default=0)
    last_checked = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    monitoring_logs = relationship("MonitoringLog", back_populates="competitor", cascade="all, delete-orphan")
    changes = relationship("Change", back_populates="competitor", cascade="all, delete-orphan")
    analysis_reports = relationship("AnalysisReport", back_populates="competitor", cascade="all, delete-orphan")
    price_history = relationship("PriceHistory", back_populates="competitor", cascade="all, delete-orphan")
    user_reviews = relationship("UserReview", back_populates="competitor", cascade="all, delete-orphan")
    alert_rules = relationship("AlertRule", back_populates="competitor", cascade="all, delete-orphan")
    snapshots = relationship("MonitoringSnapshot", back_populates="competitor", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_competitors_name", "name"),
        Index("ix_competitors_category", "category"),
        Index("ix_competitors_status", "status"),
    )


class MonitoringLog(Base):
    __tablename__ = "monitoring_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), nullable=False, default="success")
    response_time = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    url = Column(String(500), nullable=True)
    content_hash = Column(String(64), nullable=True)
    content_length = Column(Integer, nullable=True)
    monitoring_type = Column(String(50), default="manual")
    details = Column(JSON, nullable=True)
    checked_at = Column(DateTime, default=datetime.utcnow)

    competitor = relationship("Competitor", back_populates="monitoring_logs")

    __table_args__ = (
        Index("ix_monitoring_logs_competitor_id", "competitor_id"),
        Index("ix_monitoring_logs_checked_at", "checked_at"),
    )


class Change(Base):
    __tablename__ = "changes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False)
    field_name = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    change_type = Column(String(50), default="content")
    severity = Column(String(20), default="info")
    detected_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)

    competitor = relationship("Competitor", back_populates="changes")

    __table_args__ = (
        Index("ix_changes_competitor_id", "competitor_id"),
        Index("ix_changes_detected_at", "detected_at"),
    )


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False)
    report_type = Column(String(50), nullable=False, default="comprehensive")
    title = Column(String(300), nullable=True)
    summary = Column(Text, nullable=True)
    content = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    confidence_score = Column(Float, nullable=True)
    model_used = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    competitor = relationship("Competitor", back_populates="analysis_reports")

    __table_args__ = (
        Index("ix_analysis_reports_competitor_id", "competitor_id"),
    )


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False)
    rule_name = Column(String(200), nullable=False)
    rule_type = Column(String(50), nullable=False, default="price_change")
    condition = Column(JSON, nullable=True)
    threshold = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    notification_method = Column(String(50), default="in_app")
    last_triggered = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    competitor = relationship("Competitor", back_populates="alert_rules")
    alert_history = relationship("AlertHistory", back_populates="alert_rule", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_alert_rules_competitor_id", "competitor_id"),
    )


class AlertHistory(Base):
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_rule_id = Column(Integer, ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False)
    competitor_id = Column(Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=True)
    message = Column(Text, nullable=True)
    severity = Column(String(20), default="warning")
    is_read = Column(Boolean, default=False)
    triggered_at = Column(DateTime, default=datetime.utcnow)

    alert_rule = relationship("AlertRule", back_populates="alert_history")

    __table_args__ = (
        Index("ix_alert_history_triggered_at", "triggered_at"),
    )


class MonitoringSnapshot(Base):
    __tablename__ = "monitoring_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False)
    snapshot_type = Column(String(50), nullable=False, default="full_page")
    content = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=True)
    url = Column(String(500), nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    captured_at = Column(DateTime, default=datetime.utcnow)

    competitor = relationship("Competitor", back_populates="snapshots")

    __table_args__ = (
        Index("ix_monitoring_snapshots_competitor_id", "competitor_id"),
    )


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False)
    product_name = Column(String(300), nullable=True)
    price = Column(Float, nullable=True)
    original_price = Column(Float, nullable=True)
    currency = Column(String(10), default="CNY")
    source = Column(String(100), nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    competitor = relationship("Competitor", back_populates="price_history")

    __table_args__ = (
        Index("ix_price_history_competitor_id", "competitor_id"),
    )


class UserReview(Base):
    __tablename__ = "user_reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String(100), nullable=True)
    author = Column(String(200), nullable=True)
    rating = Column(Float, nullable=True)
    content = Column(Text, nullable=True)
    sentiment_score = Column(Float, nullable=True)
    review_date = Column(DateTime, nullable=True)
    collected_at = Column(DateTime, default=datetime.utcnow)

    competitor = relationship("Competitor", back_populates="user_reviews")

    __table_args__ = (
        Index("ix_user_reviews_competitor_id", "competitor_id"),
    )


class ScraperConfig(Base):
    """采集规则配置 — matches scraper_service.py raw SQL schema."""
    __tablename__ = "scraper_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(200), nullable=False, unique=True)
    target_url = Column(String(500), nullable=True)
    scrape_type = Column(String(50), nullable=False, default="playwright")
    selectors = Column(JSON, nullable=True)
    headers = Column(JSON, nullable=True)
    wait_selector = Column(String(200), nullable=True)
    wait_timeout = Column(Integer, default=10000)
    use_stealth = Column(Boolean, default=True)
    frequency_minutes = Column(Integer, default=60)
    enabled = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)
    last_status = Column(String(50), nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScrapeResult(Base):
    """采集结果 — matches scraper_service.py _save_result schema."""
    __tablename__ = "scrape_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_id = Column(Integer, ForeignKey("scraper_configs.id", ondelete="SET NULL"), nullable=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id", ondelete="SET NULL"), nullable=True)
    extracted_data = Column(JSON, nullable=True)
    price = Column(Float, nullable=True)
    title = Column(String(500), nullable=True)
    in_stock = Column(Boolean, nullable=True)
    checksum = Column(String(64), nullable=True)
    scrape_duration_ms = Column(Integer, nullable=True)
    status = Column(String(50), default="success")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_scrape_results_competitor_id", "competitor_id"),
        Index("ix_scrape_results_config_id", "config_id"),
    )


class MonitoringSchedule(Base):
    __tablename__ = "monitoring_schedule"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False)
    schedule_type = Column(String(50), nullable=False, default="periodic")
    interval_minutes = Column(Integer, default=60)
    cron_expression = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    next_run = Column(DateTime, nullable=True)
    last_run = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
