"""
Feature: Community Mule Density
Description: Detect communities using Louvain and calculate the ratio of
             confirmed mules within each community. Pre-computes density
             for fast real-time transaction evaluation.
"""

# ============================================================================
#  CONFIGURATION - Set parameters for this feature here
# ============================================================================


def get_conf() -> dict:
    """
    Configuration parameters for the Cypher queries.

    Returns:
        dict with keys:
        - sourceAccount: The account initiating a transaction
        - targetAccount: The account receiving a transaction

    Example accounts for testing. Actual density values depend on
    community detection results which may vary between runs.
    """
    return {
        "sourceAccount": "ACC_CUST_835",
        "targetAccount": "ACC_CUST_8",
    }


# ============================================================================

import logging
import warnings
from pathlib import Path

from neo4j import GraphDatabase

# Suppress Neo4j driver notifications (schema warnings, deprecations)
logging.getLogger("neo4j").setLevel(logging.ERROR)
logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="neo4j")

# Graph projection name used across all queries
GRAPH_NAME = "community-detection-graph"


def load_query(filename: str) -> str:
    """Load a Cypher query from a file in this directory."""
    cypher_file = Path(__file__).parent / filename
    return cypher_file.read_text()


def project_graph(driver: GraphDatabase.driver, database: str | None = None) -> dict:
    """
    Step 1: Create the GDS graph projection.

    Args:
        driver: Neo4j driver instance
        database: Neo4j database name (None for default)

    Returns:
        dict with graphName, nodeCount, relationshipCount
    """
    query = load_query("1-project-graph.cypher")

    with driver.session(database=database) as session:
        result = session.run(query)
        record = result.single()
        return record.data() if record else {}


def detect_communities(
    driver: GraphDatabase.driver, database: str | None = None
) -> dict:
    """
    Step 2: Run Louvain community detection and WRITE communityId to nodes.

    Args:
        driver: Neo4j driver instance
        database: Neo4j database name (None for default)

    Returns:
        dict with communityCount, nodePropertiesWritten
    """
    query = load_query("2-detect-communities.cypher")

    with driver.session(database=database) as session:
        result = session.run(query)
        record = result.single()
        return record.data() if record else {}


def calculate_density(
    driver: GraphDatabase.driver, database: str | None = None
) -> list[dict]:
    """
    Step 3: Calculate mule density and WRITE to nodes.

    Args:
        driver: Neo4j driver instance
        database: Neo4j database name (None for default)

    Returns:
        List of dicts with communityId, communitySize, muleCount, muleDensity
        (summary of what was written)
    """
    query = load_query("3-calculate-density.cypher")

    with driver.session(database=database) as session:
        result = session.run(query)
        return [record.data() for record in result]


def query_accounts(
    driver: GraphDatabase.driver, database: str | None = None, **params
) -> dict | None:
    """
    Step 4: Query community density for source and target accounts.

    This is the REAL-TIME query for transaction evaluation.
    Requires batch processing (steps 1-3) to have run first.

    Args:
        driver: Neo4j driver instance
        database: Neo4j database name (None for default)
        **params: Query parameters
            - sourceAccount (str): The account initiating the transaction
            - targetAccount (str): The account receiving the transaction

    Returns:
        dict with source and target account community info, or None if not found
    """
    query = load_query("4-query-accounts.cypher")

    with driver.session(database=database) as session:
        result = session.run(query, **params)
        record = result.single()
        return record.data() if record else None


def cleanup(driver: GraphDatabase.driver, database: str | None = None) -> dict:
    """
    Step 5: Drop the GDS graph projection.

    Args:
        driver: Neo4j driver instance
        database: Neo4j database name (None for default)

    Returns:
        dict with droppedGraph name
    """
    query = load_query("5-cleanup.cypher")

    with driver.session(database=database) as session:
        result = session.run(query)
        record = result.single()
        return record.data() if record else {}


def run_batch(driver: GraphDatabase.driver, database: str | None = None) -> list[dict]:
    """
    Run the BATCH processing workflow to pre-compute community densities.

    Execute this periodically (e.g., daily) to update community assignments
    and density calculations. After this runs, query_accounts() can be
    called for fast real-time lookups.

    Steps:
    1. Project the graph
    2. Detect communities (write communityId to nodes)
    3. Calculate density (write muleDensity to nodes)
    4. Cleanup projection

    Args:
        driver: Neo4j driver instance
        database: Neo4j database name (None for default)

    Returns:
        List of community summaries (communityId, size, muleCount, density)
    """
    try:
        # Step 1: Project graph
        projection = project_graph(driver, database=database)
        print(f"Projected graph: {projection.get('nodeCount', 0)} nodes, "
              f"{projection.get('relationshipCount', 0)} relationships")

        # Step 2: Detect communities
        communities = detect_communities(driver, database=database)
        print(f"Detected {communities.get('communityCount', 0)} communities, "
              f"wrote to {communities.get('nodePropertiesWritten', 0)} nodes")

        # Step 3: Calculate and write density
        densities = calculate_density(driver, database=database)
        print(f"Calculated density for {len(densities)} communities")

        return densities

    finally:
        # Step 5: Always cleanup
        cleanup(driver, database=database)


def run(
    driver: GraphDatabase.driver, database: str | None = None, **params
) -> dict | None:
    """
    REAL-TIME query for transaction evaluation.

    Returns community density for both source and target accounts.
    Requires run_batch() to have been executed first.

    Args:
        driver: Neo4j driver instance
        database: Neo4j database name (None for default)
        **params: Query parameters
            - sourceAccount (str): The account initiating the transaction
            - targetAccount (str): The account receiving the transaction

    Returns:
        dict with source and target account community info

    Example:
        >>> result = run(driver, sourceAccount="ACC123", targetAccount="ACC456")
        >>> if result:
        ...     if result['sourceMuleDensity'] > 0.2 or result['targetMuleDensity'] > 0.2:
        ...         print("HIGH RISK: Account in suspicious community")
    """
    return query_accounts(driver, database=database, **params)


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    # Load .env file from project root
    load_dotenv()

    # Configure via environment variables
    uri = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    database = os.getenv("NEO4J_DATABASE") or None

    conf = get_conf()

    print("=" * 60)
    print("Community Mule Density Feature")
    print("=" * 60)
    print(f"URI:      {uri}")
    print(f"Database: {database or 'default'}")
    print("-" * 60)

    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        # Run batch processing first
        print("\n[BATCH] Running community detection and density calculation...")
        print("-" * 60)

        communities = run_batch(driver, database=database)

        if communities:
            # Filter to communities with meaningful size (> 10 members)
            large_communities = [c for c in communities if c['communitySize'] > 10]
            print(f"\nTop 10 communities by mule density (size > 10):\n")
            print(f"{'Community':<12} {'Size':<8} {'Mules':<8} {'Density':<10}")
            print("-" * 40)

            for comm in large_communities[:10]:
                density_pct = f"{comm['muleDensity']:.2%}" if comm['muleDensity'] else "0.00%"
                print(
                    f"{comm['communityId']:<12} "
                    f"{comm['communitySize']:<8} "
                    f"{comm['muleCount']:<8} "
                    f"{density_pct}"
                )

        # Now run real-time query
        print("\n" + "=" * 60)
        print("[REAL-TIME] Transaction Evaluation")
        print("=" * 60)
        print(f"Source: {conf['sourceAccount']}")
        print(f"Target: {conf['targetAccount']}")
        print("-" * 60)

        result = run(driver, database=database, **conf)

        if result:
            print("\nSource Account:")
            print(f"  Community ID:   {result.get('sourceCommunityId')}")
            print(f"  Community Size: {result.get('sourceCommunitySize')}")
            print(f"  Mule Count:     {result.get('sourceMuleCount')}")
            src_density = result.get('sourceMuleDensity')
            print(f"  Mule Density:   {src_density:.2%}" if src_density else "  Mule Density:   N/A")

            print("\nTarget Account:")
            print(f"  Community ID:   {result.get('targetCommunityId')}")
            print(f"  Community Size: {result.get('targetCommunitySize')}")
            print(f"  Mule Count:     {result.get('targetMuleCount')}")
            tgt_density = result.get('targetMuleDensity')
            print(f"  Mule Density:   {tgt_density:.2%}" if tgt_density else "  Mule Density:   N/A")

            # Risk assessment
            threshold = 0.2
            src_risk = src_density and src_density > threshold
            tgt_risk = tgt_density and tgt_density > threshold

            print("\n" + "-" * 60)
            if src_risk or tgt_risk:
                print(f"⚠️  HIGH RISK: Density exceeds {threshold:.0%} threshold")
                if src_risk:
                    print(f"   - Source account in suspicious community")
                if tgt_risk:
                    print(f"   - Target account in suspicious community")
            else:
                print(f"✓  LOW RISK: Both accounts below {threshold:.0%} threshold")
        else:
            print("\nNo results - accounts may not exist or batch processing not run")

        print("\n" + "=" * 60)
