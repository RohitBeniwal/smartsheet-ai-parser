"""
Pydantic models for production items
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)
    
    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        return {"type": "string"}


class MilestoneData(BaseModel):
    """Data for a single milestone"""
    plan_date: Optional[str] = None
    quantity: Optional[float] = None
    supplier: Optional[str] = None
    required_weight: Optional[float] = None
    plan: Optional[str] = None
    
    class Config:
        extra = "allow"  # Allow additional fields


class ProductionItemBase(BaseModel):
    """Base model for production items"""
    order_number: Optional[str] = None
    style: Optional[str] = None
    fabric: Optional[str] = None
    color: Optional[str] = None
    quantity: Optional[float] = None
    shipping_date: Optional[str] = None
    milestones: Optional[Dict[str, MilestoneData]] = Field(default_factory=dict)
    status: str = "pending"
    source_file: str
    custom_fields: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ProductionItemCreate(ProductionItemBase):
    """Model for creating a production item"""
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class ProductionItemInDB(ProductionItemBase):
    """Model for production item in database"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    uploaded_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}


class ProductionItemResponse(BaseModel):
    """Model for API response"""
    id: str
    order_number: Optional[str] = None
    style: Optional[str] = None
    fabric: Optional[str] = None
    color: Optional[str] = None
    quantity: Optional[float] = None
    shipping_date: Optional[str] = None
    milestones: Optional[Dict[str, Dict[str, Any]]] = Field(default_factory=dict)
    status: str
    source_file: str
    uploaded_at: str
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class FileUploadResponse(BaseModel):
    """Response model for file upload"""
    success: bool
    message: str
    filename: str
    total_items: int
    items_preview: Optional[List[Dict[str, Any]]] = None
    ai_summary: Optional[str] = None
    error: Optional[str] = None


class ProductionItemsListResponse(BaseModel):
    """Response model for listing production items"""
    items: List[ProductionItemResponse]
    total: int
    skip: int
    limit: int
