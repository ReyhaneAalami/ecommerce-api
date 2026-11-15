from sqlalchemy import select
from sqlalchemy.orm import Session

from src.data.models import Vendor


class VendorRepository:

    @staticmethod
    def get_by_id(db: Session, vendor_id: int) -> Vendor | None:
        statement = select(Vendor).where(Vendor.id == vendor_id)
        return db.scalar(statement)

    @staticmethod
    def get_by_user_id(db: Session, user_id: int) -> Vendor | None:
        statement = select(Vendor).where(Vendor.user_id == user_id)
        return db.scalar(statement)

    @staticmethod
    def get_by_store_name(
        db: Session,
        store_name: str,
    ) -> Vendor | None:
        statement = select(Vendor).where(
            Vendor.store_name == store_name
        )
        return db.scalar(statement)

    @staticmethod
    def get_by_status(
        db: Session,
        status: str,
    ) -> list[Vendor]:
        statement = (
            select(Vendor)
            .where(Vendor.status == status)
            .order_by(Vendor.created_at.asc())
        )
        return list(db.scalars(statement).all())

    @staticmethod
    def create(db: Session, vendor_data: dict) -> Vendor:
        vendor = Vendor(**vendor_data)

        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        return vendor

    @staticmethod
    def update(
        db: Session,
        vendor: Vendor,
        update_data: dict,
    ) -> Vendor:
        for field, value in update_data.items():
            setattr(vendor, field, value)

        db.commit()
        db.refresh(vendor)

        return vendor