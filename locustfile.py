from locust import HttpUser, task, between

import uuid

class APIUser(HttpUser):
    # Base URL for your running API
    host = "http://localhost:8000"
    
    # Wait 1 to 5 seconds between tasks
    wait_time = between(1, 5)

    @task(1)
    def health_check(self):
        """Simulate a user hitting the healthcheck endpoint."""
        self.client.get("/api/v1/health")

    @task(5) # This task has a weight of 5, so it runs 5x more often
    def simulate_rag_query(self):
        """Simulate a user sending a query to the agent."""
        # Generate a unique session ID for every request to avoid LangGraph thread locking
        unique_session = str(uuid.uuid4())
        
        self.client.post("/api/v1/agent/chat", json={
            "query": "What is multi-head attention?",
            "session_id": unique_session
        })
