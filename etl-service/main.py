import os
import time
import schedule
import pandas as pd
import re
from sqlalchemy import create_engine
from datetime import datetime

# Environment Config
WAREHOUSE_URL = os.getenv("WAREHOUSE_URL")
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL_SECONDS", "60"))

# Global config storage
SOURCES = {}

def create_ha_engine(connection_string):
    """
    Creates a SQLAlchemy engine that supports High Availability (multiple hosts).
    Parses a string like: postgresql://user:pass@host1:5432,host2:5432/db
    """
    if not connection_string:
        return None

    # If simple URL (no commas in the host part), just return standard engine
    if "," not in connection_string.split("@")[-1]:
        return create_engine(connection_string)

    try:
        # 1. Extract parts using Regex
        # Matches: postgresql://(user:pass)@(host_list)/(db_name)
        match = re.match(r"postgresql://([^@]+)@([^/]+)/(.+)", connection_string)
        if not match:
            print(f"Error parsing HA URL: {connection_string}")
            return None

        user_pass = match.group(1)
        raw_hosts = match.group(2) # "host1:5432,host2:5432"
        db_name = match.group(3)

        # 2. Parse Hosts and Ports
        # Split by comma to get ["host1:5432", "host2:5432"]
        host_entries = raw_hosts.split(",")

        clean_hosts = []
        clean_ports = []

        for entry in host_entries:
            if ":" in entry:
                h, p = entry.split(":")
                clean_hosts.append(h)
                clean_ports.append(p)
            else:
                clean_hosts.append(entry)
                clean_ports.append("5432") # Default port

        # 3. Construct LibPQ parameters
        # LibPQ expects comma-separated strings for host and port
        ha_host_str = ",".join(clean_hosts)
        ha_port_str = ",".join(clean_ports)

        # 4. Create a "Safe" URL for SQLAlchemy (using just the first host to pass validation)
        # We replace the complex host string with just the first one
        first_host = clean_hosts[0]
        first_port = clean_ports[0]
        safe_url = f"postgresql://{user_pass}@{first_host}:{first_port}/{db_name}"

        # 5. Inject the full cluster list into connect_args
        # This overrides the 'safe_url' host when actually connecting
        engine = create_engine(
            safe_url,
            connect_args={
                "host": ha_host_str,
                "port": ha_port_str,
                "target_session_attrs": "prefer-standby" # ETL can read from Replicas!
            }
        )
        return engine

    except Exception as e:
        print(f"Failed to create HA engine: {e}")
        return None

def init_sources():
    """Initialize DB configuration"""
    global SOURCES
    SOURCES = {
        "TownService": {
            "url": os.getenv("TOWN_DB_URL"),
            "tables": ["locations", "movements"]
        },
        "CharacterService": {
            "url": os.getenv("CHARACTER_DB_URL"),
            "tables": ["assets", "asset_slots", "items", "player_assets", "player_items"]
        },
        "TaskService": {
            "url": os.getenv("TASK_DB_URL"),
            "tables": ["tasks", "rumor_event_log"]
        },
        "VotingService": {
            "url": os.getenv("VOTING_DB_URL"),
            "tables": ["games", "voting_sessions", "votes"]
        },
        "UserService": {
            "url": os.getenv("USER_DB_URL"),
            "tables": ["user", "pending_transaction"]
        },
        "RumoursService": {
            "url": os.getenv("RUMOURS_DB_URL"),
            "tables": ["Rumours"]
        },
        "CommunicationService": {
            "url": os.getenv("COMMUNICATION_DB_URL"),
            "tables": ["Messages", "Lobbies", "PrivateChannels", "PrivateChannelMembers", "Announcements"]
        },
        "GameService": {
            "url": os.getenv("GAME_DB_URL"),
            "tables": ["lobbies", "players", "game_events", "votes"]
        }
    }

def run_etl():
    print(f"[{datetime.now()}] Starting ETL Job...")

    try:
        warehouse_engine = create_engine(WAREHOUSE_URL)
    except Exception as e:
        print(f"CRITICAL: Cannot connect to Data Warehouse: {e}")
        return

    for service_name, config in SOURCES.items():
        source_url = config['url']
        tables = config['tables']

        if not source_url:
            print(f"Skipping {service_name}: No URL configured")
            continue

        if not tables:
            continue

        try:
            # USE THE NEW HA ENGINE CREATOR
            source_engine = create_ha_engine(source_url)
            if not source_engine:
                print(f"Skipping {service_name}: Could not create engine")
                continue

            # Test connection
            with source_engine.connect() as conn:
                pass

            for table in tables:
                try:
                    # Extract
                    query = f"SELECT * FROM {table}"
                    df = pd.read_sql(query, source_engine)

                    if not df.empty:
                        # Transform
                        df['dw_source_service'] = service_name
                        df['dw_synced_at'] = datetime.now()

                        # Load
                        target_table_name = f"{service_name.lower()}_{table}"

                        # Use 'replace' to refresh data.
                        # In production, you might want 'append' with a diff logic.
                        df.to_sql(target_table_name, warehouse_engine, if_exists='replace', index=False)

                        print(f" -> Synced {service_name}.{table} ({len(df)} rows) to {target_table_name}")
                    else:
                        print(f" -> Skipped {service_name}.{table} (Empty)")

                except Exception as e:
                    # Catch individual table errors (e.g. table doesn't exist yet)
                    print(f"    Notice: Table {table} not ready in {service_name} ({e})")

        except Exception as e:
            print(f"Error connecting to source {service_name}: {e}")

    print(f"[{datetime.now()}] ETL Job Finished.\n")

if __name__ == "__main__":
    print("Initializing ETL Service...")
    init_sources()

    print("Waiting 10s for DB clusters to stabilize...")
    time.sleep(10)

    # Run once immediately
    run_etl()

    # Schedule periodic run
    schedule.every(SYNC_INTERVAL).seconds.do(run_etl)

    while True:
        schedule.run_pending()
        time.sleep(1)