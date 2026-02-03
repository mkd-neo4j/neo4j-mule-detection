// Distance to Known Mule
// =====================
// Calculate the shortest path distance from a target account to the nearest
// confirmed mule account in the transaction network.
//
// Parameters:
//   $accountNumber - The account number to evaluate (null/empty = all accounts)
//
// Returns:
//   account         - The target account number
//   distanceToMule  - Number of hops to nearest mule (null if no path)
//   nearestMule     - Account number of the nearest confirmed mule
//   path            - The full path (for debugging/visualization)
//
// Notes:
//   - Mules are identified by the :Mule label
//   - Traverses PERFORMS and BENEFITS_TO relationships (transaction flow)
//   - Limited to 10 hops max
//   - Returns ALL paths tied for shortest length (Neo4j 5+ ALL SHORTEST syntax)

// Find all shortest paths to any mule account
// Uses Neo4j 5+ ALL SHORTEST syntax with quantified path pattern
// Pattern: Account -[:PERFORMS]-> Transaction -[:BENEFITS_TO]-> Account (repeated 1-10 times)
// If $accountNumber is null/empty, returns distances for ALL accounts
MATCH (target:Account)
WHERE CASE
        WHEN $accountNumber IS NOT NULL AND $accountNumber <> ''
        THEN target.accountNumber = $accountNumber
        ELSE true
      END
MATCH path = ALL SHORTEST (target)(()-[:PERFORMS]->(:Transaction)-[:BENEFITS_TO]->(:Account)){1,10}(mule:Mule)

RETURN
  target.accountNumber AS account,
  length(path) AS distanceToMule,
  mule.accountNumber AS nearestMule,
  [node IN nodes(path) |
    CASE
      WHEN node:Account THEN node.accountNumber
      WHEN node:Transaction THEN node.id
      ELSE elementId(node)
    END
  ] AS pathNodes
