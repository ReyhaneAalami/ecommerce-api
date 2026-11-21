from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_admin, get_current_vendor
from src.connections.database import get_db
from src.data.models import User, Vendor
from src.schemas.statistics import VendorStatisticsResponse, AdminStatisticsResponse
from src.services.statistics_service import StatisticsService

router = APIRouter(prefix="/statistics", tags=["Statistics"])


@router.get("/vendors/me", response_model=VendorStatisticsResponse)
def vendor_statistics(vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    return StatisticsService.vendor(db, vendor.id, vendor.user_id)


@router.get("/admin", response_model=AdminStatisticsResponse)
def admin_statistics(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return StatisticsService.admin(db)
