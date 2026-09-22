import os

from locust import HttpUser, between, task


class RTKUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self) -> None:
        response = self.client.post(
            "/api/auth/login",
            json={
                "email": os.getenv("RTK_TEST_EMAIL", "kam@rtk.ru"),
                "password": os.getenv("RTK_TEST_PASSWORD", "kam123"),
            },
            name="POST /api/auth/login",
        )
        if response.status_code == 200:
            token = response.json().get("access_token")
            if token:
                self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task(3)
    def view_reports(self) -> None:
        self.client.get("/api/reports", name="GET /api/reports")

    @task(2)
    def view_board(self) -> None:
        self.client.get(
            "/api/interactions/board",
            name="GET /api/interactions/board",
        )

    @task(1)
    def view_stages(self) -> None:
        self.client.get(
            "/api/stages?include_inactive=true",
            name="GET /api/stages",
        )

    @task(1)
    def view_directories(self) -> None:
        self.client.get("/api/universities", name="GET /api/universities")
        self.client.get("/api/products", name="GET /api/products")
