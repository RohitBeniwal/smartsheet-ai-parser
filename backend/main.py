from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId
import os
import logging
from contextlib import asynccontextmanager

from parser import ExcelParser
from parser.learning import ParserLearning
from models import (
    ProductionItemResponse,
    FileUploadResponse,
    ProductionItemsListResponse
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection
# For local development without auth enforcement: mongodb://localhost:27017/production
# For production with auth: mongodb://admin:pass1234@localhost:27017/production?authSource=admin
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/production")
client: Optional[AsyncIOMotorClient] = None
db = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global client, db
    try:
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client.production
        await client.server_info()  # Test connection
        logger.info("Connected to MongoDB successfully")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")

    yield

    # Shutdown
    if client:
        client.close()
        logger.info("Disconnected from MongoDB")

# Create FastAPI app
app = FastAPI(
    title="Production Planning Parser API",
    description="API for parsing and managing production planning data",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Production Planning Parser API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check MongoDB connection
        if client:
            await client.server_info()
            mongo_status = "connected"
        else:
            mongo_status = "disconnected"
    except:
        mongo_status = "error"

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "mongodb": mongo_status
    }

@app.post("/api/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload and parse production planning sheet
    """
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an Excel file (.xlsx or .xls)"
        )
    
    try:
        # Read file content
        content = await file.read()
        
        # Parse the Excel file
        parser = ExcelParser()
        parse_result = parser.parse_bytes(content, file.filename)
        
        if not parse_result['success']:
            return FileUploadResponse(
                success=False,
                message="Failed to parse file",
                filename=file.filename,
                total_items=0,
                error=parse_result.get('error', 'Unknown error')
            )
        
        # Insert items into MongoDB
        items = parse_result['items']
        if items:
            # Add created_at and updated_at timestamps
            for item in items:
                item['created_at'] = datetime.utcnow()
                item['updated_at'] = datetime.utcnow()
            
            result = await db.production_items.insert_many(items)
            logger.info(f"Inserted {len(result.inserted_ids)} items into MongoDB")
        
        # Return preview of first 3 items
        items_preview = []
        for item in items[:3]:
            preview = {
                "order_number": item.get('order_number'),
                "style": item.get('style'),
                "color": item.get('color'),
                "quantity": item.get('quantity'),
                "status": item.get('status')
            }
            items_preview.append(preview)
        
        return FileUploadResponse(
            success=True,
            message=f"Successfully parsed and stored {len(items)} items",
            filename=file.filename,
            total_items=len(items),
            items_preview=items_preview
        )
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )

@app.get("/api/production-items")
async def get_production_items(
    skip: int = 0,
    limit: int = 100,
    style: Optional[str] = None,
    status: Optional[str] = None
):
    """
    Get production line items with optional filtering
    """
    try:
        # Build query filter
        query = {}
        if style:
            query['style'] = {'$regex': style, '$options': 'i'}
        if status:
            query['status'] = status
        
        # Get total count
        total = await db.production_items.count_documents(query)
        
        # Get items with pagination
        cursor = db.production_items.find(query).skip(skip).limit(limit).sort('created_at', -1)
        items = await cursor.to_list(length=limit)
        
        # Format items for response
        formatted_items = []
        for item in items:
            formatted_item = {
                "id": str(item['_id']),
                "order_number": item.get('order_number'),
                "style": item.get('style'),
                "fabric": item.get('fabric'),
                "color": item.get('color'),
                "quantity": item.get('quantity'),
                "shipping_date": item.get('shipping_date'),
                "status": item.get('status', 'pending'),
                "milestones": item.get('milestones', {}),
                "source_file": item.get('source_file'),
                "uploaded_at": item.get('uploaded_at', datetime.utcnow()).isoformat(),
                "created_at": item.get('created_at', datetime.utcnow()).isoformat(),
                "updated_at": item.get('updated_at', datetime.utcnow()).isoformat()
            }
            formatted_items.append(formatted_item)
        
        return {
            "items": formatted_items,
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error fetching production items: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching items: {str(e)}"
        )

@app.get("/api/production-items/{item_id}")
async def get_production_item(item_id: str):
    """
    Get a specific production item by ID
    """
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(item_id):
            raise HTTPException(status_code=400, detail="Invalid item ID")
        
        item = await db.production_items.find_one({"_id": ObjectId(item_id)})
        
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        
        # Format response
        return {
            "id": str(item['_id']),
            "order_number": item.get('order_number'),
            "style": item.get('style'),
            "fabric": item.get('fabric'),
            "color": item.get('color'),
            "quantity": item.get('quantity'),
            "shipping_date": item.get('shipping_date'),
            "status": item.get('status', 'pending'),
            "milestones": item.get('milestones', {}),
            "source_file": item.get('source_file'),
            "uploaded_at": item.get('uploaded_at', datetime.utcnow()).isoformat(),
            "created_at": item.get('created_at', datetime.utcnow()).isoformat(),
            "updated_at": item.get('updated_at', datetime.utcnow()).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching item: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching item: {str(e)}"
        )

@app.delete("/api/production-items/{item_id}")
async def delete_production_item(item_id: str):
    """
    Delete a production item
    """
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(item_id):
            raise HTTPException(status_code=400, detail="Invalid item ID")
        
        result = await db.production_items.delete_one({"_id": ObjectId(item_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")
        
        return {
            "message": f"Item {item_id} deleted successfully",
            "id": item_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting item: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting item: {str(e)}"
        )

@app.post("/api/learn-pattern")
async def learn_pattern(
    column_name: str,
    standard_field: str,
    source_file: Optional[str] = None
):
    """
    Teach the parser a new column name pattern
    """
    try:
        learning = ParserLearning(db)
        is_new = await learning.learn_pattern(column_name, standard_field, source_file)
        
        return {
            "success": True,
            "is_new": is_new,
            "column_name": column_name,
            "standard_field": standard_field,
            "message": "Pattern learned successfully" if is_new else "Pattern already known"
        }
    except Exception as e:
        logger.error(f"Error learning pattern: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/learned-patterns")
async def get_learned_patterns(standard_field: Optional[str] = None):
    """
    Get learned patterns
    """
    try:
        learning = ParserLearning(db)
        
        if standard_field:
            patterns = await learning.get_learned_patterns(standard_field)
            return {"standard_field": standard_field, "patterns": patterns}
        else:
            patterns = await learning.get_all_learned_patterns()
            return {"patterns": patterns}
    except Exception as e:
        logger.error(f"Error fetching learned patterns: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/parser-statistics")
async def get_parser_statistics():
    """
    Get statistics about parser learning
    """
    try:
        learning = ParserLearning(db)
        stats = await learning.get_pattern_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error fetching statistics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
