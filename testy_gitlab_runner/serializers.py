from __future__ import annotations

from rest_framework import serializers

from testy.tests_representation.models import TestPlan


class RunTestsSerializer(serializers.Serializer):
    plan = serializers.PrimaryKeyRelatedField(queryset=TestPlan.objects.all())
    tests = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, default=list,
    )
    plans = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, default=list,
    )
    all_selected = serializers.BooleanField(required=False, default=False)
    filter_conditions = serializers.JSONField(required=False, default=dict)
    excluded_tests = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, default=list,
    )

    def validate(self, attrs):
        if not attrs["tests"] and not attrs["plans"] and not attrs["all_selected"]:
            raise serializers.ValidationError(
                "Select at least one test or plan.",
            )
        return attrs
