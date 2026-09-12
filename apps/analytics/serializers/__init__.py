from rest_framework import serializers


class AnalyticsSummarySerializer(serializers.Serializer):
    period = serializers.CharField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_orders = serializers.IntegerField()
    total_customers = serializers.IntegerField()
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    revenue_change = serializers.FloatField()
    orders_change = serializers.FloatField()
    customers_change = serializers.FloatField()
    aov_change = serializers.FloatField()


class RevenueDataPointSerializer(serializers.Serializer):
    date = serializers.CharField()
    revenue = serializers.FloatField()
    orders = serializers.IntegerField()


class TopProductSerializer(serializers.Serializer):
    product_id = serializers.CharField(allow_null=True)
    product_name = serializers.CharField()
    total_sold = serializers.IntegerField()
    revenue = serializers.FloatField()
    percentage_of_total = serializers.FloatField()


class CategoryPerformanceSerializer(serializers.Serializer):
    category_id = serializers.CharField(allow_null=True)
    category_name = serializers.CharField()
    total_sold = serializers.IntegerField()
    revenue = serializers.FloatField()
    percentage_of_total = serializers.FloatField()


class CustomerGrowthSerializer(serializers.Serializer):
    date = serializers.CharField()
    new_customers = serializers.IntegerField()
