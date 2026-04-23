# graph/graph_queries.py

from graph.neo4j_connection import Neo4jConnection


class GraphAnalyzer:

    def __init__(self, uri, user, password):
        self.conn = Neo4jConnection(uri, user, password)

    # -------------------------
    # 1. LINKED CLIENTS (via shared account or card)
    # -------------------------
    def find_linked_clients(self, client_id):

        query = """
        MATCH (c:Client {id: $client})-[:OWNS]->(acc)<-[:OWNS]-(other:Client)
        WHERE other.id <> $client
        RETURN DISTINCT other.id AS client
        LIMIT 10
        """

        with self.conn.driver.session() as session:
            result = session.run(query, client=client_id)
            return [r["client"] for r in result]

    # -------------------------
    # 2. SHARED MERCHANT NETWORK
    # -------------------------
    def shared_merchants(self, client_id):

        query = """
        MATCH (c:Client {id: $client})-[:OWNS]->(:Account)-[:PERFORMS]->(t)-[:TO]->(m)<-[:TO]-(t2)<-[:PERFORMS]-(:Account)<-[:OWNS]-(other)
        WHERE other.id <> $client
        RETURN count(DISTINCT other) AS users
        """

        with self.conn.driver.session() as session:
            result = session.run(query, client=client_id)
            record = result.single()
            return record["users"] if record else 0

    # -------------------------
    # 3. TRANSACTION BURST (VERY IMPORTANT)
    # -------------------------
    def transaction_peak(self, client_id):

        query = """
        MATCH (c:Client {id: $client})-[:OWNS]->(:Account)-[:PERFORMS]->(t)
        WITH date(t.date) AS d, count(t) AS tx_count
        RETURN max(tx_count) AS peak
        """

        with self.conn.driver.session() as session:
            result = session.run(query, client=client_id)
            record = result.single()
            return record["peak"] if record else 0

    # -------------------------
    # 4. CARD COUNT
    # -------------------------
    def count_cards(self, client_id):

        query = """
        MATCH (c:Client {id: $client})-[:OWNS]->(:Account)-[:HAS_CARD]->(card)
        RETURN count(DISTINCT card) AS cards
        """

        with self.conn.driver.session() as session:
            result = session.run(query, client=client_id)
            record = result.single()
            return record["cards"] if record else 0

    # -------------------------
    # 5. MERCHANT COUNT
    # -------------------------
    def count_merchants(self, client_id):

        query = """
        MATCH (c:Client {id: $client})-[:OWNS]->(:Account)-[:PERFORMS]->(t)-[:TO]->(m)
        RETURN count(DISTINCT m) AS merchants
        """

        with self.conn.driver.session() as session:
            result = session.run(query, client=client_id)
            record = result.single()
            return record["merchants"] if record else 0

    # -------------------------
    # 6. FULL SUBGRAPH (for visualization)
    # -------------------------
    def get_client_subgraph(self, client_id):

        query = """
        MATCH (c:Client {id: $client})-[:OWNS]->(acc)
        OPTIONAL MATCH (acc)-[:HAS_CARD]->(card)
        OPTIONAL MATCH (acc)-[:PERFORMS]->(t)-[:TO]->(m)

        RETURN c, acc, card, t, m
        LIMIT 50
        """

        with self.conn.driver.session() as session:
            result = session.run(query, client=client_id)

            nodes_map = {}
            edges_map = {}

            def node_id_for(node, fallback_key=None):
                if not node:
                    return None
                try:
                    # node might be a mapping-like or a neo4j Node
                    if hasattr(node, 'get'):
                        if 'id' in node:
                            return str(node['id'])
                        if fallback_key and fallback_key in node:
                            return str(node[fallback_key])
                    # neo4j Node exposes .id attribute (internal id)
                    return str(node.id)
                except Exception:
                    try:
                        return str(dict(node))
                    except Exception:
                        return str(node)

            def extract_label_and_title(node, default_label):
                # Safely extract properties from the node to build a friendly label and tooltip
                props = {}
                try:
                    props = dict(node)
                except Exception:
                    try:
                        props = {k: node.get(k) for k in getattr(node, 'keys', lambda: [])()}
                    except Exception:
                        props = {}

                # prefer human-readable properties for labels
                display_value = None
                for k in ('name', 'id', 'number', 'card_number', 'masked_pan', 'pan', 'label', 'last4'):
                    if props.get(k):
                        display_value = props.get(k)
                        break

                if display_value:
                    label = f"{default_label}: {display_value}"
                else:
                    label = default_label

                # build a compact HTML title showing a few properties
                title_items = []
                for i, (k, v) in enumerate(props.items()):
                    if i >= 8:
                        break
                    title_items.append(f"{k}: {v}")
                title = "<b>" + label + "</b><br/>" + "<br/>".join(title_items)
                return label, title, props

            def add_node(node, label, fallback_key=None):
                nid = node_id_for(node, fallback_key=fallback_key)
                if not node or not nid:
                    return
                if nid in nodes_map:
                    return
                lbl, title, props = extract_label_and_title(node, label)
                nodes_map[nid] = {
                    "id": nid,
                    "label": lbl,
                    "type": label,
                    "title": title,
                    "props": props,
                }

            for r in result:

                c = r.get("c")
                acc = r.get("acc")
                card = r.get("card")
                t = r.get("t")
                m = r.get("m")

                add_node(c, "Client", fallback_key='id')
                add_node(acc, "Account", fallback_key='id')

                if card:
                    add_node(card, "Card", fallback_key='id')

                if m:
                    # merchant nodes sometimes use 'name' as primary identifier
                    add_node(m, "Merchant", fallback_key='name')

                # edges (use node_id_for to get consistent ids)
                c_id = node_id_for(c, fallback_key='id')
                acc_id = node_id_for(acc, fallback_key='id')
                if c_id and acc_id:
                    key = (c_id, acc_id, "OWNS")
                    edges_map[key] = edges_map.get(key, 0) + 1

                if card:
                    card_id = node_id_for(card, fallback_key='id')
                    if acc_id and card_id:
                        key = (acc_id, card_id, "HAS_CARD")
                        edges_map[key] = edges_map.get(key, 0) + 1

                if m:
                    m_id = node_id_for(m, fallback_key='name')
                    if acc_id and m_id:
                        key = (acc_id, m_id, "TRANSACTS")
                        edges_map[key] = edges_map.get(key, 0) + 1

            # build deduplicated edges list with counts
            edges = []
            for (s, t, lbl), cnt in edges_map.items():
                edges.append({"source": s, "target": t, "label": lbl, "count": cnt})

            # return nodes as a list preserving richer metadata for visualization
            return {"nodes": list(nodes_map.values()), "edges": edges}