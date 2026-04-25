import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

class Neo4jHandler:
    def __init__(self, uri, user, password):
        self.driver = None
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            # Test connection
            self.driver.verify_connectivity()
        except Exception as e:
            print(f"Neo4j Connection Error: {str(e)}. Graph features will be disabled.")
            self.driver = None 

    def close(self):
        if self.driver:
            self.driver.close()

    def create_persona_relationship(self, user_id, persona):
        if not self.driver: return
        try:
            with self.driver.session() as session:
                session.run("""
                    MERGE (u:User {id: $user_id})
                    MERGE (p:Persona {type: $persona})
                    MERGE (u)-[:HAS_PERSONA]->(p)
                """, user_id=user_id, persona=persona)
        except Exception as e:
            print(f"⚠️ Neo4j Session Error (Persona): {str(e)}")

    def create_interest_relationship(self, user_id, asset_type, asset_name):
        if not self.driver: return
        try:
            with self.driver.session() as session:
                session.run("""
                    MERGE (u:User {id: $user_id})
                    MERGE (a:Asset {type: $asset_type, name: $asset_name})
                    MERGE (u)-[:INTERESTED_IN]->(a)
                """, user_id=user_id, asset_type=asset_type, asset_name=asset_name)
        except Exception as e:
            print(f"⚠️ Neo4j Session Error (Interest): {str(e)}")

    def get_user_graph_context(self, user_id):
        """
        Retrieves graph context for GraphRAG:
        - User's previous interests
        - Interests of users with the same persona (Collaborative Filtering)
        - Transaction history and spending patterns for personality analysis
        """
        if not self.driver: return {"user_previous_interests": [], "community_suggestions": [], "transaction_patterns": []}
        
        try:
            with self.driver.session() as session:
                # 1. Get user's direct interests
                interests_result = session.run("""
                    MATCH (u:User {id: $user_id})-[:INTERESTED_IN]->(a:Asset)
                    return a.name as name, a.type as type
                """, user_id=user_id)
                user_interests = [{"name": r["name"], "type": r["type"]} for r in interests_result]

                # 2. Get collaborative recommendations (Graph traversal)
                collab_result = session.run("""
                    MATCH (u:User {id: $user_id})-[:HAS_PERSONA]->(p:Persona)<-[:HAS_PERSONA]-(other:User)
                    WHERE u <> other
                    MATCH (other)-[:INTERESTED_IN]->(suggested:Asset)
                    WHERE NOT (u)-[:INTERESTED_IN]->(suggested)
                    RETURN suggested.name as name, suggested.type as type, count(*) as weight
                    ORDER BY weight DESC LIMIT 5
                """, user_id=user_id)
                suggestions = [{"name": r["name"], "type": r["type"]} for r in collab_result]

                # 3. Get transaction patterns (GraphRAG for personality)
                patterns_result = session.run("""
                    MATCH (u:User {id: $user_id})-[:MADE_TRANSACTION]->(t:Transaction)-[:IN_CATEGORY]->(c:Category)
                    WITH c.name as category, count(t) as frequency, sum(t.amount) as total_spent
                    ORDER BY total_spent DESC
                    RETURN category, frequency, total_spent
                """, user_id=user_id)
                patterns = [{"category": r["category"], "frequency": r["frequency"], "total_spent": r["total_spent"]} for r in patterns_result]

                return {
                    "user_previous_interests": user_interests,
                    "community_suggestions": suggestions,
                    "transaction_patterns": patterns
                }
        except Exception as e:
            print(f"⚠️ Neo4j Retrieval Error: {str(e)}")
            return {"user_previous_interests": [], "community_suggestions": [], "transaction_patterns": []}

    def sync_user_from_mongodb(self, user_data):
        """
        Syncs user data from MongoDB to Neo4j after login/registration.
        Creates User node with properties from MongoDB and persona relationships.
        """
        if not self.driver:
            print("⚠️ Neo4j not connected, skipping sync")
            return
        
        try:
            user_id = user_data.get("user_id", "")
            name = user_data.get("name", "")
            persona = user_data.get("persona", "balanced")
            total_liquidity = user_data.get("total_liquidity", 0)
            monthly_budget = user_data.get("monthly_budget", 0)
            
            with self.driver.session() as session:
                # Create/Update User node with all MongoDB properties
                session.run("""
                    MERGE (u:User {id: $user_id})
                    SET u.name = $name,
                        u.persona = $persona,
                        u.total_liquidity = $total_liquidity,
                        u.monthly_budget = $monthly_budget,
                        u.last_sync = datetime()
                """, user_id=user_id, name=name, persona=persona,
                    total_liquidity=total_liquidity, monthly_budget=monthly_budget)
                
                # Create Persona relationship
                session.run("""
                    MERGE (u:User {id: $user_id})
                    MERGE (p:Persona {type: $persona})
                    MERGE (u)-[:HAS_PERSONA]->(p)
                """, user_id=user_id, persona=persona)
                
                print(f"✅ Synced user {user_id} to Neo4j (persona: {persona}, liquidity: ${total_liquidity:,})")
        except Exception as e:
            print(f"⚠️ Neo4j Sync Error: {str(e)}")
    
    def sync_transactions_to_neo4j(self, user_id, transactions):
        """
        Syncs transaction history from MongoDB to Neo4j graph.
        Creates transaction nodes and relationships.
        """
        if not self.driver:
            return
        
        try:
            with self.driver.session() as session:
                for txn in transactions:
                    txn_type = txn.get("type", "unknown")
                    amount = txn.get("amount", 0)
                    category = txn.get("category", "uncategorized")
                    
                    # Create transaction node and link to user
                    session.run("""
                        MATCH (u:User {id: $user_id})
                        MERGE (t:Transaction {id: $txn_id})
                        SET t.type = $txn_type,
                            t.amount = $amount,
                            t.category = $category,
                            t.date = $date
                        MERGE (u)-[:MADE_TRANSACTION]->(t)
                        
                        // Also create category node for pattern analysis
                        MERGE (c:Category {name: $category})
                        MERGE (t)-[:IN_CATEGORY]->(c)
                        MERGE (u)-[:SPENDS_ON]->(c)
                    """, user_id=user_id, txn_id=txn.get("_id", str(hash(str(txn)))),
                        txn_type=txn_type, amount=amount, category=category,
                        date=txn.get("date", "unknown"))
                
                print(f"✅ Synced {len(transactions)} transactions to Neo4j for {user_id}")
        except Exception as e:
            print(f"⚠️ Neo4j Transaction Sync Error: {str(e)}")

neo4j_handler = Neo4jHandler(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
