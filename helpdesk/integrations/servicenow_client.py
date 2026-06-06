"""Create incidents in ServiceNow via the REST Table API."""

from dataclasses import dataclass

from config import settings


@dataclass
class CreatedIncident:
    number: str
    sys_id: str
    url: str


# Map this app's priority (low/medium/high) to ServiceNow urgency & impact
# (1 = High, 2 = Medium, 3 = Low). ServiceNow derives Priority from urgency x impact.
_URGENCY_IMPACT = {
    "high": ("1", "1"),
    "medium": ("2", "2"),
    "low": ("3", "3"),
}


class ServiceNowClient:
    """Thin wrapper over the ServiceNow incident Table API."""

    def __init__(self):
        self.instance = settings.SERVICENOW_INSTANCE.rstrip("/")
        self.user = settings.SERVICENOW_USER
        self.password = settings.SERVICENOW_PASSWORD
        self.configured = settings.servicenow_configured()

    def create_incident(self, short_description, description="",
                         category="", priority="medium", prompt=print):
        if not self.configured:
            return None

        try:
            import requests
        except ImportError:
            prompt("[ServiceNow] the 'requests' package isn't installed.")
            return None

        urgency, impact = _URGENCY_IMPACT.get((priority or "").lower(), ("2", "2"))
        payload = {
            "short_description": short_description,
            "description": description,
            "urgency": urgency,
            "impact": impact,
        }
        if category:
            payload["category"] = category

        url = f"{self.instance}/api/now/table/incident"
        try:
            resp = requests.post(
                url,
                auth=(self.user, self.password),
                headers={"Content-Type": "application/json",
                         "Accept": "application/json"},
                json=payload,
                timeout=60,
            )
        except Exception as exc:
            prompt(f"[ServiceNow] could not reach the instance: {exc}")
            return None

        if resp.status_code not in (200, 201):
            prompt(f"[ServiceNow] HTTP {resp.status_code}: {resp.text[:300]}")
            return None

        try:
            result = resp.json().get("result", {})
        except Exception:
            prompt("[ServiceNow] unexpected (non-JSON) response.")
            return None

        sys_id = result.get("sys_id", "")
        view_url = f"{self.instance}/incident.do?sys_id={sys_id}" if sys_id else self.instance
        return CreatedIncident(
            number=result.get("number", ""),
            sys_id=sys_id,
            url=view_url,
        )