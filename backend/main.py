from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId
import os
import logging
import io
import pandas as pd
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
        
        # Check for duplicates and prevent insertion
        items = parse_result['items']
        if items:
            # Check if similar file was already uploaded
            first_item = items[0]
            existing = await db.production_items.find_one({
                'source_file': file.filename,
                'order_number': first_item.get('order_number')
            })
            
            if existing:
                # Duplicate found - don't insert
                error_msg = f"Duplicate detected: File '{file.filename}' with order '{first_item.get('order_number')}' was already uploaded"
                logger.warning(error_msg)
                return FileUploadResponse(
                    success=False,
                    message="Duplicate file detected",
                    filename=file.filename,
                    total_items=0,
                    error=error_msg
                )
            
            # No duplicate - proceed with insertion
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
            items_preview=items_preview,
            ai_summary=parse_result.get('ai_summary')
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

@app.get("/api/statistics")
async def get_dashboard_statistics():
    """
    Get overall statistics for dashboard
    """
    try:
        # Get total counts
        total_items = await db.production_items.count_documents({})
        
        # Get status distribution
        status_pipeline = [
            {'$group': {'_id': '$status', 'count': {'$sum': 1}}}
        ]
        status_dist = await db.production_items.aggregate(status_pipeline).to_list(None)
        
        # Get source file distribution
        source_pipeline = [
            {'$group': {'_id': '$source_file', 'count': {'$sum': 1}}}
        ]
        source_dist = await db.production_items.aggregate(source_pipeline).to_list(None)
        
        # Get average quantity
        avg_pipeline = [
            {'$group': {'_id': None, 'avg_quantity': {'$avg': '$quantity'}}}
        ]
        avg_result = await db.production_items.aggregate(avg_pipeline).to_list(None)
        avg_quantity = avg_result[0]['avg_quantity'] if avg_result else 0
        
        return {
            'total_items': total_items,
            'by_status': {item['_id']: item['count'] for item in status_dist},
            'by_source': {item['_id']: item['count'] for item in source_dist},
            'average_quantity': round(avg_quantity, 2) if avg_quantity else 0
        }
    except Exception as e:
        logger.error(f"Error fetching statistics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/upload-history")
async def get_upload_history(limit: int = 10):
    """
    Get upload history
    """
    try:
        # Get unique source files with upload info
        pipeline = [
            {'$group': {
                '_id': '$source_file',
                'first_upload': {'$min': '$uploaded_at'},
                'last_upload': {'$max': '$uploaded_at'},
                'item_count': {'$sum': 1}
            }},
            {'$sort': {'last_upload': -1}},
            {'$limit': limit}
        ]
        
        history = await db.production_items.aggregate(pipeline).to_list(None)
        
        formatted_history = []
        for entry in history:
            formatted_history.append({
                'filename': entry['_id'],
                'first_upload': entry['first_upload'].isoformat() if entry['first_upload'] else None,
                'last_upload': entry['last_upload'].isoformat() if entry['last_upload'] else None,
                'item_count': entry['item_count']
            })
        
        return {'history': formatted_history, 'total': len(formatted_history)}
    except Exception as e:
        logger.error(f"Error fetching upload history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/export")
async def export_to_excel(
    style: Optional[str] = None,
    status: Optional[str] = None
):
    """
    Export production items to Excel file
    """
    try:
        # Build query filter
        query = {}
        if style:
            query['style'] = {'$regex': style, '$options': 'i'}
        if status:
            query['status'] = status
        
        # Get all matching items
        items = await db.production_items.find(query).to_list(length=None)
        
        if not items:
            raise HTTPException(status_code=404, detail="No items found to export")
        
        # Prepare data for Excel
        export_data = []
        for item in items:
            export_data.append({
                'Order Number': item.get('order_number', ''),
                'Style': item.get('style', ''),
                'Fabric': item.get('fabric', ''),
                'Color': item.get('color', ''),
                'Quantity': item.get('quantity', ''),
                'Shipping Date': item.get('shipping_date', ''),
                'Status': item.get('status', ''),
                'Source File': item.get('source_file', ''),
                'Uploaded At': item.get('uploaded_at', '').isoformat() if isinstance(item.get('uploaded_at'), datetime) else item.get('uploaded_at', '')
            })
        
        # Create Excel file
        df = pd.DataFrame(export_data)
        
        # Write to bytes buffer
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Production Items')
        output.seek(0)
        
        # Generate filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"production_items_{timestamp}.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/batch-upload")
async def batch_upload(files: List[UploadFile] = File(...)):
    """
    Upload and parse multiple Excel files at once
    """
    results = []
    
    for file in files:
        try:
            # Validate file type
            if not file.filename.endswith(('.xlsx', '.xls')):
                results.append({
                    'filename': file.filename,
                    'success': False,
                    'error': 'Invalid file type'
                })
                continue
            
            # Parse file
            content = await file.read()
            parser = ExcelParser()
            parse_result = parser.parse_bytes(content, file.filename)
            
            if parse_result['success']:
                # Insert items
                items = parse_result['items']
                if items:
                    for item in items:
                        item['created_at'] = datetime.utcnow()
                        item['updated_at'] = datetime.utcnow()
                    
                    await db.production_items.insert_many(items)
                
                results.append({
                    'filename': file.filename,
                    'success': True,
                    'items_count': len(items),
                    'ai_summary': parse_result.get('ai_summary')
                })
            else:
                results.append({
                    'filename': file.filename,
                    'success': False,
                    'error': parse_result.get('error', 'Unknown error')
                })
                
        except Exception as e:
            logger.error(f"Error processing {file.filename}: {str(e)}")
            results.append({
                'filename': file.filename,
                'success': False,
                'error': str(e)
            })
    
    successful = sum(1 for r in results if r['success'])
    total_items = sum(r.get('items_count', 0) for r in results if r['success'])
    
    return {
        'results': results,
        'summary': {
            'total_files': len(files),
            'successful': successful,
            'failed': len(files) - successful,
            'total_items_parsed': total_items
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
