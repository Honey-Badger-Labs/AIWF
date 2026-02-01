"""
Database Connection & Session Management

Provides SQLAlchemy engine with connection pooling,
session factory, and database initialization.
"""

import os
import logging
from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.exc import SQLAlchemyError
from database_models import Base

logger = logging.getLogger(__name__)

# Database Configuration
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:postgres@localhost:5432/aiwf'
)

# Connection Pool Settings
POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '20'))
POOL_MAX_OVERFLOW = int(os.getenv('DB_POOL_MAX_OVERFLOW', '10'))
POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', '30'))
POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', '3600'))  # 1 hour

# Engine singleton
_engine = None
_session_factory = None


# ============================================================================
# ENGINE CREATION
# ============================================================================

def get_engine():
    """Get or create SQLAlchemy engine with connection pooling"""
    global _engine
    
    if _engine is None:
        logger.info(f"Creating database engine: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}")
        
        _engine = create_engine(
            DATABASE_URL,
            poolclass=pool.QueuePool,
            pool_size=POOL_SIZE,
            max_overflow=POOL_MAX_OVERFLOW,
            pool_timeout=POOL_TIMEOUT,
            pool_recycle=POOL_RECYCLE,
            pool_pre_ping=True,  # Verify connections before using
            echo=os.getenv('DB_ECHO', 'false').lower() == 'true',  # SQL logging
            future=True  # SQLAlchemy 2.0 style
        )
        
        # Event listeners
        @event.listens_for(_engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Log new database connections"""
            logger.debug("New database connection established")
        
        @event.listens_for(_engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Log connection checkout from pool"""
            logger.debug("Connection checked out from pool")
    
    return _engine


# ============================================================================
# SESSION FACTORY
# ============================================================================

def get_session_factory():
    """Get or create session factory"""
    global _session_factory
    
    if _session_factory is None:
        engine = get_engine()
        _session_factory = scoped_session(
            sessionmaker(
                bind=engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False  # Prevent lazy loading issues
            )
        )
        logger.info("Session factory created")
    
    return _session_factory


def get_session() -> Session:
    """
    Get a new database session.
    
    Usage:
        session = get_session()
        try:
            # Do database operations
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    """
    factory = get_session_factory()
    return factory()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Context manager for database sessions with automatic commit/rollback.
    
    Usage:
        with session_scope() as session:
            user = User(email='test@example.com', name='Test User')
            session.add(user)
            # Automatically commits on success, rolls back on error
    """
    session = get_session()
    try:
        yield session
        session.commit()
        logger.debug("Session committed successfully")
    except Exception as e:
        session.rollback()
        logger.error(f"Session rollback due to error: {e}")
        raise
    finally:
        session.close()
        logger.debug("Session closed")


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_database(drop_all: bool = False):
    """
    Initialize database schema.
    
    Args:
        drop_all: If True, drop all tables before creating (WARNING: DATA LOSS!)
    """
    engine = get_engine()
    
    try:
        if drop_all:
            logger.warning("Dropping all database tables...")
            Base.metadata.drop_all(bind=engine)
        
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialization complete")
        
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def check_database_health() -> bool:
    """
    Check if database connection is healthy.
    
    Returns:
        True if database is accessible, False otherwise
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("Database health check: OK")
        return True
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def get_pool_status() -> dict:
    """
    Get connection pool status.
    
    Returns:
        Dict with pool metrics (size, checked_in, checked_out, overflow, etc.)
    """
    engine = get_engine()
    pool = engine.pool
    
    return {
        'pool_size': pool.size(),
        'checked_in': pool.checkedin(),
        'checked_out': pool.checkedout(),
        'overflow': pool.overflow(),
        'total_connections': pool.size() + pool.overflow(),
        'status': 'healthy' if check_database_health() else 'unhealthy'
    }


# ============================================================================
# CLEANUP
# ============================================================================

def close_database():
    """Close database connections and dispose of engine"""
    global _engine, _session_factory
    
    if _session_factory:
        _session_factory.close_all()
        _session_factory = None
        logger.info("Session factory closed")
    
    if _engine:
        _engine.dispose()
        _engine = None
        logger.info("Database engine disposed")


# ============================================================================
# DATABASE MIGRATION HELPERS
# ============================================================================

def run_sql_file(filepath: str):
    """
    Execute SQL commands from a file.
    
    Args:
        filepath: Path to SQL file (e.g., database/schema.sql)
    """
    engine = get_engine()
    
    try:
        with open(filepath, 'r') as f:
            sql = f.read()
        
        with engine.connect() as conn:
            # Execute each statement separately
            for statement in sql.split(';'):
                statement = statement.strip()
                if statement:
                    conn.execute(statement)
        
        logger.info(f"SQL file executed successfully: {filepath}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to execute SQL file {filepath}: {e}")
        raise


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize database
    print("Initializing database...")
    init_database()
    
    # Check health
    print("\nChecking database health...")
    health = check_database_health()
    print(f"Database healthy: {health}")
    
    # Pool status
    print("\nConnection pool status:")
    status = get_pool_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # Test session
    print("\nTesting session...")
    with session_scope() as session:
        from database_models import User
        
        # Create test user
        user = User(
            email='test@honeybadgerlabs.io',
            name='Test User',
            role='developer'
        )
        session.add(user)
        print(f"Created user: {user}")
    
    # Cleanup
    print("\nClosing database...")
    close_database()
    print("Done!")
