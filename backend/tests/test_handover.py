import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from starlette.testclient import TestClient
from app.database import SessionLocal, migrate_schema
from app.main import app
from app.models import (
    BorrowRequest, BorrowRequestStatus, Conversation, HandoverStatus, Listing,
    ListingStatus, Message, NegotiationOffer, Notification, OfferStatus, User,
)
from app.services.auth import create_access_token


class TestHandover(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()
        suffix = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        cls.lender = User(
            name="Handover Lender", username=f"handover_lender_{suffix}",
            email=f"handover_lender_{suffix}@test.com", password_hash="test",
        )
        cls.borrower = User(
            name="Handover Borrower", username=f"handover_borrower_{suffix}",
            email=f"handover_borrower_{suffix}@test.com", password_hash="test",
        )
        cls.intruder = User(
            name="Handover Intruder", username=f"handover_intruder_{suffix}",
            email=f"handover_intruder_{suffix}@test.com", password_hash="test",
        )
        cls.db.add_all([cls.lender, cls.borrower, cls.intruder])
        cls.db.flush()
        cls.listing = Listing(
            owner_id=cls.lender.id, name="Handover Test Item", category="Tools",
            description="Test item", price_per_day=20, status=ListingStatus.published,
        )
        cls.db.add(cls.listing)
        cls.db.flush()
        cls.headers = {
            role: {"Authorization": f"Bearer {create_access_token(user.id)}"}
            for role, user in (
                ("lender", cls.lender), ("borrower", cls.borrower), ("intruder", cls.intruder)
            )
        }
        cls.request_id = cls._make_rental("main")
        cls.issue_request_id = cls._make_rental("issue")
        cls.db.commit()

    @classmethod
    def _make_rental(cls, label):
        now = datetime.utcnow()
        start = now + timedelta(days=30)
        end = start + timedelta(days=3)
        conversation = Conversation(borrower_id=cls.borrower.id, lender_id=cls.lender.id)
        cls.db.add(conversation)
        cls.db.flush()
        request = BorrowRequest(
            borrower_id=cls.borrower.id,
            listing_id=cls.listing.id,
            title=f"Rental: {label}",
            category=cls.listing.category,
            description="Agreed rental for handover test",
            max_price_per_day=20,
            needed_from=start,
            needed_until=end,
            total_cost=60,
            status=BorrowRequestStatus.open,
            handover_status=HandoverStatus.pending.value,
        )
        cls.db.add(request)
        cls.db.flush()
        offer = NegotiationOffer(
            conversation_id=conversation.id,
            listing_id=cls.listing.id,
            sender_id=cls.borrower.id,
            daily_price=20,
            start_date=start,
            end_date=end,
            total_cost=60,
            status=OfferStatus.accepted,
            borrow_request_id=request.id,
        )
        cls.db.add(offer)
        cls.db.flush()
        return request.id

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_get_handover_is_private_to_participants(self):
        response = self.client.get(
            f"/api/borrow-requests/{self.request_id}/handover",
            headers=self.headers["borrower"],
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["handover_status"], "pending")
        self.assertTrue(response.json()["conversation_id"])
        forbidden = self.client.get(
            f"/api/borrow-requests/{self.request_id}/handover",
            headers=self.headers["intruder"],
        )
        self.assertEqual(forbidden.status_code, 403)

    def test_handover_confirmation_and_authorization(self):
        request_url = f"/api/borrow-requests/{self.request_id}/handover"
        mark_url = f"{request_url}/mark-given"
        confirm_url = f"{request_url}/confirm"

        self.assertEqual(self.client.post(mark_url, headers=self.headers["intruder"]).status_code, 403)
        self.assertEqual(self.client.post(mark_url, headers=self.headers["borrower"]).status_code, 403)
        self.assertEqual(self.client.post(confirm_url, headers=self.headers["borrower"]).status_code, 409)

        marked = self.client.post(mark_url, headers=self.headers["lender"])
        self.assertEqual(marked.status_code, 200)
        self.assertEqual(marked.json()["handover_status"], "marked_given")
        self.assertEqual(self.client.post(mark_url, headers=self.headers["lender"]).status_code, 409)

        self.assertEqual(self.client.post(confirm_url, headers=self.headers["lender"]).status_code, 403)
        confirmed = self.client.post(confirm_url, headers=self.headers["borrower"])
        self.assertEqual(confirmed.status_code, 200)
        body = confirmed.json()
        self.assertEqual(body["handover_status"], "confirmed")
        self.assertEqual(body["status"], "fulfilled")
        self.assertEqual(body["handover_confirmed_by"], self.borrower.id)
        started_at = datetime.fromisoformat(body["borrowing_started_at"])
        due_at = datetime.fromisoformat(body["return_due_at"])
        self.assertEqual(due_at - started_at, timedelta(days=3))
        self.assertEqual(self.client.post(confirm_url, headers=self.headers["borrower"]).status_code, 409)

        self.db.expire_all()
        request = self.db.query(BorrowRequest).filter_by(id=self.request_id).one()
        self.assertEqual(request.handover_status, "confirmed")
        self.assertEqual(request.status, BorrowRequestStatus.fulfilled)
        self.assertEqual(
            self.db.query(Notification).filter_by(
                borrow_request_id=self.request_id, notification_type="handover_marked"
            ).count(),
            1,
        )
        marked_notification = self.db.query(Notification).filter_by(
            borrow_request_id=self.request_id, notification_type="handover_marked"
        ).one()
        self.assertEqual(marked_notification.user_id, self.borrower.id)
        self.assertEqual(
            self.db.query(Notification).filter_by(
                borrow_request_id=self.request_id, notification_type="handover_confirmed"
            ).count(),
            1,
        )
        confirmation_notification = self.db.query(Notification).filter_by(
            borrow_request_id=self.request_id, notification_type="handover_confirmed"
        ).one()
        self.assertEqual(confirmation_notification.user_id, self.lender.id)
        self.assertGreaterEqual(
            self.db.query(Message).filter_by(is_system=True).count(), 2
        )

    def test_issue_report_does_not_activate_rental(self):
        request_url = f"/api/borrow-requests/{self.issue_request_id}/handover"
        mark_url = f"{request_url}/mark-given"
        issue_url = f"{request_url}/report-issue"
        self.assertEqual(self.client.post(mark_url, headers=self.headers["lender"]).status_code, 200)
        self.assertEqual(
            self.client.post(issue_url, json={"description": "  "}, headers=self.headers["borrower"]).status_code,
            422,
        )
        self.assertEqual(
            self.client.post(issue_url, json={"description": "Issue"}, headers=self.headers["lender"]).status_code,
            403,
        )
        reported = self.client.post(
            issue_url,
            json={"description": "The casing is cracked."},
            headers=self.headers["borrower"],
        )
        self.assertEqual(reported.status_code, 200)
        self.assertEqual(reported.json()["handover_status"], "issue_reported")
        self.assertEqual(reported.json()["status"], "open")
        self.assertIsNone(reported.json()["borrowing_started_at"])
        self.assertEqual(reported.json()["handover_issue_description"], "The casing is cracked.")
        self.assertEqual(self.client.post(issue_url, json={"description": "Again"}, headers=self.headers["borrower"]).status_code, 409)

        self.db.expire_all()
        request = self.db.query(BorrowRequest).filter_by(id=self.issue_request_id).one()
        self.assertEqual(request.status, BorrowRequestStatus.open)
        self.assertIsNone(request.borrowing_started_at)
        self.assertEqual(
            self.db.query(Notification).filter_by(
                borrow_request_id=self.issue_request_id,
                notification_type="handover_issue_reported",
            ).count(),
            1,
        )


class TestHandoverSchemaMigration(unittest.TestCase):
    def test_existing_borrow_requests_receive_additive_handover_columns(self):
        database_path = Path(tempfile.gettempdir()) / f"neighborlend-legacy-{os.getpid()}.db"
        database_path.unlink(missing_ok=True)
        engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            with engine.begin() as connection:
                connection.execute(text(
                    "CREATE TABLE borrow_requests (id VARCHAR PRIMARY KEY, title VARCHAR NOT NULL)"
                ))
                connection.execute(text(
                    "INSERT INTO borrow_requests (id, title) VALUES ('legacy-id', 'Old request')"
                ))
            migrate_schema(engine)
            columns = {column["name"] for column in inspect(engine).get_columns("borrow_requests")}
            self.assertTrue({
                "handover_status", "handover_marked_at", "handover_confirmed_at",
                "handover_confirmed_by", "handover_issue_description",
                "handover_issue_reported_at", "borrowing_started_at", "return_due_at",
            }.issubset(columns))
            with engine.connect() as connection:
                row = connection.execute(text(
                    "SELECT title, handover_status FROM borrow_requests WHERE id = 'legacy-id'"
                )).one()
            self.assertEqual(row.title, "Old request")
            self.assertEqual(row.handover_status, "not_applicable")
        finally:
            engine.dispose()
            database_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
