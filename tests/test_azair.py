import unittest
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

from pydantic import ValidationError

from azair.client import _dedupe_results, _weekday_bit, build_search_url, search_flights
from azair.models import FlightResult, FlightSegment, SearchParams
from azair.parser import _extract_currency, _parse_price, parse_results


RESULT_HTML = """
<div id="reslist">
  <div class="result">
    <div class="text">
      <p>
        <span class="caption">There</span>
        <span class="date">Tue 10/11/26</span>
        <span class="durcha">9:45 h / 1 change</span>
      </p>
      <div class="detail">
        <p>
          <span class="from">Tu 10:40 Prague <span class="code">PRG</span></span>
          <span class="to">12:05 Edinburgh <span class="code">EDI</span><a>U23326</a></span>
          <span class="airline iataU2">easyJet</span>
          <span class="legPrice">196 zł</span>
          <a class="affPopUp" href="book/one">Book</a>
        </p>
        <p>
          <span class="from">Tu 18:00 Edinburgh <span class="code">EDI</span></span>
          <span class="to">19:25 London <span class="code">STN</span><a>FR9816</a></span>
          <span class="airline iataFR">Ryanair</span>
          <span class="legPrice">132 zł</span>
        </p>
      </div>
      <p>
        <span class="caption">Back</span>
        <span class="date">Tue 17/11/26</span>
        <span class="durcha">11:45 h / 1 change</span>
      </p>
      <div class="detail">
        <p>
          <span class="from">Tu 07:50 London <span class="code">STN</span></span>
          <span class="to">20:35 Prague <span class="code">PRG</span><a>FR9817</a></span>
          <span class="airline iataFR">Ryanair</span>
          <span class="legPrice">320 zł</span>
        </p>
      </div>
      <span class="lengthOfStay">7 days</span>
      <span class="sumPrice">Total: 649 zł</span>
    </div>
  </div>
</div>
"""


def params(**overrides):
    values = {
        "src_airport": "PRG",
        "dst_airport": "MXP",
        "dep_date": "2026-11-10",
        "arr_date": "2026-11-20",
    }
    values.update(overrides)
    return SearchParams(**values)


def query(**overrides):
    return parse_qs(urlparse(build_search_url(params(**overrides))).query)


def segment(flight_number):
    return FlightSegment(
        airline="Ryanair",
        airline_iata="FR",
        flight_number=flight_number,
        departure_airport="Prague",
        departure_airport_code="PRG",
        departure_time="10:00",
        arrival_airport="London",
        arrival_airport_code="STN",
        arrival_time="11:00",
        duration="2h",
        price=10.0,
        currency="EUR",
    )


def result(flight_number):
    return FlightResult(
        total_price=20.0,
        currency="EUR",
        length_of_stay_days=2,
        outbound_date="Tue 10/11/26",
        return_date="Thu 12/11/26",
        outbound_segments=[segment(flight_number)],
        return_segments=[],
        booking_url="",
    )


class PriceTests(unittest.TestCase):
    def test_parse_price_and_currency(self):
        cases = {
            "Total: €147.32": (147.32, "EUR"),
            "Total: 649 zł": (649.0, "PLN"),
            "Total: 53916 Ft": (53916.0, "HUF"),
            "Total: 13271 руб": (13271.0, "RUB"),
            "Total: 1101.05\u00a0kr": (1101.05, "DKK"),
            "Total: 7480.76\u00a0₴": (7480.76, "UAH"),
            "Total: 517.11\u00a0₪": (517.11, "ILS"),
            "Total: 25921.54\u00a0¥": (25921.54, "JPY"),
            "Total: 8222 TRY": (8222.0, "TRY"),
            "Total: 1,234.56 €": (1234.56, "EUR"),
            "Total: 1 234,56 Kč": (1234.56, "CZK"),
        }
        for text, (price, currency) in cases.items():
            with self.subTest(text=text):
                self.assertEqual(_parse_price(text), price)
                self.assertEqual(_extract_currency(text), currency)

    def test_currency_fallback(self):
        self.assertEqual(_extract_currency("Total: 100", "PLN"), "PLN")


class ModelTests(unittest.TestCase):
    def test_invalid_inputs_are_rejected(self):
        invalid = [
            {"dep_date": "bad"},
            {"min_days_stay": 5, "max_days_stay": 2},
            {"min_hour_outbound": "20:00", "max_hour_outbound": "08:00"},
            {"dst_metro_code": "MIL"},
            {"dst_airport": "STN", "dst_metro_code": "MIL_ALL"},
        ]
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValidationError):
                    params(**overrides)

    def test_valid_metro_combinations(self):
        self.assertEqual(params(dst_airport="MIL_ALL").dst_airport, "MIL_ALL")
        self.assertEqual(
            params(dst_airport="MXP", dst_metro_code="MIL_ALL").dst_metro_code,
            "MIL_ALL",
        )
        self.assertEqual(
            params(dst_airport="XXX", dst_metro_code="XXX").dst_metro_code, "XXX"
        )

    def test_dates_are_normalized(self):
        self.assertEqual(params(dep_date="10.11.2026").dep_date, "2026-11-10")
        self.assertEqual(params(dep_date="2026/11/10").dep_date, "2026-11-10")
        self.assertEqual(params(dep_date="10/11/2026").dep_date, "2026-11-10")

    def test_weekdays_are_normalized(self):
        self.assertEqual(params(departure_weekdays=[6, 1, 1]).departure_weekdays, [1, 6])
        self.assertIsNone(params(departure_weekdays=[]).departure_weekdays)


class UrlTests(unittest.TestCase):
    def test_metro_sets_mc_and_expands_ports(self):
        data = query(dst_airport="MIL_ALL")
        self.assertEqual(data["dstMC"], ["MIL_ALL"])
        self.assertEqual(data["dstAirport"], ["[MXP] (+BGY,LIN)"])
        self.assertEqual(data["dstap0"], ["BGY"])
        self.assertEqual(data["dstap1"], ["LIN"])

    def test_country_code_sets_mc(self):
        data = query(dst_airport="DE")
        self.assertEqual(data["dstMC"], ["DE"])
        self.assertEqual(data["dstAirport"][0], "[BER] (+NRN,FMM,FRA,FDH,HAM,CGN,DUS,HHN,MUC,NUE,BRE,FKB)")

    def test_xxx_ignores_extras(self):
        data = query(dst_airport="XXX", dst_airports=["MXP"])
        self.assertEqual(data["dstAirport"], ["[XXX]"])
        self.assertNotIn("dstMC", data)
        self.assertNotIn("dstap0", data)

    def test_xxx_metro(self):
        data = query(dst_airport="XXX", dst_metro_code="XXX")
        self.assertEqual(data["dstAirport"], ["[XXX]"])
        self.assertNotIn("dstMC", data)

    def test_open_jaw_enables_transfer(self):
        self.assertEqual(query(same_arr=False)["transfer"], ["true"])
        self.assertEqual(query(is_oneway=True, same_arr=False)["transfer"], ["false"])

    def test_empty_weekdays_mean_all_days(self):
        bits = _weekday_bit([], [])
        self.assertTrue(all(value == "true" for value in bits.values()))

    def test_metro_in_extras_is_expanded(self):
        data = query(dst_airport="MXP", dst_airports=["MIL_ALL"])
        self.assertIn("BGY", data["dstAirport"][0])
        self.assertEqual(data["dstap0"], ["BGY"])


class ParserTests(unittest.TestCase):
    def test_parse_result(self):
        results = parse_results(RESULT_HTML)
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result.total_price, 649.0)
        self.assertEqual(result.currency, "PLN")
        self.assertEqual(result.length_of_stay_days, 7)
        self.assertEqual(len(result.outbound_segments), 2)
        self.assertEqual(len(result.return_segments), 1)
        self.assertEqual(result.outbound_segments[0].flight_number, "U23326")
        self.assertEqual(result.outbound_segments[1].price, 132.0)

    def test_no_results_page(self):
        self.assertEqual(parse_results('<div class="noResults">unavailable</div>'), [])


class RetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_retries_are_bounded(self):
        with patch("azair.client.RETRY_DELAY_SECONDS", 0), patch(
            "azair.client._search_once", new_callable=AsyncMock
        ) as search_once:
            search_once.side_effect = [[], [], [], [], [result("FR1")]]
            results = await search_flights(
                params(min_days_stay=2, max_days_stay=5)
            )
        self.assertEqual(len(results), 1)
        self.assertEqual(search_once.await_count, 5)

    async def test_one_way_skips_stay_range_retries(self):
        with patch("azair.client.RETRY_DELAY_SECONDS", 0), patch(
            "azair.client._search_once", new_callable=AsyncMock
        ) as search_once:
            search_once.side_effect = [[], []]
            await search_flights(params(is_oneway=True))
        self.assertEqual(search_once.await_count, 2)

    async def test_no_retry_when_results_found(self):
        with patch("azair.client._search_once", new_callable=AsyncMock) as search_once:
            search_once.return_value = [result("FR1")]
            results = await search_flights(params())
        self.assertEqual(len(results), 1)
        self.assertEqual(search_once.await_count, 1)


class DedupeTests(unittest.TestCase):
    def test_flight_number_is_part_of_key(self):
        results = _dedupe_results([result("FR1"), result("FR2")])
        self.assertEqual(len(results), 2)

    def test_identical_results_are_deduplicated(self):
        results = _dedupe_results([result("FR1"), result("FR1")])
        self.assertEqual(len(results), 1)


if __name__ == "__main__":
    unittest.main()
