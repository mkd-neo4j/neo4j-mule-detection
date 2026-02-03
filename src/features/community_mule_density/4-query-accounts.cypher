// Community Mule Density - Step 4: Query Accounts
// ================================================
// Fast property lookup for transaction evaluation.
// Returns community density for BOTH source and target accounts.
//
// Parameters:
//   $sourceAccount - The account initiating the transaction
//   $targetAccount - The account receiving the transaction
//
// Example (run in Neo4j Browser):
//   :param sourceAccount => 'ACC_CUST_835'
//   :param targetAccount => 'ACC_CUST_8'
//
//   Actual density values depend on community detection results.
//
// Prerequisites:
//   - Batch process must have run (steps 1-3) to populate properties
//
// Returns:
//   sourceAccount       - The source account number
//   sourceCommunityId   - Source's community identifier
//   sourceMuleDensity   - Mule density in source's community (0.0 = clean)
//   targetAccount       - The target account number
//   targetCommunityId   - Target's community identifier
//   targetMuleDensity   - Mule density in target's community (1.0 = 100% mule)
//
// Notes:
//   - Simple property lookup - no GDS or aggregation needed
//   - Use in real-time transaction evaluation
//   - Flag if EITHER account exceeds density threshold (e.g., > 0.2)
//   - Returns null for properties if account not found or not processed

MATCH (source)
WHERE (source:Account OR source:Mule) AND source.accountNumber = $sourceAccount
MATCH (target)
WHERE (target:Account OR target:Mule) AND target.accountNumber = $targetAccount
RETURN
  source.accountNumber AS sourceAccount,
  source.communityId AS sourceCommunityId,
  source.communitySize AS sourceCommunitySize,
  source.muleCount AS sourceMuleCount,
  source.muleDensity AS sourceMuleDensity,
  target.accountNumber AS targetAccount,
  target.communityId AS targetCommunityId,
  target.communitySize AS targetCommunitySize,
  target.muleCount AS targetMuleCount,
  target.muleDensity AS targetMuleDensity
