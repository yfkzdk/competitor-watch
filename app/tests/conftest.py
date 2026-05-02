import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.models import Base
from app.core.database import SessionLocal
from app.services.competitor_service import CompetitorService
from app.services.alert_service import AlertService
from datetime import datetime


@pytest.fixture(scope="function")
def db_session():
    """In-memory SQLite session with schema created per test."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def competitor_service(db_session: Session):
    return CompetitorService(db=db_session)


@pytest.fixture
def alert_service(db_session: Session):
    return AlertService(db=db_session)


@pytest.fixture
def seeded_db(db_session: Session):
    """Session with one competitor pre-inserted."""
    from app.core.models import Competitor
    comp = Competitor(
        name="测试竞品",
        url="https://test.com",
        status="active",
        type="saas",
        frequency="15",
        market_share=15.5,
        price_index=85.0,
        user_rating=4.2,
        growth=12.0,
        innovation_velocity=65.0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(comp)
    db_session.commit()
    db_session.refresh(comp)
    return db_session, comp
