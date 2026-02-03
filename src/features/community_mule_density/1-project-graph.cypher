// Community Mule Density - Step 1: Project Graph
// ================================================
// Create a GDS graph projection using CYPHER PROJECTION.
// This creates VIRTUAL weighted relationships between accounts based on
// their direct transaction activity WITHOUT persisting anything to the database.
//
// Virtual Relationship Logic:
//   Account A --PERFORMS--> Transaction --BENEFITS_TO--> Account B
//   Creates: Account A --[TRANSACTED_WITH {weight: totalAmount}]--> Account B
//
// Weighting:
//   Relationships are weighted by total transaction amount (sum of all
//   transactions between the two accounts). This means:
//   - £1M single transaction = strong connection
//   - 100 x 1p transactions = weak connection
//
// Prerequisites:
//   - Neo4j GDS library installed
//   - Transaction data loaded with amount property
//
// Notes:
//   - Uses gds.graph.project.cypher (Cypher projection)
//   - No data is written to the database
//   - Virtual relationships exist only in the GDS projection
//   - Only Account-to-Account/Mule transactions are included
//   - Merchants and Banks are excluded (they would dominate communities)

CALL gds.graph.project.cypher(
  'community-detection-graph',
  // Node query: all Account and Mule nodes
  'MATCH (n) WHERE n:Account OR n:Mule RETURN id(n) AS id, labels(n) AS labels',
  // Relationship query: direct account-to-account transactions weighted by amount
  'MATCH (a1)-[:PERFORMS]->(t:Transaction)-[:BENEFITS_TO]->(a2)
   WHERE (a1:Account OR a1:Mule) AND (a2:Account OR a2:Mule) AND a1 <> a2
   WITH a1, a2, sum(t.amount) AS totalAmount
   RETURN id(a1) AS source, id(a2) AS target, totalAmount AS weight',
  { validateRelationships: false }
)
YIELD graphName, nodeCount, relationshipCount
RETURN graphName, nodeCount, relationshipCount
