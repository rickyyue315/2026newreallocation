import sys
import os
import json
import tempfile
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    VERSION,
    REQUIRED_COLUMNS,
    INTEGER_COLUMNS,
    FILE_SIZE_LIMIT_BYTES,
)


class TestConfig:
    def test_version_string(self):
        assert VERSION == "v2.15.0"

    def test_required_columns(self):
        assert len(REQUIRED_COLUMNS) == 10
        assert "Article" in REQUIRED_COLUMNS
        assert "SaSa Net Stock" in REQUIRED_COLUMNS

    def test_integer_columns(self):
        assert len(INTEGER_COLUMNS) == 6


class TestDataProcessor:
    def test_preprocess_basic(self):
        from data_processor import DataProcessor
        import pandas as pd
        import numpy as np

        df_input = pd.DataFrame({
            "Article": ["123456789012", "987654321098"],
            "OM": ["Ivy", "Hippo"],
            "RP Type": ["RF", "ND"],
            "Site": ["HA02", "HB01"],
            "SaSa Net Stock": [100, 50],
            "Pending Received": [10, 5],
            "Safety Stock": [20, 10],
            "Last Month Sold Qty": [30, 15],
            "MTD Sold Qty": [5, 3],
            "MOQ": [1, 1],
        })

        buffer = io.BytesIO()
        df_input.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        dp = DataProcessor(stores_json_path="data/stores.json")
        df, stats = dp.preprocess_data(buffer)

        assert len(df) == 2
        assert "Effective Sold Qty" in df.columns
        assert "Total Available" in df.columns
        assert df["Effective Sold Qty"].iloc[0] == 35
        assert df["Total Available"].iloc[0] == 110

    def test_article_normalization(self):
        from data_processor import DataProcessor
        import pandas as pd

        df_input = pd.DataFrame({
            "Article": ["123456789012", "12345"],
            "OM": ["Ivy", "Hippo"],
            "RP Type": ["RF", "ND"],
            "Site": ["HA02", "HB01"],
            "SaSa Net Stock": [100, 50],
            "Pending Received": [0, 0],
            "Safety Stock": [20, 10],
            "Last Month Sold Qty": [0, 0],
            "MTD Sold Qty": [0, 0],
            "MOQ": [0, 0],
        })

        buffer = io.BytesIO()
        df_input.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        dp = DataProcessor(stores_json_path="data/stores.json")
        df, _ = dp.preprocess_data(buffer)

        assert len(df["Article"].iloc[0]) == 12
        assert len(df["Article"].iloc[1]) == 12

    def test_missing_columns(self):
        from data_processor import DataProcessor
        import pandas as pd

        df_input = pd.DataFrame({
            "Article": ["123456789012"],
        })

        buffer = io.BytesIO()
        df_input.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        dp = DataProcessor(stores_json_path="data/stores.json")
        try:
            dp.preprocess_data(buffer)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_outlier_correction(self):
        from data_processor import DataProcessor
        from config import OUTLIER_CAP
        import pandas as pd

        df_input = pd.DataFrame({
            "Article": ["123456789012"],
            "OM": ["Ivy"],
            "RP Type": ["RF"],
            "Site": ["HA02"],
            "SaSa Net Stock": [100],
            "Pending Received": [0],
            "Safety Stock": [20],
            "Last Month Sold Qty": [200000],
            "MTD Sold Qty": [-5],
            "MOQ": [0],
        })

        buffer = io.BytesIO()
        df_input.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        dp = DataProcessor(stores_json_path="data/stores.json")
        df, stats = dp.preprocess_data(buffer)

        assert df["Last Month Sold Qty"].iloc[0] == OUTLIER_CAP
        assert df["MTD Sold Qty"].iloc[0] == 0


class TestTargetParser:
    def test_simple_target(self):
        from services.target_utils import parse_target_series

        has_target, val, parts, raw = parse_target_series("100")
        assert has_target is True
        assert val == 100.0
        assert parts == [100.0]

    def test_comma_target(self):
        from services.target_utils import parse_target_series

        has_target, val, parts, raw = parse_target_series("1,234")
        assert has_target is True
        assert val == 1234.0

    def test_none_target(self):
        from services.target_utils import parse_target_series

        has_target, _, _, _ = parse_target_series(None)
        assert has_target is False

    def test_zero_target(self):
        from services.target_utils import parse_target_series

        has_target, _, _, _ = parse_target_series("0")
        assert has_target is False


class TestPredicates:
    def test_hd_to_hk_restricted(self):
        from strategies.predicates import is_hd_to_hk_restricted

        assert is_hd_to_hk_restricted("HD02", "HA02") is True
        assert is_hd_to_hk_restricted("HD02", "HB01") is True
        assert is_hd_to_hk_restricted("HD02", "HC01") is True
        assert is_hd_to_hk_restricted("HD02", "HD03") is False
        assert is_hd_to_hk_restricted("HA02", "HD02") is False
        assert is_hd_to_hk_restricted("HA02", "HB01") is False


class TestModeRegistry:
    def test_all_24_modes(self):
        from models.mode_registry import MODE_REGISTRY

        expected_codes = [
            "A", "B", "B2", "B2a", "B2L", "B2La",
            "B3", "B3a", "B3L", "B3La",
            "C", "C1", "C2",
            "D", "D2",
            "E1", "E1b", "E2",
            "F", "F2",
            "ND1", "ND2",
            "簡同", "簡跨",
        ]

        for code in expected_codes:
            assert code in MODE_REGISTRY, f"Mode {code} not found in registry"

        assert len(MODE_REGISTRY) == 24

    def test_b_special_strategy(self):
        from models.mode_registry import MODE_REGISTRY

        for code in ("B2", "B2a", "B2L", "B2La", "B3", "B3a", "B3L", "B3La"):
            assert MODE_REGISTRY[code].strategy_key == "b_special"
            assert "b_special" in MODE_REGISTRY[code].families

    def test_cross_om_modes(self):
        from models.mode_registry import MODE_REGISTRY

        cross_om_codes = ("B3", "B3a", "B3L", "B3La", "C2", "E2", "F", "F2", "ND2", "簡跨")
        for code in cross_om_codes:
            assert MODE_REGISTRY[code].cross_om_matching, f"{code} should have cross_om_matching"


class TestMatchingEngine:
    def setup_method(self):
        from models.mode_registry import MODE_REGISTRY

        class MockLogic:
            _mode_info_cache = MODE_REGISTRY

        self.logic = MockLogic()

    def make_source(self, **overrides):
        base = {
            "site": "HA01", "om": "Ivy", "rp_type": "RF",
            "transferable_qty": 10, "source_type": "RF過剩轉出",
            "priority": 2, "article": "123456789012",
            "net_stock": 20, "safety_stock": 5,
            "last_month_sold": 3, "mtd_sold": 1, "effective_sold_qty": 4,
            "store_type": "M", "total_available": 20,
            "original_stock": 20, "total_transferred": 0,
        }
        base.update(overrides)
        return base

    def make_dest(self, **overrides):
        base = {
            "site": "HB01", "om": "Ivy", "rp_type": "RF",
            "needed_qty": 8, "dest_type": "緊急缺貨",
            "priority": 1, "article": "123456789012",
            "net_stock": 0, "safety_stock": 8,
            "last_month_sold": 5, "mtd_sold": 2, "effective_sold_qty": 7,
            "store_type": "M", "total_available": 0,
        }
        base.update(overrides)
        return base

    def test_compute_transfer_qty_basic(self):
        from services.matching_engine import compute_transfer_qty

        source = self.make_source(transferable_qty=10)
        dest = self.make_dest(needed_qty=8)
        qty = compute_transfer_qty(self.logic, source, dest, "B", 0)
        assert qty == 8

    def test_compute_transfer_qty_limited_by_source(self):
        from services.matching_engine import compute_transfer_qty

        source = self.make_source(transferable_qty=3)
        dest = self.make_dest(needed_qty=8)
        qty = compute_transfer_qty(self.logic, source, dest, "B", 0)
        assert qty == 3

    def test_can_transfer_self_to_self(self):
        from services.matching_engine import can_transfer

        source = self.make_source(site="HA01")
        dest = self.make_dest(site="HA01")
        result = can_transfer(
            self.logic, source, dest, "A", "123456789012",
            set(), set(), set(), None, {}, False,
        )
        assert result is False

    def test_can_transfer_nd_dest_blocked(self):
        from services.matching_engine import can_transfer

        source = self.make_source(site="HA01")
        dest = self.make_dest(site="HB01", rp_type="ND")
        result = can_transfer(
            self.logic, source, dest, "A", "123456789012",
            set(), set(), set(), None, {}, False,
        )
        assert result is False

    def test_can_transfer_cross_om_hd_restricted(self):
        from services.matching_engine import can_transfer

        source = self.make_source(site="HD02", om="Windy")
        dest = self.make_dest(site="HA02", om="Ivy")

        from models.mode_registry import MODE_REGISTRY
        self.logic._mode_info_cache = MODE_REGISTRY

        result = can_transfer(
            self.logic, source, dest, "E2", "123456789012",
            set(), set(), set(), None, {}, False,
        )
        assert result is False

    def test_can_transfer_windy_restricted(self):
        from services.matching_engine import can_transfer

        source = self.make_source(site="HD02", om="Windy")
        dest = self.make_dest(site="HD03", om="Windy")

        source2 = self.make_source(site="HD02", om="Windy")
        dest2 = self.make_dest(site="HA02", om="Ivy")

        from models.mode_registry import MODE_REGISTRY
        self.logic._mode_info_cache = MODE_REGISTRY

        result1 = can_transfer(
            self.logic, source, dest, "E2", "123456789012",
            set(), set(), set(), None, {}, False,
        )
        assert result1 is True

        result2 = can_transfer(
            self.logic, source2, dest2, "E2", "123456789012",
            set(), set(), set(), None, {}, False,
        )
        assert result2 is False

    def test_single_piece_upgrade(self):
        from services.matching_engine import compute_transfer_qty

        source = self.make_source(transferable_qty=5, source_type="ND轉出")
        dest = self.make_dest(needed_qty=2)
        qty = compute_transfer_qty(self.logic, source, dest, "A", 0)
        assert qty >= 2


class TestQualityChecks:
    def test_article_integrity(self):
        from services.quality_checks import run_quality_checks

        recs = [{"Article": "", "Transfer Qty": 5, "Transfer Site": "HA01", "Receive Site": "HB01"}]
        passed, errors = run_quality_checks(recs)
        assert passed is False
        assert any("Article" in e for e in errors)

    def test_positive_qty(self):
        from services.quality_checks import run_quality_checks

        recs = [{"Article": "123456789012", "Transfer Qty": 0, "Transfer Site": "HA01", "Receive Site": "HB01"}]
        passed, errors = run_quality_checks(recs)
        assert passed is False

    def test_no_dual_role(self):
        from services.quality_checks import run_quality_checks

        recs = [
            {"Article": "123456789012", "Transfer Qty": 3, "Transfer Site": "HA01", "Receive Site": "HB01", "Source Type": "ND", "Destination Type": "緊急缺貨"},
            {"Article": "123456789012", "Transfer Qty": 2, "Transfer Site": "HB01", "Receive Site": "HA01", "Source Type": "RF", "Destination Type": "潛在缺貨"},
        ]
        passed, errors = run_quality_checks(recs)
        assert passed is False
        assert any("dual" in e.lower() for e in errors)

    def test_article_length(self):
        from services.quality_checks import run_quality_checks

        recs = [{"Article": "12345", "Transfer Qty": 3, "Transfer Site": "HA01", "Receive Site": "HB01"}]
        passed, errors = run_quality_checks(recs)
        assert passed is False
        assert any("12" in e for e in errors)


class TestTransferLogic:
    def test_sources_general_a_mode(self):
        import pandas as pd
        from business_logic import TransferLogic

        df = pd.DataFrame({
            "Article": ["123456789012", "123456789012"],
            "OM": ["Ivy", "Ivy"],
            "RP Type": ["RF", "RF"],
            "Site": ["HA01", "HA02"],
            "SaSa Net Stock": [100, 50],
            "Pending Received": [0, 0],
            "Safety Stock": [20, 10],
            "Last Month Sold Qty": [5, 30],
            "MTD Sold Qty": [3, 10],
            "MOQ": [1, 1],
            "Effective Sold Qty": [8, 40],
            "Total Available": [100, 50],
            "Article Description": ["Test Product", "Test Product"],
        })

        logic = TransferLogic()
        sources = logic._sources_general(df, "A")

        nd_sources = [s for s in sources if s["rp_type"] == "ND"]
        assert len(nd_sources) == 0

        rf_sources = [s for s in sources if s["rp_type"] == "RF"]
        assert len(rf_sources) >= 1

    def test_sources_general_b_mode(self):
        import pandas as pd
        from business_logic import TransferLogic

        df = pd.DataFrame({
            "Article": ["123456789012"],
            "OM": ["Ivy"],
            "RP Type": ["RF"],
            "Site": ["HA01"],
            "SaSa Net Stock": [100],
            "Pending Received": [0],
            "Safety Stock": [20],
            "Last Month Sold Qty": [5],
            "MTD Sold Qty": [3],
            "MOQ": [1],
            "Effective Sold Qty": [8],
            "Total Available": [100],
            "Article Description": ["Test"],
        })

        logic = TransferLogic()
        sources = logic._sources_general(df, "B")

        assert len(sources) >= 1
        rf_source = sources[0]
        assert rf_source["transferable_qty"] > 0

    def test_dests_general(self):
        import pandas as pd
        from business_logic import TransferLogic

        df = pd.DataFrame({
            "Article": ["123456789012", "123456789012"],
            "OM": ["Ivy", "Ivy"],
            "RP Type": ["RF", "RF"],
            "Site": ["HA01", "HA02"],
            "SaSa Net Stock": [0, 30],
            "Pending Received": [0, 0],
            "Safety Stock": [15, 50],
            "Last Month Sold Qty": [10, 0],
            "MTD Sold Qty": [5, 0],
            "MOQ": [1, 1],
            "Effective Sold Qty": [15, 0],
            "Total Available": [0, 30],
            "Article Description": ["Test", "Test"],
        })

        logic = TransferLogic()
        dests = logic._dests_general(df, "A")

        assert len(dests) >= 1

        critical = [d for d in dests if d["dest_type"] == "緊急缺貨"]
        assert len(critical) >= 1
        assert critical[0]["net_stock"] == 0

        potential = [d for d in dests if d["dest_type"] == "潛在缺貨"]
        if potential:
            assert potential[0]["total_available"] < potential[0]["safety_stock"]


class TestStatistics:
    def test_basic_stats(self):
        from services.statistics import compute_transfer_statistics

        recs = [
            {
                "Article": "123456789012",
                "Transfer Qty": 5,
                "Transfer OM": "Ivy",
                "Receive OM": "Ivy",
                "Transfer Site": "HA01",
                "Receive Site": "HA02",
                "Source Type": "RF過剩轉出",
                "Destination Type": "緊急缺貨",
            },
            {
                "Article": "123456789012",
                "Transfer Qty": 3,
                "Transfer OM": "Ivy",
                "Receive OM": "Ivy",
                "Transfer Site": "HA01",
                "Receive Site": "HA03",
                "Source Type": "RF過剩轉出",
                "Destination Type": "潛在缺貨",
            },
        ]

        stats = compute_transfer_statistics(recs)
        assert stats["total_recommendations"] == 2
        assert stats["total_transfer_qty"] == 8
        assert stats["unique_articles"] == 1
        assert stats["unique_oms"] == 1


if __name__ == "__main__":
    print("Running tests...")

    t = TestConfig()
    t.test_version_string()
    t.test_required_columns()
    t.test_integer_columns()
    print("  Config tests: PASSED")

    tp = TestTargetParser()
    tp.test_simple_target()
    tp.test_comma_target()
    tp.test_none_target()
    tp.test_zero_target()
    print("  TargetParser tests: PASSED")

    tpr = TestPredicates()
    tpr.test_hd_to_hk_restricted()
    print("  Predicates tests: PASSED")

    tmr = TestModeRegistry()
    tmr.test_all_24_modes()
    tmr.test_b_special_strategy()
    tmr.test_cross_om_modes()
    print("  ModeRegistry tests: PASSED")

    td = TestDataProcessor()
    td.test_preprocess_basic()
    td.test_article_normalization()
    td.test_outlier_correction()
    print("  DataProcessor tests: PASSED")

    tme = TestMatchingEngine()
    tme.setup_method()
    tme.test_compute_transfer_qty_basic()
    tme.test_compute_transfer_qty_limited_by_source()
    tme.test_can_transfer_self_to_self()
    tme.test_can_transfer_nd_dest_blocked()
    tme.test_single_piece_upgrade()
    print("  MatchingEngine tests: PASSED")

    tqc = TestQualityChecks()
    tqc.test_article_integrity()
    tqc.test_positive_qty()
    tqc.test_no_dual_role()
    tqc.test_article_length()
    print("  QualityChecks tests: PASSED")

    ttl = TestTransferLogic()
    ttl.test_sources_general_a_mode()
    ttl.test_sources_general_b_mode()
    ttl.test_dests_general()
    print("  TransferLogic tests: PASSED")

    ts = TestStatistics()
    ts.test_basic_stats()
    print("  Statistics tests: PASSED")

    print("\nAll tests passed!")
