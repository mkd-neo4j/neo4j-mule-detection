// Community Mule Density - Step 2: Detect Communities
// ====================================================
// Run Louvain community detection and WRITE communityId back to nodes.
// This persists the community assignment for efficient real-time queries.
//
// Prerequisites:
//   - Run 1-project-graph.cypher first
//
// Writes:
//   communityId - Written to all Account and Mule nodes in the projection
//
// Returns:
//   communityCount         - Number of communities detected
//   nodePropertiesWritten  - Number of nodes updated
//
// Notes:
//   - Uses gds.louvain.write (not stream) for efficiency
//   - Transaction nodes also get communityId but we filter in later queries
//   - Run this as part of batch processing, not real-time

CALL gds.louvain.write('community-detection-graph', {
  writeProperty: 'communityId'
})
YIELD communityCount, nodePropertiesWritten
RETURN communityCount, nodePropertiesWritten
