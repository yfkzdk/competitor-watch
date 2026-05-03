"""Tests for data_pipeline.py — the core fetch → detect → persist → alert pipeline."""
import pytest
from app.services.data_pipeline import DataPipeline


class TestComputeChecksum:
    """Checksum computation — must be deterministic."""

    def test_same_input_produces_same_checksum(self):
        pipeline = DataPipeline()
        data = {"events": [{"type": "test", "title": "hello"}], "metrics": {"price_index": 90}}
        assert pipeline._compute_checksum(data) == pipeline._compute_checksum(data)

    def test_different_input_produces_different_checksum(self):
        pipeline = DataPipeline()
        a = {"events": [{"type": "test", "title": "hello"}]}
        b = {"events": [{"type": "test", "title": "world"}]}
        assert pipeline._compute_checksum(a) != pipeline._compute_checksum(b)

    def test_metrics_change_detected(self):
        pipeline = DataPipeline()
        a = {"events": [], "metrics": {"price_index": 90}}
        b = {"events": [], "metrics": {"price_index": 95}}
        assert pipeline._compute_checksum(a) != pipeline._compute_checksum(b)


class TestDetectChanges:
    """Change detection — checksum comparison logic."""

    def test_no_previous_checksum_no_content_change(self, db_session):
        """First run: no prior checksum in DB → no content_changed event."""
        pipeline = DataPipeline(db=db_session)
        fetch_result = {"events": [], "metrics": {}}
        new_checksum = pipeline._compute_checksum(fetch_result)

        changes = pipeline._detect_changes(1, new_checksum, fetch_result)
        content_changes = [c for c in changes if c["type"] == "content_changed"]
        assert len(content_changes) == 0

    def test_different_checksum_triggers_change(self, db_session):
        """Second run: new checksum differs from stored → content_changed."""
        pipeline = DataPipeline(db=db_session)
        # Simulate a previous run by persisting a checksum
        pipeline._persist_checksum(1, "abcdef1234567890")
        fetch_result = {"events": [], "metrics": {"price_index": 100}}

        new_checksum = pipeline._compute_checksum(fetch_result)
        changes = pipeline._detect_changes(1, new_checksum, fetch_result)
        content_changes = [c for c in changes if c["type"] == "content_changed"]
        assert len(content_changes) == 1
        assert content_changes[0]["old_checksum"] == "abcdef1234567890"

    def test_same_checksum_no_change(self, db_session):
        """Same checksum → no content_changed."""
        pipeline = DataPipeline(db=db_session)
        fetch_result = {"events": [], "metrics": {}}
        checksum = pipeline._compute_checksum(fetch_result)
        pipeline._persist_checksum(1, checksum)

        changes = pipeline._detect_changes(1, checksum, fetch_result)
        content_changes = [c for c in changes if c["type"] == "content_changed"]
        assert len(content_changes) == 0

    def test_price_events_detected(self, db_session):
        """Events with type=price_detected → price_change change."""
        pipeline = DataPipeline(db=db_session)
        fetch_result = {
            "events": [
                {"type": "price_detected", "title": "ECS g7", "data": {"price": 0.45}},
                {"type": "price_detected", "title": "RDS mysql", "data": {"price": 1.20}},
            ],
            "metrics": {},
        }
        checksum = pipeline._compute_checksum(fetch_result)
        changes = pipeline._detect_changes(1, checksum, fetch_result)

        price_changes = [c for c in changes if c["type"] == "price_change"]
        assert len(price_changes) == 1
        assert price_changes[0]["severity"] == "P1"
        assert len(price_changes[0]["prices"]) == 2


class TestPipelineRun:
    """End-to-end pipeline run with injected in-memory SQLite."""

    @pytest.fixture(autouse=True)
    def setup_competitor(self, db_session):
        """Ensure a competitor record exists for the pipeline to update."""
        from app.core.models import Competitor
        from datetime import datetime
        comp = Competitor(
            id=1, name="PipelineTest竞品", url="https://test-pipeline.com",
            status="monitoring", type="all", frequency="30",
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        db_session.add(comp)
        db_session.commit()

    def test_run_persists_events(self, db_session):
        """Events from fetch_result appear in monitoring_logs."""
        from app.core.models import MonitoringLog

        pipeline = DataPipeline(db=db_session)
        fetch_result = {
            "events": [
                {"type": "product_detected", "title": "TestProduct", "source": "https://example.com", "data": {"foo": "bar"}},
            ],
            "metrics": {"feature_count": 12},
        }
        result = pipeline.run(1, fetch_result)

        assert result["fetch_events"] == 1
        assert result["competitor_id"] == 1

        log = db_session.query(MonitoringLog).filter(MonitoringLog.competitor_id == 1).first()
        assert log is not None
        assert log.status == "success"
        assert log.monitoring_type == "pipeline"

    def test_run_persists_metrics(self, db_session):
        """Metrics from fetch_result update the competitor record."""
        from app.core.models import Competitor

        pipeline = DataPipeline(db=db_session)
        fetch_result = {
            "events": [],
            "metrics": {"feature_count": 99, "innovation_velocity": 77},
        }
        pipeline.run(1, fetch_result)

        comp = db_session.query(Competitor).filter(Competitor.id == 1).first()
        assert comp.feature_count == 99
        assert comp.innovation_velocity == 77

    def test_run_creates_snapshot(self, db_session):
        """Every run creates a monitoring_snapshot with a checksum."""
        from app.core.models import MonitoringSnapshot

        pipeline = DataPipeline(db=db_session)
        fetch_result = {"events": [{"type": "test", "title": "snap"}], "metrics": {}}
        pipeline.run(1, fetch_result)

        snap = db_session.query(MonitoringSnapshot).filter(
            MonitoringSnapshot.competitor_id == 1
        ).first()
        assert snap is not None
        assert len(snap.content_hash) == 32  # MD5 hex

    def test_run_empty_fetch_is_noop(self, db_session):
        """Empty fetch result doesn't crash."""
        pipeline = DataPipeline(db=db_session)
        result = pipeline.run(1, {"events": [], "metrics": {}})
        assert result["fetch_events"] == 0
        assert result["changes_detected"] == []
        assert result["alerts_triggered"] == 0
