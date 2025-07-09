#!/usr/bin/env python3
"""
This script verifies that all components are properly configured.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_imports():
    """Test that all critical modules can be imported."""
    print("Testing imports...")
    try:
        import importlib
        importlib.import_module("models.base")
        print("✅ Base model imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Base model: {e}")
        assert False
    try:
        import importlib
        importlib.import_module("models.deploy")
        print("✅ Deploy model imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Deploy model: {e}")
        assert False
    try:
        import importlib
        importlib.import_module("models.balance")
        print("✅ Balance model imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Balance model: {e}")
        assert False
    try:
        import importlib
        importlib.import_module("models.transaction")
        print("✅ BRC20Operation model imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import BRC20Operation model: {e}")
        assert False
    try:
        import importlib
        importlib.import_module("models.block")
        print("✅ ProcessedBlock model imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import ProcessedBlock model: {e}")
        assert False
    try:
        import importlib
        importlib.import_module("config")
        print("✅ Configuration imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import configuration: {e}")
        assert False
    try:
        import importlib
        importlib.import_module("database.connection")
        print("✅ Database connection imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import database connection: {e}")
        assert False
    # No return


def test_critical_rules_compliance():
    """Test compliance with critical rules."""
    print("\nTesting critical rules compliance...")

    from models.deploy import Deploy
    from models.balance import Balance
    from models.transaction import BRC20Operation
    from datetime import datetime

    # Test 1: String amounts
    deploy = Deploy(
        ticker="TEST",
        max_supply="1000000",  # Must be string
        limit_per_op="1000",  # Must be string
        deploy_txid="abc123",
        deploy_height=800000,
        deploy_timestamp=datetime.now(),
    )

    if not isinstance(deploy.max_supply, str):
        print("❌ max_supply is not a string")
        assert False
    print("✅ Deploy.max_supply is string type")

    if not isinstance(deploy.limit_per_op, str):
        print("❌ limit_per_op is not a string")
        assert False
    print("✅ Deploy.limit_per_op is string type")

    # Test 2: Balance as string
    balance = Balance(
        address="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
        ticker="TEST",
        balance="5000",  # Must be string
    )

    if not isinstance(balance.balance, str):
        print("❌ balance is not a string")
        assert False
    print("✅ Balance.balance is string type")

    # Test 3: ticker can be NULL
    operation = BRC20Operation(
        txid="test123",
        vout_index=0,
        operation="invalid",
        ticker=None,  # NULL is allowed for failed parsing
        amount=None,
        from_address=None,
        to_address=None,
        block_height=800000,
        block_hash="000000000000000000000123",
        tx_index=0,
        timestamp=datetime.now(),
        is_valid=False,
        error_code="INVALID_JSON",
        error_message="Malformed JSON",
        raw_op_return="6a4c50...",
        parsed_json=None,
    )

    if operation.ticker is not None:
        print("❌ ticker should be NULL for failed parsing")
        assert False
    print("✅ BRC20Operation.ticker can be NULL")

    # Test 4: ticker "0" is valid
    valid_operation = BRC20Operation(
        txid="test456",
        vout_index=0,
        operation="deploy",
        ticker="0",  # "0" is a valid ticker
        amount=None,
        from_address=None,
        to_address=None,
        block_height=800000,
        block_hash="000000000000000000000123",
        tx_index=1,
        timestamp=datetime.now(),
        is_valid=True,
        error_code=None,
        error_message=None,
        raw_op_return="6a4c50...",
        parsed_json='{"p":"brc-20","op":"deploy","tick":"0","m":"1000"}',
    )

    if valid_operation.ticker != "0":
        print("❌ ticker '0' should be valid")
        assert False
    print("✅ BRC20Operation.ticker '0' is valid")

    assert True


def test_database_schema():
    """Test database schema creation."""
    print("\nTesting database schema...")
    try:
        from models.base import Base
        # Check that all tables are defined in metadata
        table_names = list(Base.metadata.tables.keys())
        expected_tables = [
            "deploys",
            "balances",
            "brc20_operations",
            "processed_blocks",
        ]
        for table in expected_tables:
            if table not in table_names:
                print(f"❌ Missing table: {table}")
                assert False
            print(f"✅ Table '{table}' defined in schema")
        assert True
    except Exception as e:
        print(f"❌ Database schema test failed: {e}")
        assert False


def main():
    """Run all validation tests."""
    print("🚀 Universal BRC-20 Indexer - Phase 1 Infrastructure Validation")
    print("=" * 60)

    all_passed = True

    # Test imports
    if not test_imports():
        all_passed = False

    # Test critical rules compliance
    if not test_critical_rules_compliance():
        all_passed = False

    # Test database schema
    if not test_database_schema():
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED - Phase 1 Infrastructure is ready!")
        print("\nNext steps:")
        print("1. Start PostgreSQL: docker-compose up -d")
        print("2. Run migrations: alembic upgrade head")
        print("3. Proceed to Phase 2: Parsing and Validation")
    else:
        print("❌ SOME TESTS FAILED - Please fix issues before proceeding")
        sys.exit(1)


if __name__ == "__main__":
    main()
