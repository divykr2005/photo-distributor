# Architecture

## Overall Architecture
The system consists of a frontend portal, a backend API, a background worker for processing images, and an AI service for face recognition.

## Component Diagram
- Frontend Client
- Backend API
- Database (PostgreSQL + pgvector)
- Cache/Message Queue (Redis)
- AI Service (InsightFace)
- Worker (Celery)
- Storage (S3)

## Data Flow
1. Guest registers with a selfie.
2. Photographer uploads event photos.
3. Worker extracts faces using AI Service.
4. Matches are found via vector similarity.
5. Notifications are dispatched to matched guests.
