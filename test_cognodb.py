import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Read values from .env
load_dotenv()

# Get CognoDB details
uri = os.getenv("COGNODB_URI")
username = os.getenv("COGNODB_USER")
password = os.getenv("COGNODB_PASSWORD")

print("Connecting to CognoDB...")

# Create connection
driver = GraphDatabase.driver(
    uri,
    auth=(username, password)
)

try:
    # Test connection
    driver.verify_connectivity()
    print("Successfully connected to CognoDB!")

finally:
    driver.close()