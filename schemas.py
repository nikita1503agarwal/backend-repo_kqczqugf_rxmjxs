"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user"
    """
    username: str = Field(..., min_length=3, max_length=32)
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="E.164 phone number like +15551234567")
    password_hash: str = Field(..., description="BCrypt hash of the user's password")
    name: Optional[str] = Field(None, description="Full name")
    is_active: bool = Field(True, description="Whether user is active")
    is_admin: bool = Field(False, description="Admin privileges")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product"
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    image: Optional[str] = Field(None, description="Image URL")
    rating: Optional[float] = Field(4.5, ge=0, le=5)
    rating_count: Optional[int] = Field(0, ge=0)
    in_stock: bool = Field(True, description="Whether product is in stock")

class Category(BaseModel):
    """Categories collection schema (name unique)"""
    name: str = Field(...)
    slug: str = Field(...)

class OrderItem(BaseModel):
    product_id: str
    title: str
    price: float
    quantity: int
    image: Optional[str] = None

class Order(BaseModel):
    """Orders collection schema"""
    user_id: str
    items: List[OrderItem]
    total: float
    address: str
    status: str = Field("placed")
