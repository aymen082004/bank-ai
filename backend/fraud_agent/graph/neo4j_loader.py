# graph/neo4j_loader.py

from graph.neo4j_connection import Neo4jConnection
import logging
import services.logger

logger = logging.getLogger(__name__)


class Neo4jLoader:

    def __init__(self, uri, user, password):
        self.conn = Neo4jConnection(uri, user, password)

    def create_indexes(self):
        queries = [
            "CREATE INDEX client_id IF NOT EXISTS FOR (c:Client) ON (c.id)",
            "CREATE INDEX account_id IF NOT EXISTS FOR (a:Account) ON (a.id)",
            "CREATE INDEX card_id IF NOT EXISTS FOR (c:Card) ON (c.id)",
            "CREATE INDEX merchant_name IF NOT EXISTS FOR (m:Merchant) ON (m.name)"
        ]

        with self.conn.driver.session() as session:
            for q in queries:
                session.run(q)

        logger.info("Indexes created")

    def create_transactions_batch(self, txs):

        query = """
        UNWIND $txs AS tx

        MERGE (c:Client {id: tx.client})
        MERGE (acc:Account {id: tx.account})
        MERGE (m:Merchant {name: tx.merchant})

        MERGE (c)-[:OWNS]->(acc)

        // Create transaction
        CREATE (t:Transaction {
            amount: tx.amount,
            date: tx.date,
            source: tx.source
        })

        MERGE (acc)-[:PERFORMS]->(t)
        MERGE (t)-[:TO]->(m)

        // Only create card if exists
        FOREACH (_ IN CASE WHEN tx.card <> 'NO_CARD' THEN [1] ELSE [] END |
            MERGE (card:Card {id: tx.card})
            MERGE (acc)-[:HAS_CARD]->(card)
        )
        """

        with self.conn.driver.session() as session:
            session.run(query, txs=txs)