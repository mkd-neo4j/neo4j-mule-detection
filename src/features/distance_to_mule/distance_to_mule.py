"""
Feature: Distance to Known Mule
Description: Calculate the shortest path distance from an account to the nearest
             confirmed mule account in the transaction network.
"""

# ============================================================================
#  CONFIGURATION - Set parameters for this feature here
# ============================================================================


def get_conf() -> dict:
    """
    Configuration parameters for the Cypher query.

    Returns:
        dict with keys matching the Cypher query parameters:
        - accountNumber: The account to evaluate (empty string = all accounts)
    """
    return {
        "accountNumber": "ACC_CUST_6413",
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


def load_query() -> str:
    """Load the Cypher query from the .cypher file."""
    cypher_file = Path(__file__).parent / "distance_to_mule.cypher"
    return cypher_file.read_text()


def run(driver: GraphDatabase.driver, database: str | None = None, **params) -> list[dict]:
    """
    Execute the distance to mule query.

    Args:
        driver: Neo4j driver instance
        database: Neo4j database name (None for default)
        **params: Query parameters
            - accountNumber (str): The account number to evaluate (null/empty = all)

    Returns:
        List of result records as dictionaries containing:
            - account: The target account number
            - distanceToMule: Number of hops to nearest mule (None if no path)
            - nearestMule: Account number of the nearest confirmed mule
            - pathNodes: List of node identifiers in the path

    Example:
        >>> results = run(driver, accountNumber="ACC123")
        >>> if results:
        ...     print(f"Distance to mule: {results[0]['distanceToMule']}")
    """
    query = load_query()

    with driver.session(database=database) as session:
        result = session.run(query, **params)
        return [record.data() for record in result]


def run_batch(
    driver: GraphDatabase.driver,
    account_numbers: list[str],
    database: str | None = None,
) -> dict[str, dict]:
    """
    Run the query for multiple accounts.

    Args:
        driver: Neo4j driver instance
        account_numbers: List of account numbers to evaluate
        database: Neo4j database name (None for default)

    Returns:
        Dictionary mapping account number to result dict
    """
    results = {}
    for account_number in account_numbers:
        result = run(driver, database=database, accountNumber=account_number)
        if result:
            results[account_number] = result[0]
        else:
            results[account_number] = {
                "account": account_number,
                "distanceToMule": None,
                "nearestMule": None,
                "pathNodes": None,
            }
    return results


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    # Load .env file from project root
    load_dotenv()

    # Example usage - configure via environment variables
    uri = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    database = os.getenv("NEO4J_DATABASE") or None

    conf = get_conf()

    print("=" * 50)
    print("Distance to Mule Feature")
    print("=" * 50)
    print(f"URI:      {uri}")
    print(f"Database: {database or 'default'}")
    print(f"Params:   {conf}")
    print("-" * 50)

    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        results = run(driver, database=database, **conf)

        if results:
            for record in results:
                print()
                print(f"Distance to mule: {record['distanceToMule']} hops")
                print(f"Nearest mule:     {record['nearestMule']}")
                print()
                path_nodes = [str(n) for n in (record['pathNodes'] or []) if n is not None]
                print(f"Path ({len(path_nodes)} nodes):")
                for i, node in enumerate(path_nodes):
                    prefix = "  " if i == 0 else "    -> "
                    print(f"{prefix}{node}")
                print()
                print("=" * 50)
        else:
            print()
            print("No path found to any confirmed mule")
            print("=" * 50)
