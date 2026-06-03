"""ServiceNow integration — creates and updates tickets.

VERSION 1 (this file): a STUB so the architecture is in place. We implement the
real REST calls in a later step. ServiceNow exposes a Table API; creating an
incident is an HTTP POST to:

    {instance_url}/api/now/table/incident

authenticated with your ServiceNow credentials. We'll use the `requests`
library and read credentials from config/settings.py (never hardcoded).
"""

from config import settings
from helpdesk.incidents.models import Incident


class ServiceNowClient:
    def __init__(self):
        self.instance_url = settings.SERVICENOW_INSTANCE_URL
        self.username = settings.SERVICENOW_USERNAME
        self.password = settings.SERVICENOW_PASSWORD

    def is_configured(self) -> bool:
        return bool(self.instance_url and self.username and self.password)

    def create_incident(self, incident: Incident) -> str:
        """Create a ticket in ServiceNow and return its number.

        Later step (rough shape):

            import requests
            response = requests.post(
                f"{self.instance_url}/api/now/table/incident",
                auth=(self.username, self.password),
                json={
                    "short_description": incident.description,
                    "category": incident.category.value,
                    "urgency": ...,  # map our Priority to ServiceNow urgency
                },
                headers={"Content-Type": "application/json"},
            )
            return response.json()["result"]["number"]
        """
        if not self.is_configured():
            return "[ServiceNow not configured] Would have created a ticket for: " + incident.summary()

        # TODO (later step): make the real API call.
        raise NotImplementedError("Real ServiceNow call is implemented in a later step.")
