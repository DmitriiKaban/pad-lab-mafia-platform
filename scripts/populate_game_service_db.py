import sys
import os
import time
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from app.database.models import Lobby, Player, GameEvent, Vote, Base
import random
import string

load_dotenv()

# Add the parent directory to the path so we can import our app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_database_url():
    """Smart database URL that works both locally and in Docker"""
    user = os.getenv("GAME_SERVICE_POSTGRES_USER")
    password = os.getenv("GAME_SERVICE_POSTGRES_PASSWORD")
    db = os.getenv("GAME_SERVICE_POSTGRES_DB")

    # Auto-detect environment
    if os.path.exists('/.dockerenv') or os.getenv('DOCKER_ENV'):
        # Running inside Docker container
        host = "game-service-db"
        port = "5432"
        print("Detected Docker environment - connecting to 'db' service")
    else:
        # Running locally
        host = "localhost"
        port = "5434"
        print("Detected local environment - connecting to localhost:5434")



    # Only use environment variables when running in Docker
    if os.path.exists('/.dockerenv') or os.getenv('DOCKER_ENV'):
        host = os.getenv("GAME_SERVICE_POSTGRES_HOST", host)
        port = os.getenv("GAME_SERVICE_POSTGRES_PORT", port)

    database_url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
    print(f"Database URL: postgresql://{user}:***@{host}:{port}/{db}")

    return database_url


def wait_for_database(database_url, max_retries=30, delay=1):
    """Wait for database to become available"""
    print("Waiting for database to become available...")

    for attempt in range(max_retries):
        try:
            engine = create_engine(database_url)
            engine.connect()
            print("Database is ready!")
            return engine
        except OperationalError as e:
            if attempt < max_retries - 1:
                print(f"Database not ready (attempt {attempt + 1}/{max_retries}). Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"Failed to connect to database after {max_retries} attempts.")
                raise e


def create_tables(engine):
    """Create all tables if they don't exist"""
    print("Creating tables if they don't exist...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")


def generate_join_code(length: int = 4) -> str:
    """Generate a random alphanumeric join code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def create_sample_lobbies(db):
    """Create sample lobbies for testing"""
    print("Creating sample lobbies...")

    sample_lobbies = [
        {
            "game_id": 1001,
            "lobby_id": 2001,
            "host_id": 1,  # Assuming user ID 1 exists from user service
            "lobby_name": "Beginner's Game",
            "max_players": 8,
            "status": "waiting_for_players",
            "join_code": generate_join_code(),
            "phase": "day",
            "day_number": 1
        },
        {
            "game_id": 1002,
            "lobby_id": 2002,
            "host_id": 2,  # Assuming user ID 2 exists
            "lobby_name": "Pro Players Only",
            "max_players": 12,
            "status": "waiting_for_players",
            "join_code": generate_join_code(),
            "phase": "day",
            "day_number": 1
        },
        {
            "game_id": 1003,
            "lobby_id": 2003,
            "host_id": 1,
            "lobby_name": "Quick Match",
            "max_players": 6,
            "status": "started",
            "join_code": generate_join_code(),
            "phase": "voting",
            "day_number": 2
        }
    ]

    created_lobbies = []
    for lobby_data in sample_lobbies:
        # Check if lobby already exists
        existing_lobby = db.query(Lobby).filter(
            Lobby.lobby_id == lobby_data["lobby_id"]
        ).first()

        if not existing_lobby:
            new_lobby = Lobby(
                game_id=lobby_data["game_id"],
                lobby_id=lobby_data["lobby_id"],
                host_id=lobby_data["host_id"],
                lobby_name=lobby_data["lobby_name"],
                max_players=lobby_data["max_players"],
                status=lobby_data["status"],
                join_code=lobby_data["join_code"],
                phase=lobby_data["phase"],
                day_number=lobby_data["day_number"]
            )

            db.add(new_lobby)
            created_lobbies.append(new_lobby)
            print(
                f"Created lobby: {lobby_data['lobby_name']} (ID: {lobby_data['lobby_id']}, Join Code: {lobby_data['join_code']})")

    db.commit()
    return created_lobbies


def create_sample_players(db, lobbies):
    """Create sample players for testing lobbies"""
    print("Creating sample players...")

    roles = ["mafia", "doctor", "investigator", "villager", "villager", "villager"]
    careers = ["teacher", "journalist", "engineer", "chef", "farmer", "builder"]

    for lobby in lobbies:
        # Create different numbers of players based on lobby status
        if lobby.status == "waiting_for_players":
            player_count = random.randint(2, min(5, lobby.max_players))
        else:  # started game
            player_count = random.randint(5, lobby.max_players)

        print(f"  Adding {player_count} players to lobby '{lobby.lobby_name}'")

        for i in range(player_count):
            # Generate test user IDs (assuming they exist in user service)
            user_id = (i + 1) + (lobby.lobby_id * 10)  # Generate unique user IDs
            username = f"player_{user_id}"

            # Check if player already exists in this lobby
            existing_player = db.query(Player).filter(
                Player.user_id == user_id,
                Player.lobby_id == lobby.id
            ).first()

            if not existing_player:
                # Assign role and career if game has started
                role = None
                career = None
                status = "alive"

                if lobby.status == "started":
                    role = roles[i % len(roles)]
                    career = careers[i % len(careers)]
                    # Randomly eliminate one player in started games for demo
                    if i == player_count - 1 and player_count > 5:
                        status = "eliminated"

                new_player = Player(
                    user_id=user_id,
                    username=username,
                    lobby_id=lobby.id,
                    role=role,
                    career=career,
                    status=status
                )

                db.add(new_player)
                print(f"    Added player: {username} (Role: {role}, Career: {career}, Status: {status})")

    db.commit()


def create_sample_game_events(db):
    """Create sample game events for started games"""
    print("Creating sample game events...")

    started_lobbies = db.query(Lobby).filter(Lobby.status == "started").all()

    for lobby in started_lobbies:
        # Create some sample events
        sample_events = [
            {
                "day_number": 1,
                "type": "announcement",
                "message": "The game has begun! It is now Day 1."
            },
            {
                "day_number": 1,
                "type": "elimination",
                "message": "TestPlayer was eliminated by popular vote."
            },
            {
                "day_number": 2,
                "type": "announcement",
                "message": "Night has fallen. The mafia are choosing their target..."
            }
        ]

        for event_data in sample_events:
            # Check if event already exists
            existing_event = db.query(GameEvent).filter(
                GameEvent.lobby_id == lobby.id,
                GameEvent.day_number == event_data["day_number"],
                GameEvent.message == event_data["message"]
            ).first()

            if not existing_event:
                new_event = GameEvent(
                    lobby_id=lobby.id,
                    day_number=event_data["day_number"],
                    type=event_data["type"],
                    message=event_data["message"]
                )

                db.add(new_event)
                print(f"  Added event to lobby {lobby.lobby_name}: {event_data['message']}")

    db.commit()


def create_sample_votes(db):
    """Create sample votes for testing"""
    print("Creating sample votes...")

    voting_lobbies = db.query(Lobby).filter(Lobby.phase == "voting").all()

    for lobby in voting_lobbies:
        players = lobby.players
        alive_players = [p for p in players if p.status == "alive"]

        if len(alive_players) >= 2:
            # Create some sample votes
            for i, voter in enumerate(alive_players[:3]):  # First 3 players vote
                if i < len(alive_players) - 1:  # Don't let player vote for themselves
                    target = alive_players[i + 1] if i + 1 < len(alive_players) else alive_players[0]

                    # Check if vote already exists
                    existing_vote = db.query(Vote).filter(
                        Vote.lobby_id == lobby.id,
                        Vote.day_number == lobby.day_number,
                        Vote.voter_id == voter.user_id
                    ).first()

                    if not existing_vote:
                        new_vote = Vote(
                            lobby_id=lobby.id,
                            day_number=lobby.day_number,
                            voter_id=voter.user_id,
                            target_id=target.user_id
                        )

                        db.add(new_vote)
                        print(f"  Added vote: {voter.username} voted for {target.username}")

    db.commit()


def populate_database():
    """Main function to populate the database with initial data"""
    database_url = get_database_url()
    print(f"Connecting to database...")

    # Wait for database to be ready and get engine
    engine = wait_for_database(database_url)

    # Create tables
    create_tables(engine)

    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        print("Checking if database needs population...")

        # Check if any lobbies already exist
        existing_lobbies = db.query(Lobby).first()

        if existing_lobbies is None:
            print("No lobbies found. Creating sample data...")

            # Create sample data
            lobbies = create_sample_lobbies(db)

            # Refresh lobbies to get their database IDs
            for lobby in lobbies:
                db.refresh(lobby)

            create_sample_players(db, lobbies)
            create_sample_game_events(db)
            create_sample_votes(db)

            print(f"Successfully created sample game data!")
            print(f"Created {len(lobbies)} lobbies with players, events, and votes.")
            print("\nSample Join Codes:")
            for lobby in lobbies:
                print(f"  {lobby.lobby_name}: {lobby.join_code} (Lobby ID: {lobby.lobby_id})")

        else:
            lobby_count = db.query(Lobby).count()
            player_count = db.query(Player).count()
            event_count = db.query(GameEvent).count()
            vote_count = db.query(Vote).count()

            print(f"Database already contains data:")
            print(f"  - {lobby_count} lobbies")
            print(f"  - {player_count} players")
            print(f"  - {event_count} game events")
            print(f"  - {vote_count} votes")
            print("No action taken.")

    except Exception as e:
        print(f"Error populating database: {e}")
        db.rollback()
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("GAME SERVICE DATABASE POPULATION SCRIPT")
    print("=" * 60)

    try:
        populate_database()
        print("\n" + "=" * 60)
        print("GAME SERVICE DATABASE POPULATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
    except Exception as e:
        print(f"\n" + "=" * 60)
        print("GAME SERVICE DATABASE POPULATION FAILED!")
        print(f"Error: {e}")
        print("=" * 60)
        sys.exit(1)