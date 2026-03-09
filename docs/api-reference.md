# API Documentation

## Authentication

All API endpoints require authentication via Bearer token in the Authorization header.

```
Authorization: Bearer <your_token>
```

## Endpoints

### GET /api/v1/users

Retrieve a list of users.

**Query Parameters:**
- `limit` (int, optional): Maximum number of users to return (default: 20)
- `offset` (int, optional): Number of users to skip (default: 0)

**Response:**
```json
{
  "users": [...],
  "total": 100,
  "limit": 20,
  "offset": 0
}
```

### POST /api/v1/users

Create a new user.

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "role": "user"
}
```

### GET /api/v1/projects

Retrieve all projects.

**Response:**
```json
{
  "projects": [
    {
      "id": 1,
      "name": "Project Alpha",
      "status": "active"
    }
  ]
}
```

## Error Codes

- 200: Success
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 500: Internal Server Error
