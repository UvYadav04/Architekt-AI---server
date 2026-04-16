# ⚙️ ArchitektAI — Server

ArchitektAI (server) is a **multi-agent AI backend system** that generates structured system designs from high-level product ideas.

It orchestrates multiple specialized agents to **plan, construct, evaluate, and refine architectures**, enabling scalable, context-aware, and iterative system design generation.

---

## ✨ Key Features

### 🤖 Multi-Agent Architecture
- Built using **5 specialized agents working in coordination**:
  - **Planner** → Decomposes the problem and defines system structure  
  - **Synthesizer** → Builds relationships between components  
  - **Graph Designer** → Structures architecture as a graph  
  - **Evaluator** → Validates system design decisions  
  - **Evaluation Loop** → Iteratively refines outputs  

---

### 🧠 Intelligent System Design Generation
- Converts high-level ideas into:
  - Architecture design
  - Component breakdown
  - Data flow and interactions
- Produces structured and logically consistent outputs

---

### 🔄 Iterative Agent Loop
- Multi-agent refinement loop to:
  - Improve design quality
  - Resolve inconsistencies
  - Optimize architecture decisions
- Ensures higher-quality output than single-pass systems

---

### 📊 Graph-Based Architecture Modeling
- Represents systems as structured graphs
- Captures:
  - Service relationships  
  - Dependencies  
  - Data flow  

---

### 🔍 Efficient Context Retrieval
- Uses **Qdrant (vector database)** for similarity search
- Fetches only:
  - Relevant documents  
  - Relevant chat history  
- Reduces:
  - Token usage  
  - LLM response latency  

---

### 💬 Context-Aware Chat per Design
- Each design includes a chat assistant
- Supports:
  - Explaining architecture  
  - Assisting in development decisions  
  - Iterative improvements  

---

### 🗄️ Persistent Storage
- Stores system designs in **MongoDB**
- Enables:
  - Retrieval of previous designs  
  - Continuous refinement  

---

### ⚡ Asynchronous Processing
- Built with **FastAPI (async)**
- Handles:
  - Multi-agent workflows  
  - Concurrent requests  
- Ensures non-blocking execution

---

### 🧱 Structured Backend Design
- Class-based modular architecture
- Uses **Singleton pattern** for shared resources:
  - LLM instances  
  - Vector DB connections  
- Optimizes memory and performance

---

### 🔄 Robust Error Handling
- Handles failures inside agent loops
- Prevents cascading failures
- Maintains stable execution flow

---


---

## 🛠️ Tech Stack

- **Python**
- **FastAPI**
- **Uvicorn**
- **LangChain**
- **Qdrant (Vector Database)**
- **MongoDB**
- **Asyncio**

---

## 🔁 Core Workflow

### Design Generation
- Accept system idea  
- Planner defines structure  
- Synthesizer builds relationships  
- Graph designer constructs architecture  
- Evaluator validates design  
- Loop refines output  

---

### Context Optimization
- Retrieve only relevant:
  - Documents  
  - Chat history  
- Use vector similarity (Qdrant)  
- Reduce token usage and improve speed  

---

### Interaction Layer
- User interacts with generated system design  
- Chat assistant:
  - Explains architecture  
  - Suggests improvements  
  - Guides development  

---

## ▶️ Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/UvYadav04/Architekt-AI---server
cd Architekt-AI---server

python -m venv venv
source venv/bin/activate   # Linux / Mac
venv\Scripts\activate

pip install -r requirements.txt

uvicorn main:app --reload
