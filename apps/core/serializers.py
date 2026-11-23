from rest_framework import serializers


def person(user):
    if user is None:
        return None
    return {"id": user.id, "name": user.get_full_name() or user.get_username()}


class Sz_position_in(serializers.Serializer):
    """Ubicación opcional que manda la app del conductor."""

    latitude = serializers.FloatField(required=False, min_value=-90, max_value=90)
    longitude = serializers.FloatField(required=False, min_value=-180, max_value=180)

    def validate(self, attrs):
        # El GPS manda más decimales de los que guarda la base (6).
        for key in ("latitude", "longitude"):
            if attrs.get(key) is not None:
                attrs[key] = round(attrs[key], 6)
        return attrs


class Sz_reason_in(serializers.Serializer):
    reason = serializers.CharField()
