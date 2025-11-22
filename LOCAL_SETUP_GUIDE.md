# Local Development Environment - Quick Reference

## ✅ Current Status

Your local environment is **fully operational**:

- ✅ **MongoDB**: Running on `localhost:27017` (without auth enforcement for local dev)
- ✅ **Backend API**: Running on `http://localhost:8000`
- ✅ **Frontend**: Running on `http://localhost:3000`
- ✅ **Parser**: Tested and working with all 3 sample files
- ✅ **Database**: 12 items already loaded from `tna-uno.xlsx`

## 🚀 Quick Access

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend App | http://localhost:3000 | Main dashboard interface |
| Backend API | http://localhost:8000 | REST API endpoints |
| API Docs | http://localhost:8000/docs | Interactive API documentation |
| Health Check | http://localhost:8000/health | System health status |

## 🔧 Managing Services

### Check Service Status
```bash
# Check if MongoDB is running
brew services list | grep mongodb

# Check if backend is running
ps aux | grep "uvicorn main:app" | grep -v grep

# Check if frontend is running
ps aux | grep "npm start" | grep -v grep
```

### Start Services (if stopped)
```bash
# Start MongoDB
brew services start mongodb/brew/mongodb-community@7.0

# Start Backend (from backend directory)
cd backend
nohup python3 -m uvicorn main:app --reload --port 8000 > backend.log 2>&1 &

# Start Frontend (from frontend directory)
cd frontend
nohup npm start > frontend.log 2>&1 &
```

### Stop Services
```bash
# Stop MongoDB
brew services stop mongodb/brew/mongodb-community@7.0

# Stop Backend
pkill -f "uvicorn main:app"

# Stop Frontend
pkill -f "npm start"
```

### View Logs
```bash
# Backend logs
tail -f backend/backend.log

# Frontend logs
tail -f frontend/frontend.log
```

## 📊 Testing the Application

### 1. Using the Web Interface
1. Open browser: http://localhost:3000
2. Click "Upload Production Sheet"
3. Select one of the sample files from `data/` directory
4. View parsed data in the dashboard

### 2. Using API Directly

**Upload a file:**
```bash
curl -X POST "http://localhost:8000/api/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@data/tna-dos.xlsx"
```

**Get all items:**
```bash
curl http://localhost:8000/api/production-items | python3 -m json.tool
```

**Get specific item:**
```bash
# Replace {id} with actual MongoDB ObjectId from previous response
curl http://localhost:8000/api/production-items/{id} | python3 -m json.tool
```

### 3. Test Parser Standalone
```bash
cd backend
python3 test_parser.py
```

## 🗄️ MongoDB Commands

### Access MongoDB Shell
```bash
mongosh production
```

### Common MongoDB Operations
```javascript
// Count documents
db.production_items.countDocuments()

// Find all items
db.production_items.find().limit(5).pretty()

// Find by style
db.production_items.find({style: "8GE4S1V2Q"}).pretty()

// Find by status
db.production_items.find({status: "completed"}).pretty()

// Clear all data (if needed)
db.production_items.deleteMany({})

// Drop collection (if needed)
db.production_items.drop()
```

## 📁 Sample Files for Testing

Location: `data/` directory

1. **tna-uno.xlsx** - Nike Fall 2025 (12 items, 4 milestones)
2. **tna-dos.xlsx** - Adidas Fall 2025 (12 items, 5 milestones)
3. **tna-tres.xlsx** - Under Armour Fall 2025 (12 items, 4 milestones)

## 🔍 Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is already in use
lsof -i :8000

# Kill process if needed
kill -9 <PID>

# Check backend logs
tail -50 backend/backend.log
```

### Frontend won't start
```bash
# Check if port 3000 is already in use
lsof -i :3000

# Kill process if needed
kill -9 <PID>

# Check frontend logs
tail -50 frontend/frontend.log
```

### MongoDB connection issues
```bash
# Verify MongoDB is running
brew services list | grep mongodb

# Test MongoDB connection
mongosh --eval "db.adminCommand('ping')"

# Restart MongoDB
brew services restart mongodb/brew/mongodb-community@7.0
```

### Data not showing in frontend
```bash
# Check if backend can reach MongoDB
curl http://localhost:8000/health

# Check if data exists in MongoDB
mongosh production --eval "db.production_items.countDocuments()"

# Check browser console for errors (F12 in most browsers)
```

## 🔐 Authentication Note

**Current Setup:** MongoDB is running **without** authentication enforcement for local development convenience.

**Connection String:** `mongodb://localhost:27017/production`

**For Production:** You would enable auth and use:
`mongodb://admin:pass1234@localhost:27017/production?authSource=admin`

To enable authentication:
1. Stop MongoDB: `brew services stop mongodb/brew/mongodb-community@7.0`
2. Edit config: `/opt/homebrew/etc/mongod.conf`
3. Add:
   ```yaml
   security:
     authorization: enabled
   ```
4. Restart MongoDB
5. Update `MONGODB_URL` in `backend/main.py` or set environment variable

## 📝 Development Workflow

### Making Code Changes

**Backend changes:**
- Edit files in `backend/`
- Server auto-reloads (watch logs: `tail -f backend/backend.log`)

**Frontend changes:**
- Edit files in `frontend/src/`
- Browser auto-refreshes

**Parser changes:**
- Edit files in `backend/parser/`
- Test with: `cd backend && python3 test_parser.py`

### Adding New Features

1. Stop services
2. Make code changes
3. Restart services
4. Test changes
5. Commit to git

## 📚 Additional Resources

- **Implementation Details:** See `IMPLEMENTATION.md`
- **Project README:** See `README.md`
- **API Documentation:** http://localhost:8000/docs (when backend is running)

## 💡 Quick Tips

1. **Reset Everything:**
   ```bash
   # Clear MongoDB
   mongosh production --eval "db.production_items.deleteMany({})"
   
   # Restart backend (auto-reloads anyway)
   pkill -f "uvicorn main:app"
   cd backend && nohup python3 -m uvicorn main:app --reload --port 8000 > backend.log 2>&1 &
   ```

2. **Upload All Sample Files:**
   ```bash
   for file in data/*.xlsx; do
     curl -X POST "http://localhost:8000/api/upload" \
       -H "Content-Type: multipart/form-data" \
       -F "file=@$file"
     sleep 1
   done
   ```

3. **Check Everything is Running:**
   ```bash
   echo "MongoDB: $(brew services list | grep mongodb | awk '{print $2}')"
   echo "Backend: $(curl -s http://localhost:8000/health | python3 -c 'import sys, json; print(json.load(sys.stdin)["mongodb"])')"
   echo "Frontend: $(curl -s http://localhost:3000 > /dev/null && echo 'running' || echo 'stopped')"
   ```

---

**Last Updated:** November 22, 2025

**Environment:** macOS with Homebrew, Python 3, Node.js
