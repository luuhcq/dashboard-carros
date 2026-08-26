import django_filters

from .models import Vehicle, VehicleStatus

AGING_BUCKET_RANGES = {
    '0-15': (0, 15),
    '16-30': (16, 30),
    '31-45': (31, 45),
    '46-60': (46, 60),
    '61-90': (61, 90),
    # '90+' tratado à parte (sem limite superior) em filter_aging_bucket
}
AGING_BUCKET_CHOICES = [(bucket, bucket) for bucket in (*AGING_BUCKET_RANGES, '90+')]


class VehicleFilter(django_filters.FilterSet):
    """Opera sobre o queryset já anotado por annotate_vehicle_metrics()
    (aplicado em VehicleViewSet.get_queryset() antes do filtro) — aging_bucket
    filtra pela coluna `aging` já calculada em SQL, não recalcula nada aqui.
    """

    status = django_filters.ChoiceFilter(choices=VehicleStatus.choices)
    brand = django_filters.CharFilter(lookup_expr='icontains')
    model = django_filters.CharFilter(lookup_expr='icontains')
    is_sold = django_filters.BooleanFilter(method='filter_is_sold')
    aging_bucket = django_filters.ChoiceFilter(
        choices=AGING_BUCKET_CHOICES, method='filter_aging_bucket'
    )

    class Meta:
        model = Vehicle
        fields = ['status', 'brand', 'model']

    def filter_is_sold(self, queryset, name, value):
        if value:
            return queryset.filter(status=VehicleStatus.SOLD)
        return queryset.exclude(status=VehicleStatus.SOLD)

    def filter_aging_bucket(self, queryset, name, value):
        if value == '90+':
            return queryset.filter(aging__gt=90)
        low, high = AGING_BUCKET_RANGES[value]
        return queryset.filter(aging__gte=low, aging__lte=high)
