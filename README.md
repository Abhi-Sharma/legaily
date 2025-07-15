# Legaily ⚖️ - AI-Powered Legal Assistance Platform

**Legaily** (Legal + AI) is a comprehensive web-based platform designed to simplify and streamline various legal processes using Artificial Intelligence. It enables lawyers, judges, and clients to manage legal documentation, translate case files, summarize legal texts, and efficiently track legal diaries — all in a user-friendly environment.

---

## 🚀 Features

- **Login & Signup Authentication**
    - Secure authentication system with JWT-based stateless session management.
    - Role-based access control (Judge and Lawyer views).

- **Doc AI Page**
    - Upload and summarize complex legal documents.
    - Translate documents into regional languages using AI-powered summarization models.

- **Advocate Diary**
    - Allows advocates to log daily matter entries.
    - Calendar-based visualizations with popup details on click.
    - Data persistence using local storage and pop-up notifications.

- **Drafts Page**
    - Save and manage draft documents efficiently.

- **Query Page (Chatbot)**
    - Legal chatbot integrated using LangChain, Huggingface embeddings, and FAISS vector database.
    - Provides quick and accurate answers based on Indian Penal Code laws.

- **Role-Specific Views**
    - Judge View and Lawyer View are accessible based on authenticated user role.

---

## 📂 Tech Stack

### Frontend:
- React.js
- React Router
- Streamlit (for chatbot interface)
- Tailwind CSS

### Backend:
- Node.js & Express.js
- MongoDB Atlas (Cloud database)
- Mongoose ODM
- JWT Authentication
- Bcrypt for password hashing

### AI & ML:
- LangChain with Huggingface InLegalBERT model
- FAISS for semantic search
- TogetherAI API for LLM-based question answering

---

## 📌 Project Structure

legaily/
│
├── legaily_backend/ # Backend Node.js Server (APIs, Auth)
├── src/ # React Frontend Source Code
├── public/ # Static Assets
├── README.md # Project Documentation
└── package.json # Project Configurations



## 🛠️ Installation

### Backend:
```bash
cd legaily_backend
npm install
node server.js

### Frontend:
cd legaily
npm install
npm start


Make sure to configure your .env file with:

MONGO_URI=your_mongodb_connection_string
JWT_SECRET=your_secret_key



💡 Contributions
This project was built collaboratively as part of an academic project:

Full-Stack Development: Login, Signup, Role-Based Routing

AI Integration: LangChain-based legal chatbot

Document AI Utilities: Summarization, Translation, Diary Management

UI Design: Clean, responsive front-end with role-specific dashboards.



🤝Acknowledgments
OpenAI for GPT-based assistance

Huggingface InLegalBERT model

TogetherAI API

LangChain community


