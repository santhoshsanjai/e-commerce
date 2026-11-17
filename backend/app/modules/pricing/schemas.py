from pydantic import BaseModel, Field, model_validator

# GST slabs in basis points. Products can use any rate from 0 to 40%; these are the usual ones.
GST_SLABS_BP = (0, 500, 1800, 4000)


class Charges(BaseModel):
    shipping_fee_minor: int
    free_shipping_over_minor: int | None
    prices_include_gst: bool
    default_gst_rate_bp: int


class ChargesUpdate(BaseModel):
    shipping_fee_minor: int = Field(ge=0, le=100_000_00, description="Delivery charge, in paise")
    free_shipping_over_minor: int | None = Field(
        default=None, gt=0, le=10_000_000_00, description="Free delivery from this subtotal"
    )
    prices_include_gst: bool = True
    default_gst_rate_bp: int = Field(ge=0, le=4000, description="1800 = 18%")

    @model_validator(mode="after")
    def _threshold_needs_a_fee(self) -> "ChargesUpdate":
        if self.free_shipping_over_minor is not None and self.shipping_fee_minor == 0:
            raise ValueError("Free delivery over an amount needs a delivery charge to waive")
        return self
