from locust import HttpUser, task, between
import time

class NormalUser(HttpUser):
    """Simulates users making a mix of quick and slow requests."""
    wait_time = between(1, 3)

    @task(3)
    def light_request(self):
        """Quick page load."""
        self.client.get("/", name="Light Request")

    @task(1)
    def heavy_request(self):
        """Slower request — simulates processing."""
        self.client.get("/?heavy=true", name="Heavy Request")
        time.sleep(0.5)
