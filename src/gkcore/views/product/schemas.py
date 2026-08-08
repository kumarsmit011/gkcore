from pydantic import BaseModel, ValidationInfo, confloat, model_validator
from typing import Optional, Dict, Any, Literal
from typing_extensions import Self

from gkcore.views.product.services import (
    check_duplicate_item_account_name, check_duplicate_item_name
)


class GodownStock(BaseModel):
    qty: Optional[float] = None
    rate: Optional[float] = None


class ProductDetail(BaseModel):
    amountdiscount: Optional[confloat(ge=0)] = 0
    categorycode: Optional[int] = None
    gscode: Optional[str] = None
    gsflag: Literal[7, 19]
    openingstock: Optional[float] = 0.0
    percentdiscount: Optional[confloat(ge=0, le=100)] = 0
    prodmrp: Optional[confloat(ge=0)] = 0
    productdesc: str
    prodsp: Optional[confloat(ge=0)] = 0
    specs: Optional[Dict[str, Any]] = None
    uomid: Optional[int] = None


class ProductGodown(BaseModel):
    productdetails: ProductDetail
    godownflag: Optional[bool] = None
    godetails: Optional[Dict[int, GodownStock]] = None

    @model_validator(mode="after")
    def validate_productdesc(self, info: ValidationInfo) -> Self:
        check_duplicate_item_name(
             self.productdetails.productdesc,
             info.context["orgcode"],
             getattr(self.productdetails, "productcode", None),
        )
        check_duplicate_item_account_name(
             self.productdetails.productdesc,
             info.context["orgcode"],
             getattr(self.productdetails, "productcode", None),
        )
        return self


class ProductDetailUpdate(ProductDetail):
    productcode: int


class ProductGodownUpdate(ProductGodown):
    productdetails: ProductDetailUpdate
