"""Utilidades para los steps de workflow.

El motor arma el contexto con ``request.data`` (dict en JSON, QueryDict en
multipart), agrega ``user`` y ``files``. Estas funciones leen el contexto
igual en ambos casos y convierten los errores de validación en mensajes
legibles para el frontend.
"""

from apps.core.exceptions import BusinessError


def context_user(context):
    return context.get("user")


def context_files(context) -> list:
    """Archivos subidos (``files`` del multipart). Los saca del contexto para que no se guarden en la ejecución."""
    files = context.get("files")
    if "files" in context:
        context.pop("files")
    if not files:
        return []
    return list(files) if isinstance(files, (list, tuple)) else [files]


def _flatten_errors(errors, prefix="") -> list[str]:
    messages = []
    if isinstance(errors, dict):
        for key, value in errors.items():
            messages.extend(_flatten_errors(value, f"{prefix}{key}: " if key != "non_field_errors" else prefix))
    elif isinstance(errors, list):
        for index, value in enumerate(errors):
            if isinstance(value, (dict, list)):
                messages.extend(_flatten_errors(value, f"{prefix}[{index}] "))
            else:
                messages.append(f"{prefix}{value}")
    else:
        messages.append(f"{prefix}{errors}")
    return messages


def validate_input(serializer_class, context) -> dict:
    """Valida los campos declarados en ``serializer_class`` tomados del contexto."""
    fields = serializer_class().fields
    data = {name: context.get(name) for name in fields if name in context and context.get(name) is not None}
    serializer = serializer_class(data=data)
    if not serializer.is_valid():
        raise BusinessError("; ".join(_flatten_errors(serializer.errors)), code="invalid_input")
    return serializer.validated_data


def results(data):
    return {"context_updates": {"results": data}}


def validate_files(files, validator) -> list:
    """Aplica ``validator`` a cada archivo y devuelve errores legibles como BusinessError."""
    from django.core.exceptions import ValidationError as DjangoValidationError
    from rest_framework.exceptions import ValidationError as DrfValidationError

    for file in files:
        try:
            validator(file)
        except (DjangoValidationError, DrfValidationError) as exc:
            detail = getattr(exc, "messages", None) or getattr(exc, "detail", None) or [str(exc)]
            raise BusinessError(f"{file.name}: {'; '.join(str(m) for m in detail)}", code="invalid_file")
    return files
