import os
import random

from locust import HttpUser, between, tag, task


class RTKUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self) -> None:
        self.interaction_id: int | None = None
        self.stage_id = 1
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
                self._load_interaction()

    def _load_interaction(self) -> None:
        response = self.client.get(
            "/api/interactions/board",
            name="GET /api/interactions/board (write setup)",
        )
        if response.status_code != 200:
            return
        for column in response.json().get("columns", []):
            interactions = column.get("interactions", [])
            if interactions:
                self.interaction_id = interactions[0].get("id")
                self.stage_id = interactions[0].get("stage_id", 1)
                return

    @task(3)
    def view_reports(self) -> None:
        self.client.get(
            "/api/reports",
            params=random.choice(
                [
                    {},
                    {"date_from": "2026-08-01", "date_to": "2026-09-30"},
                    {"stage_id": self.stage_id},
                    {"university_id": 1},
                    {"product_id": 1},
                ]
            ),
            name="GET /api/reports",
        )

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

    @task(2)
    @tag("write")
    def create_interaction(self) -> None:
        response = self.client.post(
            "/api/interactions",
            json={
                "university_id": random.randint(1, 5),
                "product_id": random.randint(1, 5),
                "stage_id": random.randint(1, 14),
            },
            name="POST /api/interactions",
        )
        if response.status_code == 201:
            self.interaction_id = response.json().get("id")

    @task(3)
    @tag("write")
    def move_interaction(self) -> None:
        if self.interaction_id is None:
            self._load_interaction()
        if self.interaction_id is None:
            return
        target_stage = random.choice(
            [stage for stage in range(1, 15) if stage != self.stage_id]
        )
        response = self.client.post(
            f"/api/interactions/{self.interaction_id}/move",
            params={"stage_id": target_stage},
            name="POST /api/interactions/{id}/move",
        )
        if response.status_code == 200:
            self.stage_id = target_stage

    @task(2)
    @tag("write")
    def add_comment(self) -> None:
        if self.interaction_id is None:
            self._load_interaction()
        if self.interaction_id is not None:
            self.client.post(
                f"/api/interactions/{self.interaction_id}/comments",
                json={"text": "Locust write test"},
                name="POST /api/interactions/{id}/comments",
            )

    @task(1)
    @tag("write")
    def upload_file(self) -> None:
        if self.interaction_id is None:
            self._load_interaction()
        if self.interaction_id is not None:
            self.client.post(
                f"/api/files/interactions/{self.interaction_id}/upload",
                files={
                    "file": (
                        "locust-test.png",
                        (
                            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
                            b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
                            b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00"
                            b"\x0cIDAT\x08\xd7c\xf8\xcf\xc0\xf0\x1f\x00"
                            b"\x05\x00\x01\xff\x89\x99=\x1d\x00\x00\x00\x00"
                            b"IEND\xaeB`\x82"
                        ),
                        "image/png",
                    )
                },
                name="POST /api/files/interactions/{id}/upload",
            )

    @task(1)
    @tag("export")
    def export_xlsx(self) -> None:
        self.client.get(
            "/api/reports/xlsx",
            params={"date_from": "2026-08-01", "date_to": "2026-09-30"},
            name="GET /api/reports/xlsx",
        )

    @task(1)
    @tag("export")
    def export_xls(self) -> None:
        self.client.get(
            "/api/reports/xls",
            params={"date_from": "2026-08-01", "date_to": "2026-09-30"},
            name="GET /api/reports/xls",
        )

    @task(1)
    @tag("export")
    def export_pdf(self) -> None:
        self.client.get(
            "/api/reports/pdf",
            params={"date_from": "2026-08-01", "date_to": "2026-09-30"},
            name="GET /api/reports/pdf",
        )


class StageAdminUser(HttpUser):
    """Профиль администратора для проверки PATCH этапа workflow."""

    wait_time = between(1, 3)

    def on_start(self) -> None:
        response = self.client.post(
            "/api/auth/login",
            json={
                "email": os.getenv("RTK_ADMIN_EMAIL", "admin@rtk.ru"),
                "password": os.getenv("RTK_ADMIN_PASSWORD", "admin123"),
            },
            name="POST /api/auth/login (admin)",
        )
        if response.status_code == 200:
            token = response.json().get("access_token")
            if token:
                self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task
    @tag("write")
    def toggle_stage(self) -> None:
        self.client.patch(
            "/api/stages/14",
            json={"color": "#08979c"},
            name="PATCH /api/stages/{id}",
        )


class ReportsUser(HttpUser):
    """Отдельный сценарий для параллельного построения отчётов."""

    weight = 1
    wait_time = between(0.5, 1.5)

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

    @task
    def build_report(self) -> None:
        variants = [
            {"date_from": "2026-08-01", "date_to": "2026-09-30"},
            {"university_id": 1},
            {"product_id": 1},
            {"stage_id": 5},
            {"date_from": "2026-09-01", "date_to": "2026-09-15"},
            {"direction_id": 1},
            {"assigned_kam_id": 3},
            {},
        ]
        self.client.get(
            "/api/reports",
            params=random.choice(variants),
            name="GET /api/reports (parallel)",
        )
