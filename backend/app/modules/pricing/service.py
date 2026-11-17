"""Delivery charge and GST for a basket, shared by the cart and checkout so both show the same
numbers (ADR 0009).

GST is worked out per line, rounded to the paisa (half up), then added up:
- prices include GST: GST = line * rate / (100% + rate); the total doesn't change.
- prices exclude GST: GST = line * rate; it is added to the total as tax.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.audit import service as audit
from app.modules.pricing.models import ShopCharges
from app.modules.pricing.schemas import Charges, ChargesUpdate


def get(db: Session) -> Charges:
    row = db.get(ShopCharges, 1)
    if row is None:
        return Charges(
            shipping_fee_minor=get_settings().shipping_fee_minor,
            free_shipping_over_minor=None,
            prices_include_gst=True,
            default_gst_rate_bp=1800,
        )
    return Charges(
        shipping_fee_minor=row.shipping_fee_minor,
        free_shipping_over_minor=row.free_shipping_over_minor,
        prices_include_gst=row.prices_include_gst,
        default_gst_rate_bp=row.default_gst_rate_bp,
    )


def update(db: Session, data: ChargesUpdate, *, actor_id: uuid.UUID, request: Request) -> Charges:
    before = get(db).model_dump()
    row = db.get(ShopCharges, 1)
    if row is None:
        row = ShopCharges(id=1)
        db.add(row)
    row.shipping_fee_minor = data.shipping_fee_minor
    row.free_shipping_over_minor = data.free_shipping_over_minor
    row.prices_include_gst = data.prices_include_gst
    row.default_gst_rate_bp = data.default_gst_rate_bp
    row.updated_by = actor_id
    audit.record(
        db,
        "charges.updated",
        actor_id=actor_id,
        request=request,
        entity_type="charges",
        entity_id="1",
        before=before,
        after=data.model_dump(),
    )
    db.commit()
    return get(db)


def _div_round(numerator: int, denominator: int) -> int:
    """Integer division rounded half up (amounts are never negative)."""
    return (2 * numerator + denominator) // (2 * denominator)


def line_gst(line_total_minor: int, rate_bp: int, prices_include_gst: bool) -> int:
    if prices_include_gst:
        return _div_round(line_total_minor * rate_bp, 10_000 + rate_bp)
    return _div_round(line_total_minor * rate_bp, 10_000)


@dataclass(frozen=True)
class Line:
    total_minor: int
    gst_rate_bp: int | None  # None: the shop's default rate


@dataclass(frozen=True)
class Quote:
    subtotal_minor: int
    shipping_minor: int
    tax_minor: int  # added to the total (0 when prices include GST)
    gst_minor: int  # all GST in the order, included or added
    total_minor: int
    line_rates_bp: tuple[int, ...]
    line_gst_minor: tuple[int, ...]
    prices_include_gst: bool
    free_shipping_over_minor: int | None


def quote(charges: Charges, lines: Sequence[Line]) -> Quote:
    rates = tuple(
        charges.default_gst_rate_bp if line.gst_rate_bp is None else line.gst_rate_bp
        for line in lines
    )
    gst = tuple(
        line_gst(line.total_minor, rate, charges.prices_include_gst)
        for line, rate in zip(lines, rates, strict=True)
    )
    subtotal = sum(line.total_minor for line in lines)
    free = (
        charges.free_shipping_over_minor is not None
        and subtotal >= charges.free_shipping_over_minor
    )
    shipping = 0 if not lines or free else charges.shipping_fee_minor
    tax = 0 if charges.prices_include_gst else sum(gst)
    return Quote(
        subtotal_minor=subtotal,
        shipping_minor=shipping,
        tax_minor=tax,
        gst_minor=sum(gst),
        total_minor=subtotal + shipping + tax,
        line_rates_bp=rates,
        line_gst_minor=gst,
        prices_include_gst=charges.prices_include_gst,
        free_shipping_over_minor=charges.free_shipping_over_minor if lines else None,
    )
