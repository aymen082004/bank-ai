# neo4j_connection.py
from neo4j import GraphDatabase
import logging
import services.logger

logger = logging.getLogger(__name__)


class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

        # quick connectivity check (best-effort)
        try:
            if hasattr(self.driver, "verify_connectivity"):
                self.driver.verify_connectivity()
            else:
                with self.driver.session() as session:
                    session.run("RETURN 1").single()
            logger.info("Connected to Neo4j at %s", uri)
        except Exception as e:
            logger.exception("Neo4j connectivity test failed: %s", e)

    def close(self):
        try:
            self.driver.close()
        except Exception:
            logger.exception("Error closing Neo4j driver")