from typing import Any, Literal

from pydantic import BaseModel, Field


class Meta(BaseModel):
    title: str
    kicker: str
    sub: str
    pills: list[str] = []


class VehicleOption(BaseModel):
    id: str
    label: str
    kmpl: float


class PriceDefaults(BaseModel):
    pax: int
    nights: int
    hotelPerNight: float
    foodPerPersonDay: float
    tolls: float
    entriesPerPerson: float
    campPerPerson: float
    misc: float


class Prices(BaseModel):
    petrolDelhi: float
    petrolRajasthan: float
    blended: float
    defaults: PriceDefaults


class Budget(BaseModel):
    vehicle: list[VehicleOption]
    prices: Prices
    legs: list[list[Any]] = []


class Alert(BaseModel):
    type: str
    html: str


class TimetableEntry(BaseModel):
    time: str
    what: str
    desc: str | None = None
    key: bool = False
    status: Literal["planned", "visited", "skipped"] = "planned"


class Day(BaseModel):
    n: str
    title: str
    wd: str | None = None
    km: int | None = None
    load: str | None = None
    star: bool = False
    stat: str | None = None
    map: str | None = None
    photos: list[str] = []
    alerts: list[Alert] = []
    tl: list[TimetableEntry] = []
    logistics: list[list[str]] = []


class Variant(BaseModel):
    name: str
    km: int
    how: str
    tradeoff: str


class NoteBlock(BaseModel):
    h: str
    items: list[str]


class Reference(BaseModel):
    food: list[list[Any]] = []
    stays: list[list[Any]] = []
    fuelStops: list[list[Any]] = []
    variants: list[Variant] = []
    notes: list[NoteBlock] = []
    sources: list[str] = []
    photoUrls: dict[str, str] = {}
    photoWiki: dict[str, list[str]] = {}


class ChecklistItem(BaseModel):
    id: str
    text: str
    done: bool = False


class Expense(BaseModel):
    id: str | None = None
    date: str
    amount: float
    currency: str = "INR"
    paidBy: str
    category: str | None = None
    note: str | None = None
    dayRef: str | None = None


class StatusUpdate(BaseModel):
    status: Literal["planned", "visited", "skipped"]
