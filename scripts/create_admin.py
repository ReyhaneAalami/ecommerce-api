
from getpass import getpass

from pydantic import ValidationError
from sqlalchemy import select

from src.connections.database import SessionLocal
from src.data.models import User
from src.schemas.user import UserCreate
from src.utils.security import hash_password


def create_first_admin():
    db = SessionLocal()

    try:
        existing_admin = db.scalar(
            select(User.id)
            .where(User.role == "admin")
            .limit(1)
        )

        if existing_admin is not None:
            print("An administrator account already exists.")
            print("Admin creation has been disabled.")
            return

        print("=== Create First Administrator ===")

        full_name = input("Full name: ").strip()
        email = input("Email: ").strip().lower()

        password = getpass("Password: ")
        password_confirmation = getpass("Confirm password: ")

        if password != password_confirmation:
            print("Passwords do not match.")
            return

        try:
            validated_data = UserCreate(
                full_name=full_name,
                email=email,
                password=password,
                phone=None,
            )
        except ValidationError as error:
            print("Invalid administrator information:")
            print(error)
            return

        existing_user = db.scalar(
            select(User.id).where(
                User.email == validated_data.email
            )
        )

        if existing_user is not None:
            print("This email is already registered.")
            return

        admin = User(
            full_name=validated_data.full_name,
            email=str(validated_data.email),
            phone=None,
            password_hash=hash_password(
                validated_data.password
            ),
            role="admin",
            is_active=True,
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        print("\nAdministrator created successfully.")
        print(f"Admin ID: {admin.id}")
        print(f"Email: {admin.email}")
        print(f"Role: {admin.role}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    create_first_admin()
