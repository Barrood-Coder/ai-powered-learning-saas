# AI-Powered Adaptive Learning Platform (SaaS Backend)

A full-stack, enterprise-grade educational SaaS platform built with **Flask**, **SQLAlchemy**, and integrated with **Google Gemini Pro API**. The system features an AI-driven adaptive learning engine that diagnoses student mathematical weaknesses and dynamically generates customized practice workloads.

## 🚀 Key Architectural Features
- **Generative AI Integration**: Seamlessly integrated with **Gemini LLM** via a scalable configurations wrapper to automatically construct tailored mathematics problem sets with structured json schemas (answers & structural explanations).
- **Hardened Web Security Middleware**: Implemented dynamic security headers enforcing `HSTS (Strict-Transport-Security)`, `X-Frame-Options (DENY)`, and `X-XSS-Protection` alongside comprehensive exception fallback handling for user session security.
- **Adaptive Weakness Tracking (Data Modeling)**：Engineered relational database tracking (`StudentWeakness`, `AISession`, `PracticeResult`) to dynamically compute student accuracy matrices, generating a real-time behavioral diagnostics dashboard.
- **Robust Session Lifecycle Management**: Formulated zero-trust route decorators (`@student_login_required`) with active state verification to prevent session pollution and unauthorized data leakage.

## 🛠️ Tech Stack & Architecture
- **Backend Framework**: Flask (Python)
- **Database ORM**: Flask-SQLAlchemy (PostgreSQL / MySQL / SQLite compatible)
- **AI Engine**: Google Gemini API (Generative AI Wrapper)
- **Security**: Custom Security Header Middleware, CSRF Exceptions for API Endpoints
- **Data Structuring**: In-memory JSON Parsing (`json.loads`) for high-speed dynamic state management
