"""Unit tests for the ETL seed command helper functions."""

from datetime import time
from decimal import Decimal

from django.test import SimpleTestCase

from sensemap.management.commands.seed import (
    load_csv,
    parse_bool,
    parse_float,
    parse_int,
    parse_rating,
    parse_time,
)


class SeedHelperTests(SimpleTestCase):
    def test_parse_int_with_valid_integer(self):
        self.assertEqual(parse_int("42"), 42)

    def test_parse_int_with_invalid_value(self):
        self.assertIsNone(parse_int("not-a-number"))

    def test_parse_int_with_whitespace(self):
        self.assertIsNone(parse_int("   "))

    def test_parse_float_with_valid_decimal(self):
        self.assertEqual(parse_float("57.1648"), 57.1648)

    def test_parse_float_with_invalid_value(self):
        self.assertIsNone(parse_float("n/a"))

    def test_parse_bool_returns_true_for_common_truthy_strings(self):
        for value in ["true", "True", "yes", "YES", "1"]:
            with self.subTest(value=value):
                self.assertTrue(parse_bool(value))

    def test_parse_bool_returns_false_for_other_values(self):
        for value in ["false", "no", "0", "", None]:
            with self.subTest(value=value):
                self.assertFalse(parse_bool(value))

    def test_parse_time_with_24_hour_format(self):
        self.assertEqual(parse_time("09:00"), time(9, 0))

    def test_parse_time_with_12_hour_format(self):
        self.assertEqual(parse_time("10:30 AM"), time(10, 30))

    def test_parse_time_with_closed_returns_none(self):
        self.assertIsNone(parse_time("Closed"))

    def test_parse_rating_with_valid_integer(self):
        self.assertEqual(parse_rating("3"), Decimal("3"))

    def test_parse_rating_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            parse_rating("6")

    def test_parse_rating_with_empty_returns_none(self):
        self.assertIsNone(parse_rating(""))

    def test_load_csv_reads_facility_csv(self):
        rows = load_csv("Facility.csv")
        self.assertIsInstance(rows, list)
        self.assertGreater(len(rows), 0)
        self.assertIn("facility_id", rows[0])
        self.assertIn("name", rows[0])
