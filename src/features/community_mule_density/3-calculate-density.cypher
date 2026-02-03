// Community Mule Density - Step 3: Calculate Density
// ===================================================
// Calculate mule density for each community and WRITE back to nodes.
// This enables fast property lookups at query time.
//
// Prerequisites:
//   - Run 1-project-graph.cypher first
//   - Run 2-detect-communities.cypher first (communityId must exist on nodes)
//
// Writes:
//   muleDensity   - Ratio of mules in the community (0.0 - 1.0)
//   communitySize - Total Account + Mule nodes in the community
//   muleCount     - Number of Mule nodes in the community
//
// Returns:
//   Summary of each community's density (for verification)
//
// Notes:
//   - Only processes Account and Mule nodes (ignores Transaction nodes)
//   - Higher density indicates more suspicious community
//   - A density of 0.5 means half the accounts are confirmed mules

MATCH (n)
WHERE (n:Account OR n:Mule) AND n.communityId IS NOT NULL
WITH n.communityId AS communityId, collect(n) AS members
WITH communityId,
     members,
     size(members) AS communitySize,
     size([m IN members WHERE m:Mule]) AS muleCount
WITH communityId, members, communitySize, muleCount,
     round(toFloat(muleCount) / communitySize, 4) AS muleDensity
UNWIND members AS member
SET member.muleDensity = muleDensity,
    member.communitySize = communitySize,
    member.muleCount = muleCount
WITH DISTINCT communityId, communitySize, muleCount, muleDensity
RETURN communityId, communitySize, muleCount, muleDensity
ORDER BY muleDensity DESC
