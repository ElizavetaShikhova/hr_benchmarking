import unittest

from sqlalchemy.orm import Session

from backend.database import engine


class DatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        connection = engine.connect()
        transaction = connection.begin()
        self.session = Session(bind=connection, join_transaction_mode="create_savepoint")
        self.addCleanup(connection.close)
        self.addCleanup(transaction.rollback)
        self.addCleanup(self.session.close)
