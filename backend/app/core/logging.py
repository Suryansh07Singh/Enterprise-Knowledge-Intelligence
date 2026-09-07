import logging
import json
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "trace_id": trace_id_var.get() or str(uuid.uuid4())[:8],
        }
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_data.update(record.extra)
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

def setup_logger():
    logger = logging.getLogger("enterprise_rag")
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        
    return logger

logger = setup_logger()

def get_trace_id() -> str:
    tid = trace_id_var.get()
    if not tid:
        tid = str(uuid.uuid4())
        trace_id_var.set(tid)
    return tid

def set_trace_id(tid: str):
    trace_id_var.set(tid)
