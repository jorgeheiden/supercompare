from pydantic import BaseModel
from typing import List, Optional

class Product(BaseModel):
    name: str
    price: float
    original_price: Optional[float] = None
    image_url: Optional[str] = None
    unit: Optional[str] = None
    brand: Optional[str] = None
    is_on_sale: bool = False
    discount_percent: Optional[int] = None
    product_url: Optional[str] = None
    supermarket: str

class SearchResult(BaseModel):
    query: str
    dia: List[Product]
    coto: List[Product]
