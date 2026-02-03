// Community Mule Density - Step 5: Cleanup
// =========================================
// Drop the GDS graph projection to free memory.
//
// Notes:
//   - Always run this after you're done with community detection
//   - GDS projections consume heap memory until dropped
//   - Safe to run even if projection doesn't exist (will just return false)

CALL gds.graph.drop('community-detection-graph', false)
YIELD graphName
RETURN graphName AS droppedGraph
