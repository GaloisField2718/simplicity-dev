"""
BRC-20 consensus rule validation service.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, BigInteger
from src.utils.exceptions import BRC20ErrorCodes, ValidationResult
from src.utils.amounts import (
    is_valid_amount,
    is_amount_greater_than,
    is_amount_greater_equal,
    add_amounts,
    subtract_amounts,
)
from src.utils.bitcoin import (
    extract_address_from_script,
    is_op_return_script,
    is_standard_output,
)
from src.models.deploy import Deploy
from src.models.balance import Balance


class BRC20Validator:
    """Validate operations according to consensus rules"""

    def __init__(self, db_session: Session):
        """
        Initialize validator

        Args:
            db_session: Database session for queries
        """
        self.db = db_session

    def validate_deploy(
        self, operation: Dict[str, Any], intermediate_deploys: Optional[Dict] = None
    ) -> ValidationResult:
        """
        Validate deploy operation with intermediate state check

        Args:
            operation: Parsed deploy operation
            intermediate_deploys: Intermediate deploy state for current block

        Returns:
            ValidationResult: Validation result
        """
        ticker = operation.get("tick").upper()
        max_supply = operation.get("m")
        limit_per_op = operation.get("l")

        if intermediate_deploys is not None and ticker in intermediate_deploys:
            return ValidationResult(
                False,
                BRC20ErrorCodes.TICKER_ALREADY_EXISTS,
                f"Ticker '{ticker}' already deployed in this block",
            )

        existing_deploy = self.db.query(Deploy).filter(Deploy.ticker.ilike(ticker)).first()
        if existing_deploy:
            return ValidationResult(
                False,
                BRC20ErrorCodes.TICKER_ALREADY_EXISTS,
                f"Ticker '{ticker}' already deployed",
            )

        if not is_valid_amount(max_supply):
            return ValidationResult(
                False,
                BRC20ErrorCodes.INVALID_AMOUNT,
                f"Invalid max supply: {max_supply}",
            )

        if limit_per_op is not None:
            if not is_valid_amount(limit_per_op):
                return ValidationResult(
                    False,
                    BRC20ErrorCodes.INVALID_AMOUNT,
                    f"Invalid limit per operation: {limit_per_op}",
                )

        return ValidationResult(True)

    def validate_mint(
        self,
        operation: Dict[str, Any],
        deploy: Optional[Deploy],
        intermediate_total_minted: Optional[Dict] = None,
    ) -> ValidationResult:
        """
        Validate mint operation with intermediate state support

        Args:
            operation: Parsed mint operation
            deploy: Deploy record for the ticker
            intermediate_total_minted: Intermediate total minted state for current block

        Returns:
            ValidationResult: Validation result
        """
        ticker = operation.get("tick")
        amount = operation.get("amt")

        if deploy is None:
            return ValidationResult(
                False,
                BRC20ErrorCodes.TICKER_NOT_DEPLOYED,
                f"Ticker '{ticker}' not deployed",
            )

        if not is_valid_amount(amount):
            return ValidationResult(False, BRC20ErrorCodes.INVALID_AMOUNT, f"Invalid mint amount: {amount}")

        if deploy.limit_per_op is not None:
            if is_amount_greater_than(amount, deploy.limit_per_op):
                return ValidationResult(
                    False,
                    BRC20ErrorCodes.EXCEEDS_MINT_LIMIT,
                    f"Mint amount {amount} exceeds limit {deploy.limit_per_op}",
                )

        overflow_result = self.validate_mint_overflow(
            ticker, amount, deploy, intermediate_total_minted=intermediate_total_minted
        )
        if not overflow_result.is_valid:
            return overflow_result

        return ValidationResult(True)

    def validate_transfer(
        self,
        operation: Dict[str, Any],
        sender_balance: str,
        deploy: Optional[Deploy] = None,
        intermediate_balances=None,
    ) -> ValidationResult:
        """
        Validate transfer operation

        Args:
            operation: Parsed transfer operation
            sender_balance: Sender's current balance as string
            deploy: Deploy record (optional, for additional checks)

        Returns:
            ValidationResult: Validation result

        CRITICAL RULES:
        - Ticker must exist
        - sender_balance ≥ amount
        - NO limit_per_op verification (limit only applies to mints)
        """
        ticker = operation.get("tick")
        amount = operation.get("amt")

        if deploy is None:
            return ValidationResult(
                False,
                BRC20ErrorCodes.TICKER_NOT_DEPLOYED,
                f"Ticker '{ticker}' not deployed",
            )

        if not is_valid_amount(amount):
            return ValidationResult(
                False,
                BRC20ErrorCodes.INVALID_AMOUNT,
                f"Invalid transfer amount: {amount}",
            )

        if not is_amount_greater_equal(sender_balance, amount):
            return ValidationResult(
                False,
                BRC20ErrorCodes.INSUFFICIENT_BALANCE,
                f"Insufficient balance: {sender_balance} < {amount}",
            )

        return ValidationResult(True)

    def validate_output_addresses(
        self, tx_outputs: List[Dict[str, Any]], operation_type: str = None
    ) -> ValidationResult:
        """
        Validate transaction outputs based on operation type

        Args:
            tx_outputs: List of transaction outputs
            operation_type: Type of operation ('deploy', 'mint', 'transfer')

        Returns:
            ValidationResult: Validation result

        RULES:
        - Deploy: NO output validation required (can have only OP_RETURN)
        - Mint/Transfer: Must have at least one standard output
        - Accept P2PKH, P2SH, P2WPKH, P2WSH, P2TR
        - NO dust limit constraint
        """
        if not isinstance(tx_outputs, list) or not tx_outputs:
            return ValidationResult(
                False,
                BRC20ErrorCodes.NO_STANDARD_OUTPUT,
                "Invalid or empty transaction outputs",
            )

        if operation_type == "deploy":
            return ValidationResult(True)

        # ✅ FIX: Filter None values before checking
        has_standard_output = any(
            out is not None
            and out.get("scriptPubKey", {}).get("type") != "nulldata"
            and not out.get("scriptPubKey", {}).get("hex", "").startswith("6a")
            for out in tx_outputs
        )

        if not has_standard_output:
            return ValidationResult(
                False,
                BRC20ErrorCodes.NO_STANDARD_OUTPUT,
                "No standard outputs found in transaction",
            )

        return ValidationResult(True)

    def get_output_after_op_return_address(self, tx_outputs: List[Dict[str, Any]]) -> Optional[str]:
        """
        Get the address of the output AFTER the OP_RETURN for token allocation

        Args:
            tx_outputs: List of transaction outputs

        Returns:
            Optional[str]: Address of output after OP_RETURN, None if not found

        RULE: Tokens are allocated to the output AFTER the OP_RETURN
        """
        op_return_index = None
        for i, vout in enumerate(tx_outputs):
            if not isinstance(vout, dict):
                continue

            script_pub_key = vout.get("scriptPubKey", {})
            if not isinstance(script_pub_key, dict):
                continue

            if script_pub_key.get("type") == "nulldata" or (
                script_pub_key.get("hex", "") and script_pub_key.get("hex", "").startswith("6a")
            ):
                op_return_index = i
                break

        if op_return_index is None or op_return_index + 1 >= len(tx_outputs):
            return None

        next_output = tx_outputs[op_return_index + 1]
        # ✅ FIX: Check if next_output is None
        if next_output is None or not isinstance(next_output, dict):
            return None

        script_pub_key = next_output.get("scriptPubKey", {})

        if script_pub_key.get("type") == "nulldata" or (
            script_pub_key.get("hex", "") and script_pub_key.get("hex", "").startswith("6a")
        ):
            return None

        addresses = script_pub_key.get("addresses", [])
        if addresses and len(addresses) > 0:
            return addresses[0]
        elif script_pub_key.get("address", None):
            return script_pub_key.get("address")
        else:
            script_hex = script_pub_key.get("hex", "")
            if script_hex and not is_op_return_script(script_hex) and is_standard_output(script_hex):
                address = extract_address_from_script(script_hex)
                if address:
                    return address

        return None

    def get_current_supply(self, ticker: str) -> str:
        """
        Get current total supply for a ticker

        Args:
            ticker: Token ticker

        Returns:
            str: Current total supply as string
        """
        total = (
            self.db.query(func.coalesce(func.sum(cast(Balance.balance, BigInteger)), 0))
            .filter(Balance.ticker.ilike(ticker))
            .scalar()
        )

        return str(total or 0)

    def get_total_minted(self, ticker: str, intermediate_total_minted: Optional[Dict] = None) -> str:
        """
        Get current total minted amount for ticker, prioritizing intermediate state

        Args:
            ticker: Token ticker
            intermediate_total_minted: Intermediate total minted state for current block

        Returns:
            str: Total minted amount as string
        """
        from src.models.transaction import BRC20Operation

        normalized_ticker = ticker.upper()

        if intermediate_total_minted is not None and normalized_ticker in intermediate_total_minted:
            return intermediate_total_minted[normalized_ticker]

        db_total = (
            self.db.query(func.coalesce(func.sum(cast(BRC20Operation.amount, BigInteger)), "0"))
            .filter(
                BRC20Operation.ticker.ilike(normalized_ticker),
                BRC20Operation.operation == "mint",
                BRC20Operation.is_valid.is_(True),
            )
            .scalar()
        )

        return str(db_total or "0")

    def validate_mint_overflow(
        self,
        ticker: str,
        mint_amount: str,
        deploy: Deploy,
        intermediate_total_minted=None,
    ) -> ValidationResult:
        """
        CRITICAL: Validate that mint doesn't exceed max supply

        ALGORITHM:
        1. Get current total minted for ticker (from valid mint operations)
        2. Add proposed mint amount to current total
        3. Compare new total against max supply
        4. REJECT if new total > max supply

        Args:
            ticker: Token ticker
            mint_amount: Amount to mint
            deploy: Deploy record with max_supply

        Returns:
            ValidationResult: Valid if mint doesn't exceed max supply
        """
        current_total_minted = self.get_total_minted(ticker, intermediate_total_minted=intermediate_total_minted)

        try:
            proposed_total_after_mint = add_amounts(current_total_minted, mint_amount)
        except ValueError as e:
            return ValidationResult(
                False,
                BRC20ErrorCodes.INVALID_AMOUNT,
                f"Amount calculation error: {str(e)}",
            )

        if is_amount_greater_than(proposed_total_after_mint, deploy.max_supply):
            excess_amount = subtract_amounts(proposed_total_after_mint, deploy.max_supply)

            return ValidationResult(
                False,
                BRC20ErrorCodes.EXCEEDS_MAX_SUPPLY,
                f"Mint would exceed max supply. "
                f"Current: {current_total_minted}, "
                f"Mint: {mint_amount}, "
                f"Proposed: {proposed_total_after_mint}, "
                f"Max: {deploy.max_supply}, "
                f"Excess: {excess_amount}",
            )

        return ValidationResult(True)

    def get_first_standard_output_address(self, tx_outputs: list) -> str | None:
        """
        Get the first standard (non-OP_RETURN) output address from transaction outputs.

        Args:
            tx_outputs: List of transaction outputs

        Returns:
            The first standard output address or None if no standard output found
        """
        return self.get_output_after_op_return_address(tx_outputs)

    def get_balance(self, address: str, ticker: str, intermediate_balances: Optional[Dict] = None) -> str:
        """
        Get balance for specific address and ticker, prioritizing intermediate state

        Args:
            address: Bitcoin address
            ticker: Token ticker
            intermediate_balances: Intermediate balance state for current block

        Returns:
            str: Balance as string (0 if not found)
        """
        normalized_ticker = ticker.upper()
        key = (address, normalized_ticker)

        if intermediate_balances is not None and key in intermediate_balances:
            return intermediate_balances[key]

        balance_record = (
            self.db.query(Balance).filter(Balance.address == address, Balance.ticker.ilike(normalized_ticker)).first()
        )

        return balance_record.balance if balance_record else "0"

    def get_deploy_record(self, ticker: str, intermediate_deploys: Optional[Dict] = None) -> Optional[Deploy]:
        """
        Get deploy record for ticker, prioritizing intermediate state

        Args:
            ticker: Token ticker
            intermediate_deploys: Intermediate deploy state for current block

        Returns:
            Optional[Deploy]: Deploy record if exists
        """
        normalized_ticker = ticker.upper()

        if intermediate_deploys is not None and normalized_ticker in intermediate_deploys:
            return intermediate_deploys[normalized_ticker]

        return self.db.query(Deploy).filter(Deploy.ticker.ilike(normalized_ticker)).first()

    def validate_complete_operation(
        self,
        operation: Dict[str, Any],
        tx_outputs: List[Dict[str, Any]],
        sender_address: Optional[str] = None,
        intermediate_balances: Optional[Dict] = None,
        intermediate_total_minted: Optional[Dict] = None,
        intermediate_deploys: Optional[Dict] = None,
    ) -> ValidationResult:
        """
        Validate complete BRC-20 operation with all consensus rules

        Args:
            operation: Parsed BRC-20 operation
            tx_outputs: Transaction outputs
            sender_address: Sender address (for transfers)
            intermediate_balances: intermediate balances
            intermediate_total_minted: intermediate total minted
            intermediate_deploys: intermediate deploys

        Returns:
            ValidationResult: Complete validation result
        """
        op_type = operation.get("op")
        ticker = operation.get("tick")

        # Validate output addresses with operation type
        output_validation = self.validate_output_addresses(tx_outputs, op_type)
        if not output_validation.is_valid:
            return output_validation

        # For mint and transfer, ensure there's a valid recipient after OP_RETURN
        if op_type in ["mint", "transfer"]:
            recipient_address = self.get_output_after_op_return_address(tx_outputs)
            if not recipient_address:
                return ValidationResult(
                    False,
                    BRC20ErrorCodes.NO_STANDARD_OUTPUT,
                    f"No valid recipient found after OP_RETURN for {op_type} operation",
                )

        # Get deploy record
        deploy = self.get_deploy_record(ticker, intermediate_deploys=intermediate_deploys)

        if op_type == "deploy":
            return self.validate_deploy(operation, intermediate_deploys=intermediate_deploys)

        elif op_type == "mint":
            # Use corrected validate_mint that calculates current supply internally
            return self.validate_mint(operation, deploy, intermediate_total_minted=intermediate_total_minted)

        elif op_type == "transfer":
            if sender_address is None:
                return ValidationResult(
                    False,
                    BRC20ErrorCodes.NO_STANDARD_OUTPUT,
                    "Sender address required for transfer validation",
                )

            sender_balance = self.get_balance(sender_address, ticker, intermediate_balances=intermediate_balances)
            return self.validate_transfer(
                operation,
                sender_balance,
                deploy,
                intermediate_balances=intermediate_balances,
            )

        else:
            return ValidationResult(
                False,
                BRC20ErrorCodes.INVALID_OPERATION,
                f"Unknown operation type: {op_type}",
            )
