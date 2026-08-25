"""
KPSS Super-Brain: Hata Türleri ve İstisna Hiyerarşisi (Error Models)
Sistemin sessizce başarısız olmasını engelleyen, tip güvenli ve sınıflandırılmış hata modelleri.
"""
from enum import Enum
from typing import Optional, Dict, Any

class ErrorSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class ErrorRetryability(str, Enum):
    RETRYABLE = "RETRYABLE"
    NON_RETRYABLE = "NON_RETRYABLE"
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"

class SuperBrainError(Exception):
    """Tüm KPSS Super-Brain hatalarının temel sınıfı."""
    def __init__(
        self,
        message: str,
        error_code: str = "GENERIC_ERROR",
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        retryability: ErrorRetryability = ErrorRetryability.NON_RETRYABLE,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.retryability = retryability
        self.context = context or {}
        self.cause = cause

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "severity": self.severity.value,
            "retryability": self.retryability.value,
            "context": self.context,
            "cause": str(self.cause) if self.cause else None
        }

class AgentError(SuperBrainError):
    """Araştırma ajanının durum veya planlama hataları."""
    pass

class ToolError(SuperBrainError):
    """Araç çalıştırma, parametre veya zaman aşımı hataları."""
    pass

class TranscriptError(SuperBrainError):
    """Altyazı ve ses işleme hataları."""
    pass

class ExtractionError(SuperBrainError):
    """Transkriptten atomik claim çıkarma ve JSON ayrıştırma hataları."""
    pass

class VerificationError(SuperBrainError):
    """Anti-halüsinasyon, RefChecker ve Z3 SMT doğrulama hataları."""
    pass

class ContradictionError(SuperBrainError):
    """Çelişki tespit ve çözümleme hataları."""
    pass

class PersistenceError(SuperBrainError):
    """SQLite ve ambar veritabanı yazma hataları."""
    pass
