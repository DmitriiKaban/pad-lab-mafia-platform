import sys
import os
import time
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from app.models import User, Base
from app.security import get_password_hash


load_dotenv()

# Add the parent directory to the path so we can import our app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_database_url():
    """Smart database URL that works both locally and in Docker"""
    user = os.getenv("USER_MANAGEMENT_SERVICE_POSTGRES_USER")
    password = os.getenv("USER_MANAGEMENT_SERVICE_POSTGRES_PASSWORD")
    db = os.getenv("USER_MANAGEMENT_SERVICE_POSTGRES_DB")

    # Auto-detect environment
    if os.path.exists('/.dockerenv') or os.getenv('DOCKER_ENV'):
        # Running inside Docker container
        host = "db_user_management_service"
        port = "5432"
        print("Detected Docker environment - connecting to 'db' service")
    else:
        # Running locally
        host = "localhost"
        port = "5433"
        print("Detected local environment - connecting to localhost:5433")

    # Only use environment variables when running in Docker
    if os.path.exists('/.dockerenv') or os.getenv('DOCKER_ENV'):
        host = os.getenv("USER_MANAGEMENT_SERVICE_POSTGRES_HOST", host)
        port = os.getenv("USER_MANAGEMENT_SERVICE_POSTGRES_PORT", port)

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

        # Check if any users already exist
        existing_users = db.query(User).first()

        if existing_users is None:
            print("No users found. Creating default users...")

            # Create default users
            default_users = [
                {
                    "username": "testuser223",
                    "email": "test223@example.com",
                    "password": "password123334",
                    "identification": "test_021",
                    "deviceInfo": {"os": "web", "type": "browser"},
                    "location": "test_location",
                    "currency": {"diamonds": 100, "coins": 1000}
                }
            ]

            for user_data in default_users:
                new_user = User(
                    username=user_data["username"],
                    email=user_data["email"],
                    password=get_password_hash(user_data["password"]),
                    identification=user_data["identification"],
                    deviceInfo=user_data["deviceInfo"],
                    location=user_data["location"],
                    currency=user_data["currency"]
                )

                db.add(new_user)
                print(f"Created user: {user_data['username']} (password: {user_data['password']})")

            # Commit all users
            db.commit()
            print(f"Successfully created {len(default_users)} default users!")

        else:
            user_count = db.query(User).count()
            print(f"Database already contains {user_count} users. No action taken.")

    except Exception as e:
        print(f"Error populating database: {e}")
        db.rollback()
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 50)
    print("DATABASE POPULATION SCRIPT")
    print("=" * 50)

    try:
        populate_database()
        print("\n" + "=" * 50)
        print("DATABASE POPULATION COMPLETED SUCCESSFULLY!")
        print("=" * 50)
    except Exception as e:
        print(f"\n" + "=" * 50)
        print("DATABASE POPULATION FAILED!")
        print(f"Error: {e}")
        print("=" * 50)
        sys.exit(1)