from fastapi import APIRouter, Depends

from ..auth import require_auth
from ..models import Expense
from ..services import trip_service

router = APIRouter(prefix="/api/expenses", tags=["expenses"])


@router.get("")
def list_expenses(paidBy: str | None = None, dayRef: str | None = None):
    return trip_service.list_expenses(paid_by=paidBy, day_ref=dayRef)


@router.post("", dependencies=[Depends(require_auth)])
def add_expense(expense: Expense):
    return trip_service.add_expense(expense.model_dump(exclude_none=True))


@router.delete("/{expense_id}", dependencies=[Depends(require_auth)])
def delete_expense(expense_id: str):
    trip_service.delete_expense(expense_id)
    return {"ok": True}
