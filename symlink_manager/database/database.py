from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
engine = create_engine("sqlite:///media_library.db")
Session = sessionmaker(bind=engine)


def create_tables(engine=engine, drop_existing=False, echo=True):
    """Create all database tables defined in the model classes.

    Args:
        engine: SQLAlchemy engine to use (defaults to the pre-configured engine)
        drop_existing: If True, drop all existing tables before creating them (use with caution)
        echo: If True, print status messages to stdout

    Returns:
        bool: True if operation was successful, False otherwise
    """
    try:
        if drop_existing:
            if echo:
                print("Dropping all existing tables...")
            Base.metadata.drop_all(engine)

        if echo:
            print("Creating database tables...")

        Base.metadata.create_all(engine)

        if echo:
            # Get list of created tables for informational output
            table_names = list(Base.metadata.tables.keys())
            print(f"Database tables created successfully: {
                  ', '.join(table_names)}")

        return True

    except Exception as e:
        if echo:
            print(f"Error creating database tables: {e}")
        return False
