from sqlalchemy.orm import Session

from src.data.models import User, Vendor
from src.repositories.vendor_repository import VendorRepository
from src.schemas.vendor import VendorCreate, VendorUpdate


class VendorService:

    @staticmethod
    def register_vendor(
        db: Session,
        user: User,
        vendor_data: VendorCreate,
    ) -> Vendor:

        if user.role != "customer":
            raise ValueError(
                "Only customer accounts can register as vendors."
            )

        existing_vendor = VendorRepository.get_by_user_id(
            db,
            user.id,
        )

        if existing_vendor:
            raise ValueError(
                "This user already has a vendor account."
            )

        store_name = vendor_data.store_name.strip()

        if not store_name:
            raise ValueError("Store name is required.")

        existing_store = VendorRepository.get_by_store_name(
            db,
            store_name,
        )

        if existing_store:
            raise ValueError(
                "This store name is already registered."
            )

        vendor = Vendor(
            user_id=user.id,
            store_name=store_name,
            description=vendor_data.description,
            status="pending",
            is_active=True,
        )

        try:
            user.role = "vendor"
            db.add(vendor)
            db.commit()
            db.refresh(vendor)

        except Exception:
            db.rollback()
            raise

        return vendor

    @staticmethod
    def get_vendor_by_user(
        db: Session,
        user_id: int,
    ) -> Vendor:

        vendor = VendorRepository.get_by_user_id(
            db,
            user_id,
        )

        if not vendor:
            raise ValueError("Vendor account was not found.")

        return vendor

    @staticmethod
    def update_vendor(
        db: Session,
        vendor: Vendor,
        update_data: VendorUpdate,
    ) -> Vendor:

        update_dict = update_data.model_dump(
            exclude_unset=True,
        )

        if not update_dict:
            raise ValueError(
                "At least one field must be provided."
            )

        if (
            "store_name" in update_dict
            and update_dict["store_name"] is not None
        ):
            store_name = update_dict["store_name"].strip()

            if not store_name:
                raise ValueError("Store name cannot be empty.")

            existing_store = VendorRepository.get_by_store_name(
                db,
                store_name,
            )

            if (
                existing_store
                and existing_store.id != vendor.id
            ):
                raise ValueError(
                    "This store name is already registered."
                )

            update_dict["store_name"] = store_name

        return VendorRepository.update(
            db,
            vendor,
            update_dict,
        )

    @staticmethod
    def get_pending_vendors(db: Session) -> list[Vendor]:
        return VendorRepository.get_by_status(
            db,
            "pending",
        )

    @staticmethod
    def review_vendor(
        db: Session,
        vendor_id: int,
        decision: str,
    ) -> Vendor:

        if decision not in {"approved", "rejected"}:
            raise ValueError("Invalid vendor decision.")

        vendor = VendorRepository.get_by_id(
            db,
            vendor_id,
        )

        if vendor is None:
            raise LookupError("Vendor not found.")

        if vendor.status != "pending":
            raise ValueError(
                "Only pending vendor applications can be reviewed."
            )

        update_data = {
            "status": decision,
            "is_active": decision == "approved",
        }

        return VendorRepository.update(
            db,
            vendor,
            update_data,
        )