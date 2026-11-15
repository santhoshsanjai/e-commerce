import uuid

from pydantic import BaseModel, Field

from app.modules.orders.lifecycle import PaymentMethod


class CheckoutRequest(BaseModel):
    address_id: uuid.UUID
    payment_method: PaymentMethod = PaymentMethod.COD
    delivery_instructions: str = Field(default="", max_length=500)
