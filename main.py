import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId
from passlib.hash import bcrypt

from database import db, create_document, get_documents
from schemas import User, Product, Category, Order, OrderItem

app = FastAPI(title="Amazons API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Amazons backend running"}

# ---------- Auth Models ----------
class SignupRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None

class LoginRequest(BaseModel):
    username: Optional[str] = None
    phone: Optional[str] = None
    password: str

# ---------- Helpers ----------
def to_str_id(doc):
    if doc is None:
        return doc
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d

# ---------- Auth Endpoints ----------
@app.post("/auth/signup")
def signup(payload: SignupRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    if not payload.username or not payload.password:
        raise HTTPException(status_code=400, detail="Username and password required")

    # Ensure unique username/phone/email
    existing = db["user"].find_one({
        "$or": [
            {"username": payload.username},
            {"phone": payload.phone} if payload.phone else {},
            {"email": payload.email} if payload.email else {}
        ]
    })
    if existing:
        raise HTTPException(status_code=409, detail="Account already exists")

    password_hash = bcrypt.hash(payload.password)
    user_doc = User(
        username=payload.username,
        email=payload.email,
        phone=payload.phone,
        password_hash=password_hash,
        name=payload.name,
    ).model_dump()

    user_id = db["user"].insert_one(user_doc).inserted_id
    return {"id": str(user_id), "username": payload.username}

@app.post("/auth/login")
def login(payload: LoginRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    if not payload.password:
        raise HTTPException(status_code=400, detail="Password required")

    query = {}
    if payload.username:
        query["username"] = payload.username
    if payload.phone:
        query["phone"] = payload.phone
    if not query:
        raise HTTPException(status_code=400, detail="Provide username or phone")

    user = db["user"].find_one(query)
    if not user or not bcrypt.verify(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"id": str(user["_id"]), "username": user.get("username"), "name": user.get("name")}

# ---------- Catalog Endpoints ----------
@app.get("/categories")
def list_categories():
    cats = list(db["category"].find()) if db else []
    return [to_str_id(c) for c in cats]

class CreateCategory(BaseModel):
    name: str
    slug: str

@app.post("/categories")
def create_category(payload: CreateCategory):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    if db["category"].find_one({"slug": payload.slug}):
        raise HTTPException(status_code=409, detail="Category exists")
    _id = db["category"].insert_one(payload.model_dump()).inserted_id
    return {"id": str(_id)}

@app.get("/products")
def list_products(q: Optional[str] = None, category: Optional[str] = None, limit: int = 20, skip: int = 0):
    if db is None:
        return []
    filt = {}
    if q:
        filt["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    if category:
        filt["category"] = category

    cursor = db["product"].find(filt).skip(skip).limit(limit)
    return [to_str_id(p) for p in cursor]

@app.get("/products/{product_id}")
def get_product(product_id: str):
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    prod = db["product"].find_one({"_id": oid}) if db else None
    if not prod:
        raise HTTPException(status_code=404, detail="Not found")
    return to_str_id(prod)

class CreateProduct(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    image: Optional[str] = None

@app.post("/products")
def create_product(payload: CreateProduct):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    prod = Product(**payload.model_dump()).model_dump()
    _id = db["product"].insert_one(prod).inserted_id
    return {"id": str(_id)}

# ---------- Orders ----------
class CheckoutRequest(BaseModel):
    user_id: str
    items: List[OrderItem]
    address: str

@app.post("/orders/checkout")
def checkout(payload: CheckoutRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    total = sum(item.price * item.quantity for item in payload.items)
    order_doc = Order(
        user_id=payload.user_id,
        items=payload.items,
        total=total,
        address=payload.address,
    ).model_dump()

    _id = db["order"].insert_one(order_doc).inserted_id
    return {"order_id": str(_id), "total": total, "status": "placed"}

# ---------- Seed Data ----------
@app.post("/seed")
def seed():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    base_categories = [
        {"name": "Electronics", "slug": "electronics"},
        {"name": "Books", "slug": "books"},
        {"name": "Home", "slug": "home"},
        {"name": "Fashion", "slug": "fashion"},
    ]
    for c in base_categories:
        if not db["category"].find_one({"slug": c["slug"]}):
            db["category"].insert_one(c)

    sample_products = [
        {"title": "Noise-Canceling Headphones", "description": "Over-ear, Bluetooth 5.3, 30h battery", "price": 129.99, "category": "Electronics", "image": "https://images.unsplash.com/photo-1517495306984-937bcd3c5b86"},
        {"title": "Smartphone Stand", "description": "Adjustable aluminum desk stand", "price": 19.99, "category": "Electronics", "image": "https://images.unsplash.com/photo-1510557880182-3d4d3cba35a5"},
        {"title": "Bestselling Novel", "description": "Paperback, 352 pages", "price": 12.49, "category": "Books", "image": "https://images.unsplash.com/photo-1512820790803-83ca734da794"},
        {"title": "Cozy Throw Blanket", "description": "Ultra-soft microfiber, 50x60", "price": 24.95, "category": "Home", "image": "https://images.unsplash.com/photo-1499933374294-4584851497cc"},
        {"title": "Classic T-Shirt", "description": "100% cotton, unisex fit", "price": 14.99, "category": "Fashion", "image": "https://images.unsplash.com/photo-1512436991641-6745cdb1723f"},
    ]

    for p in sample_products:
        if not db["product"].find_one({"title": p["title"]}):
            db["product"].insert_one(Product(**p).model_dump())

    # Create a demo user if none
    if not db["user"].find_one({"username": "demo"}):
        db["user"].insert_one(User(username="demo", email="demo@example.com", phone=None, password_hash=bcrypt.hash("demo123"), name="Demo User").model_dump())

    return {"status": "seeded"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available" if db is None else "✅ Connected",
    }
    if db is not None:
        response["collections"] = db.list_collection_names()
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
