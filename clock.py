"""Pure timestamp conversion; no source file reader."""
import re
from datetime import datetime,timezone
def timestamp(token):
    if not re.fullmatch('\\d{4}-\\d{2}-\\d{2}[ T]\\d{2}:\\d{2}:\\d{2}(?:\\.\\d{1,6})?(?:Z|\\+00:00)?', token):
        raise ValueError('TIME_FORMAT')
    value = datetime.fromisoformat(token.replace('Z', '+00:00'))
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
