from rest_framework import serializers

ARC_MODES = [("legs", "Origen -> parada 1 -> parada 2..."), ("hub", "Origen -> cada parada")]


class Sz_positions_in(serializers.Serializer):
    vehicle_ids = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True)
    plates = serializers.ListField(child=serializers.CharField(max_length=10), required=False, allow_empty=True)


class Sz_history_in(serializers.Serializer):
    vehicle_id = serializers.IntegerField(required=False)
    plate = serializers.CharField(max_length=10, required=False)
    start = serializers.DateTimeField(required=False)
    end = serializers.DateTimeField(required=False)
    event_codes = serializers.ListField(child=serializers.CharField(max_length=30), required=False,
                                        allow_empty=True)

    def validate(self, attrs):
        if not attrs.get("vehicle_id") and not attrs.get("plate"):
            raise serializers.ValidationError("Envía vehicle_id o plate.")
        return attrs


class Sz_map_overview_in(serializers.Serializer):
    arc_mode = serializers.ChoiceField(choices=ARC_MODES, required=False, default="legs")
    trip_ids = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True)


class Sz_trip_map_in(serializers.Serializer):
    trip_id = serializers.IntegerField()
    arc_mode = serializers.ChoiceField(choices=ARC_MODES, required=False, default="legs")
    with_route = serializers.BooleanField(required=False, default=True)
