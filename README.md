# Memersala Flask Application - REST API Enhancement

## Original Author
Gadiel Zya T. Maramag, BSIT2-B1

## What I Added

### 1. REST API Implementation
Added a complete REST API layer that provides programmatic access to the application's post management features:

- `GET /api/posts`: List all posts with pagination
- `GET /api/posts/<filename>`: Get a specific post
- `POST /api/posts`: Create a new post
- `PATCH /api/posts/<filename>`: Update post caption
- `DELETE /api/posts/<filename>`: Delete a post

### 2. API Features
- Full CRUD operations for posts
- Authentication and authorization
- Proper error handling with status codes
- HATEOAS links for navigation
- JSON request/response format
- Swagger documentation at `/api/docs`

### 3. Testing Suite
Added comprehensive tests using pytest:
- Test coverage for all CRUD operations
- Authentication and authorization tests
- Error handling tests
- Both positive and negative test cases

### 4. Dependencies Added
Added new dependencies in requirements.txt:
- flask-restx: For API and Swagger documentation
- flask-cors: For CORS support
- pytest: For testing
- pytest-cov: For test coverage

## Original Features (Pre-existing)
- Upload memes/images functionality
- Basic user authentication
- Image display
- Chat functionality

## How to Access the API
The API documentation is available at `/api/docs` when running the application. All endpoints require authentication via session cookie. 