
from sqlalchemy import text
from src.connections.database import engine

try:
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_database(), current_user")
        )
        database, user = result.fetchone()

        print("Database:", database)
        print("User:", user)
        print("Database connection successful!")

except Exception as error:
    print("Database connection failed:")
    print(error)

finally:
    engine.dispose()
