import csv
import logging
from collections import defaultdict, deque
from typing import Dict, List, Optional, Set, Tuple

from backend.core.models.domain import CurrencyEnum

logger = logging.getLogger(__name__)


class ExchangeRateConverter:
    """Fixed-rate currency converter with graph-based BFS triangulation,

    rate inversion for reverse pairs, and as-of date matching.
    """

    def __init__(self, csv_path: str = "dataset/exchange_rates.csv") -> None:
        self.csv_path = csv_path
        # History per directional pair: (from_curr, to_curr) -> list of (rate_date, rate)
        self.pair_history: Dict[Tuple[str, str], List[Tuple[str, float]]] = defaultdict(list)
        self.all_dates: List[str] = []
        self._load_exchange_rates()

    def _load_exchange_rates(self) -> None:
        unique_dates: Set[str] = set()
        with open(self.csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rate_date = row["rate_date"].strip()
                from_curr = CurrencyEnum.validate(row["from_currency"])
                to_curr = CurrencyEnum.validate(row["to_currency"])
                rate = float(row["rate"].strip())

                self.pair_history[(from_curr, to_curr)].append((rate_date, rate))
                unique_dates.add(rate_date)

        if not unique_dates:
            raise ValueError(f"No exchange rate data found in {self.csv_path}")

        self.all_dates = sorted(unique_dates)
        # Sort each pair's historical entries chronologically by rate_date
        for pair in self.pair_history:
            self.pair_history[pair].sort(key=lambda x: x[0])

    def get_as_of_snapshot_date(self, event_date: str) -> str:
        """Find the applicable rate snapshot date for event_date.

        Rule: pick the latest snapshot with rate_date <= event_date.
        If event_date predates all entries in the table, pick the earliest snapshot.
        """
        cleaned_date = event_date.strip()
        if cleaned_date < self.all_dates[0]:
            return self.all_dates[0]

        candidates = [d for d in self.all_dates if d <= cleaned_date]
        if candidates:
            return candidates[-1]
        return self.all_dates[0]

    def get_direct_rates(self, snapshot_date: str) -> Dict[str, Dict[str, float]]:
        """Return direct published rates available as of snapshot_date.

        For each known pair (u, v), finds the latest rate with rate_date <= snapshot_date.
        If snapshot_date predates the first recording of (u, v), falls back to the earliest.
        """
        direct: Dict[str, Dict[str, float]] = defaultdict(dict)
        for (u, v), history in self.pair_history.items():
            valid = [rate for r_date, rate in history if r_date <= snapshot_date]
            if valid:
                direct[u][v] = valid[-1]
            else:
                # Predates first record for this pair, fall back to earliest known
                direct[u][v] = history[0][1]
        return direct

    def _build_graph(
        self, snapshot_date: str
    ) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Dict[str, float]]]:
        """Build the full directional graph for snapshot_date.

        Returns:
            direct_rates: direct published pairs
            full_graph: direct edges + inverted edges where reverse is absent
        """
        direct_rates = self.get_direct_rates(snapshot_date)
        full_graph: Dict[str, Dict[str, float]] = defaultdict(dict)

        # 1. Add all direct rates
        for u, targets in direct_rates.items():
            for v, rate in targets.items():
                full_graph[u][v] = rate

        # 2. Add inverted rate (1.0 / rate) when only reverse is present
        for u, targets in direct_rates.items():
            for v, rate in targets.items():
                if rate <= 0:
                    raise ValueError(f"Non-positive exchange rate encountered for {u}->{v}: {rate}")
                if u not in full_graph[v]:
                    full_graph[v][u] = 1.0 / rate

        return direct_rates, full_graph

    def get_rate_and_path(
        self, from_curr: str, to_curr: str, event_date: str
    ) -> Tuple[float, List[str]]:
        """Compute the exchange rate and conversion path from from_curr to to_curr on event_date.

        Follows resolution priority:
        1. Same currency -> rate 1.0, path [curr]
        2. Direct lookup in published rates as-of date
        3. Inversion (1.0 / rate) if reverse is directly present
        4. BFS triangulation for cross-pairs
        """
        from_curr = CurrencyEnum.validate(from_curr)
        to_curr = CurrencyEnum.validate(to_curr)

        if from_curr == to_curr:
            return 1.0, [from_curr]

        snapshot_date = self.get_as_of_snapshot_date(event_date)
        direct_rates, full_graph = self._build_graph(snapshot_date)

        # Priority 1: Direct lookup for existing pair
        if to_curr in direct_rates.get(from_curr, {}):
            return direct_rates[from_curr][to_curr], [from_curr, to_curr]

        # Priority 2: Inversion (1.0 / rate) when only reverse is directly present
        if from_curr in direct_rates.get(to_curr, {}):
            return 1.0 / direct_rates[to_curr][from_curr], [from_curr, to_curr]

        # Priority 3: BFS triangulation for cross-pairs
        queue: deque[Tuple[str, float, List[str]]] = deque([(from_curr, 1.0, [from_curr])])
        visited: Set[str] = {from_curr}

        while queue:
            curr, cum_rate, path = queue.popleft()
            if curr == to_curr:
                return cum_rate, path

            for nxt, edge_rate in full_graph.get(curr, {}).items():
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt, cum_rate * edge_rate, path + [nxt]))

        raise ValueError(
            f"No exchange rate path from {from_curr} to {to_curr} on date {event_date} "
            f"(as-of snapshot {snapshot_date})"
        )

    def get_rate(self, from_curr: str, to_curr: str, event_date: str) -> float:
        """Return the exchange rate multiplier to convert from_curr to to_curr on event_date."""
        rate, _ = self.get_rate_and_path(from_curr, to_curr, event_date)
        return rate

    def get_conversion_path(self, from_curr: str, to_curr: str, event_date: str) -> List[str]:
        """Return the sequence of currencies traversed for the conversion."""
        _, path = self.get_rate_and_path(from_curr, to_curr, event_date)
        return path

    def convert(self, amount: float, from_curr: str, to_curr: str, event_date: str) -> float:
        """Convert amount from from_curr to to_curr as of event_date.

        If from_curr == to_curr, returns amount directly.
        """
        if from_curr == to_curr:
            return float(amount)
        if amount == 0.0:
            return 0.0

        rate = self.get_rate(from_curr, to_curr, event_date)
        return float(amount * rate)
