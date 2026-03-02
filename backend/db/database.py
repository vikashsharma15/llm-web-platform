from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from core.config import get_settings
# this is going to be the file where we are going to be creating our database engine and our database session and our base class for our models and then we are going to be importing this database session in our endpoints and then we are going to be using it to interact with our database

engine = create_engine(
    get_settings().DATABASE_URL # this is going to be the url for our database and we are going to be loading it from our environment variables using our settings class that we created in our core config file and then we are going to be using this engine to create our database session and then we are going to be using this engine to create our database tables based on our models that we are going to be creating in our models folder
)

# this is going to be the base class for our models and then we are going to be inheriting from this base class in our models to create our database tables and then we are going to be using the database session to interact with our database tables
SessionLocal = sessionmaker(autocommit = False, autoflush = False, bind = engine)

# this is going to be the function that we are going to be using in our endpoints to get a database session and then we are going to be using this database session to interact with our database tables and then we are going to be closing the database session after we are done interacting with our database tables to prevent any memory leaks or any issues with too many open database connections
Base = declarative_base()

def get_db():
    db = SessionLocal() # this is going to create a new database session for us and then we are going to be using this database session to interact with our database tables and then we are going to be closing the database session after we are done interacting with our database tables to prevent any memory leaks or any issues with too many open database connections
    try:
        yield db # this is going to yield the database session to our endpoints and then we are going to be using this database session to interact with our database tables and then we are going to be closing the database session after we are done interacting with our database tables to prevent any memory leaks or any issues with too many open database connections
    finally:
        db.close() # this is going to close the database session after we are done interacting with our database tables to prevent any memory leaks or any issues with too many open database connections

def create_tables():
    Base.metadata.create_all(bind=engine) # this is going to create our database tables based on our models that we are going to be creating in our models folder and then we are going to be using this function to create our database tables when we run our application for the first time or when we make changes to our models and then we are going to be using alembic to manage our database migrations when we make changes to our models and then we are going to be using this function to create our database tables when we run our application for the first time or when we make changes to our models and then we are going to be using alembic to manage our database migrations when we make changes to our models

