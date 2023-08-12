import random
import string

from locust import HttpUser, task


def get_random_text(length: int = 12):
    return "".join(random.choice(string.ascii_lowercase) for i in range(length))


class InfersUser(HttpUser):
    @task
    def post_infer(self):
        self.client.post("/api/v1/infer", json={"text": get_random_text()})
