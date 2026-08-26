"""Prompt 23 — fecha a Dívida #4 do checkpoint arquitetural: confirma que
vehicles.filters.AGING_BUCKET_RANGES (usado em SQL, filtro aging_bucket= e
/api/dashboard/aging/) concorda com vehicles.services._aging_bucket (usado
em Python, VehicleMetricsService) nos mesmos pontos de corte. Os dois
comentários já documentavam essa duplicação deliberada e o risco de
divergência sem teste — este arquivo é esse teste.
"""

from django.test import SimpleTestCase

from vehicles.filters import AGING_BUCKET_RANGES
from vehicles.services import _aging_bucket


def _bucket_from_ranges(days_in_stock: int) -> str:
    """Mesma lógica de vehicles.filters.VehicleFilter.filter_aging_bucket,
    mas em Python puro (sem queryset) — só pra comparar contra
    _aging_bucket() sem precisar de banco."""
    for bucket, (low, high) in AGING_BUCKET_RANGES.items():
        if low <= days_in_stock <= high:
            return bucket
    return '90+'


class AgingBucketRangesMatchServiceTests(SimpleTestCase):
    def test_ranges_and_service_agree_across_full_practical_domain(self):
        """Varredura de 0 a 120 dias (cobre todas as faixas e bem além do
        90+) — não só os pontos de fronteira, todo o domínio prático."""
        mismatches = [
            days for days in range(0, 121)
            if _aging_bucket(days) != _bucket_from_ranges(days)
        ]
        self.assertEqual(
            mismatches, [],
            f'_aging_bucket() e AGING_BUCKET_RANGES divergem nestes dias: {mismatches}'
        )

    def test_boundary_points_explicitly(self):
        """Redundante com o teste acima de propósito — os pontos de
        fronteira são os mais fáceis de errar ao editar as faixas (off-by-
        one), então merecem ficar explícitos, não só cobertos de raspão
        pela varredura."""
        boundary_expectations = {
            0: '0-15', 15: '0-15', 16: '16-30', 30: '16-30',
            31: '31-45', 45: '31-45', 46: '46-60', 60: '46-60',
            61: '61-90', 90: '61-90', 91: '90+', 200: '90+',
        }
        for days, expected_bucket in boundary_expectations.items():
            with self.subTest(days=days):
                self.assertEqual(_aging_bucket(days), expected_bucket)
                self.assertEqual(_bucket_from_ranges(days), expected_bucket)
