"""
Feature: Counterparty Diversity
Description: Calculate counterparty diversity metrics to identify accounts
             with limited transaction networks (potential mule behavior).
"""

# ============================================================================
#  CONFIGURATION - Set parameters for this feature here
# ============================================================================


def get_conf() -> dict:
    """
    Configuration parameters for the Cypher queries.

    Returns:
        dict with keys:
        - accountNumber: The account to evaluate (for batch lookup)
        - sourceAccount: Source account for real-time query
        - targetAccount: Target account for real-time query
    """
    return {
        "accountNumber": "ACC_CUST_835",
        "sourceAccount": "ACC_MULE_55937",
        "targetAccount": "ACC_CUST_2155",
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


def load_query(filename: str) -> str:
    """Load a Cypher query from a file in this directory."""
    cypher_file = Path(__file__).parent / filename
    return cypher_file.read_text()


def calculate_diversity(
    driver: GraphDatabase.driver, database: str | None = None
) -> list[dict]:
    """
    BATCH: Calculate diversity metrics and write to all Account/Mule nodes.

    Run this periodically to update diversity calculations.

    Args:
        driver: Neo4j driver instance
        database: Neo4j database name (None for default)

    Returns:
        List of dicts with per-account diversity metrics
    """
    query = load_query("1-calculate-diversity.cypher")

    with driver.session(database=database) as session:
        result = session.run(query)
        return [record.data() for record in result]


def query_account(
    driver: GraphDatabase.driver, database: str | None = None, **params
) -> dict | None:
    """
    REAL-TIME: Query pre-computed diversity for a single account.

    Requires calculate_diversity() to have run first.

    Args:
        driver: Neo4j driver instance
        database: Neo4j database name (None for default)
        **params: Query parameters
            - accountNumber (str): The account to query

    Returns:
        dict with diversity metrics, or None if not found
    """
    query = load_query("2-query-account.cypher")

    with driver.session(database=database) as session:
        result = session.run(query, **params)
        record = result.single()
        return record.data() if record else None


def query_realtime(
    driver: GraphDatabase.driver, database: str | None = None, **params
) -> dict | None:
    """
    REAL-TIME: Calculate diversity on-the-fly for source and target accounts.

    No pre-computation required - calculates fresh from current transaction data.

    Args:
        driver: Neo4j driver instance
        database: Neo4j database name (None for default)
        **params: Query parameters
            - sourceAccount (str): Account initiating the transaction
            - targetAccount (str): Account receiving the transaction

    Returns:
        dict with diversity metrics for both accounts, or None if not found

    Example:
        >>> result = query_realtime(driver, sourceAccount="ACC123", targetAccount="ACC456")
        >>> if result:
        ...     if result['sourceDiversityRatio'] < 0.1:
        ...         print("Source has low diversity")
    """
    query = load_query("3-query-realtime.cypher")

    with driver.session(database=database) as session:
        result = session.run(query, **params)
        record = result.single()
        return record.data() if record else None


def run_batch(driver: GraphDatabase.driver, database: str | None = None) -> list[dict]:
    """
    Run BATCH processing to update all diversity metrics.

    Args:
        driver: Neo4j driver instance
        database: Neo4j database name (None for default)

    Returns:
        List of account diversity summaries
    """
    print("Calculating counterparty diversity for all accounts...")
    results = calculate_diversity(driver, database=database)
    print(f"Updated diversity metrics for {len(results)} accounts")
    return results


def run(
    driver: GraphDatabase.driver, database: str | None = None, **params
) -> dict | None:
    """
    REAL-TIME query for account evaluation.

    Args:
        driver: Neo4j driver instance
        database: Neo4j database name (None for default)
        **params: Query parameters
            - accountNumber (str): The account to evaluate

    Returns:
        dict with diversity metrics

    Example:
        >>> result = run(driver, accountNumber="ACC123")
        >>> if result and result['diversityRatio'] < 0.1:
        ...     print("LOW DIVERSITY: Potential mule behavior")
    """
    return query_account(driver, database=database, **params)


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
    print("Counterparty Diversity Feature")
    print("=" * 60)
    print(f"URI:      {uri}")
    print(f"Database: {database or 'default'}")
    print("-" * 60)

    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        # Run batch processing
        print("\n[BATCH] Calculating diversity metrics...")
        print("-" * 60)

        results = run_batch(driver, database=database)

        if results:
            # Filter to accounts with meaningful transaction volume (> 10)
            suspicious = [r for r in results if (r.get("totalTransactions") or 0) > 10]

            print(f"\nTop 10 suspicious accounts (low diversity, >10 transactions):\n")
            print(
                f"{'Account':<20} {'Counterparties':<15} {'Transactions':<15} "
                f"{'Ratio':<10} {'Top CP %':<10}"
            )
            print("-" * 70)

            for acc in suspicious[:10]:
                ratio = acc.get("diversityRatio")
                top_share = acc.get("topCounterpartyShare")
                ratio_str = f"{ratio:.2%}" if ratio is not None else "N/A"
                top_str = f"{top_share:.2%}" if top_share is not None else "N/A"
                print(
                    f"{acc.get('accountNumber', 'N/A'):<20} "
                    f"{acc.get('uniqueCounterparties', 0):<15} "
                    f"{acc.get('totalTransactions', 0):<15} "
                    f"{ratio_str:<10} "
                    f"{top_str}"
                )

        # Real-time query (on-the-fly calculation)
        print("\n" + "=" * 60)
        print("[REAL-TIME] Transaction Evaluation (On-the-fly)")
        print("=" * 60)
        print(f"Source: {conf['sourceAccount']}")
        print(f"Target: {conf['targetAccount']}")
        print("-" * 60)

        result = query_realtime(
            driver,
            database=database,
            sourceAccount=conf["sourceAccount"],
            targetAccount=conf["targetAccount"],
        )

        if result:
            print("\nSource Account:")
            print(f"  Unique Counterparties: {result.get('sourceUniqueCounterparties')}")
            print(f"  Total Transactions:    {result.get('sourceTotalTransactions')}")
            src_ratio = result.get("sourceDiversityRatio")
            src_share = result.get("sourceTopCounterpartyShare")
            print(
                f"  Diversity Ratio:       {src_ratio:.2%}"
                if src_ratio is not None
                else "  Diversity Ratio:       N/A"
            )
            print(
                f"  Top Counterparty Share: {src_share:.2%}"
                if src_share is not None
                else "  Top Counterparty Share: N/A"
            )

            print("\nTarget Account:")
            print(f"  Unique Counterparties: {result.get('targetUniqueCounterparties')}")
            print(f"  Total Transactions:    {result.get('targetTotalTransactions')}")
            tgt_ratio = result.get("targetDiversityRatio")
            tgt_share = result.get("targetTopCounterpartyShare")
            print(
                f"  Diversity Ratio:       {tgt_ratio:.2%}"
                if tgt_ratio is not None
                else "  Diversity Ratio:       N/A"
            )
            print(
                f"  Top Counterparty Share: {tgt_share:.2%}"
                if tgt_share is not None
                else "  Top Counterparty Share: N/A"
            )

            # Risk assessment
            print("\n" + "-" * 60)
            threshold_ratio = 0.1
            threshold_share = 0.5

            src_tx = result.get("sourceTotalTransactions") or 0
            tgt_tx = result.get("targetTotalTransactions") or 0

            src_risk = src_ratio is not None and src_ratio < threshold_ratio and src_tx > 50
            tgt_risk = tgt_ratio is not None and tgt_ratio < threshold_ratio and tgt_tx > 50
            src_conc = src_share is not None and src_share > threshold_share
            tgt_conc = tgt_share is not None and tgt_share > threshold_share

            if src_risk or tgt_risk:
                print("HIGH RISK: Low diversity with high volume")
                if src_risk:
                    print(f"  - Source: {src_ratio:.2%} ratio, {src_tx} transactions")
                if tgt_risk:
                    print(f"  - Target: {tgt_ratio:.2%} ratio, {tgt_tx} transactions")
            elif src_conc or tgt_conc:
                print("MEDIUM RISK: High counterparty concentration")
                if src_conc:
                    print(f"  - Source: {src_share:.2%} with top counterparty")
                if tgt_conc:
                    print(f"  - Target: {tgt_share:.2%} with top counterparty")
            else:
                print("LOW RISK: Normal counterparty diversity for both accounts")
        else:
            print("\nAccounts not found")

        print("\n" + "=" * 60)
