"""Errores de negocio.

Los servicios lanzan estas excepciones sin depender de DRF; el
``exception_handler`` de la API las convierte en respuestas HTTP.
"""


class BusinessError(Exception):
    """Una regla de negocio impide la acción (HTTP 400)."""

    status_code = 400
    default_code = "business_error"

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code


class BusinessPermissionError(BusinessError):
    """El usuario no tiene el rol o no es el responsable de la acción (HTTP 403)."""

    status_code = 403
    default_code = "permission_denied"


class BusinessNotFound(BusinessError):
    """El registro no existe o no es visible para el usuario (HTTP 404)."""

    status_code = 404
    default_code = "not_found"
