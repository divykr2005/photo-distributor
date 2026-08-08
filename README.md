# AI Event Photo Distribution

## Problem Statement
Distributing photos taken by photographers at events to the respective guests is a manual, tedious, and time-consuming process.

## Solution
An automated system that uses facial recognition to match event photos with registered guests and seamlessly delivers them via WhatsApp/SMS or a web gallery.

## Features
- Face Capture and Registration
- Event Management
- Automated Face Matching
- WhatsApp/SMS Notifications
- Gallery & ZIP Export
- Privacy-first approach

## Architecture
See [ARCHITECTURE.md](ARCHITECTURE.md)

## Tech Stack
- Frontend: React / Next.js
- Backend: FastAPI / Node.js
- AI Service: Python, InsightFace
- Database: PostgreSQL (with pgvector), Redis
- Worker: Celery

## Installation & Running Locally
See [DEPLOYMENT.md](DEPLOYMENT.md)

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md)

## License
MIT License
