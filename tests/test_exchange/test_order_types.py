"""Comprehensive tests for Extended Order Types.

Tests cover:
- TrailingStopOrder: trailing stop behavior for buy and sell
- BracketOrder: entry/TP/SL lifecycle with atomic unit
- OCOOrder: one-cancels-other behavior
- IcebergOrder: hidden quantity display and replenishment
- State machine: valid/invalid transitions
- TransitionRecord audit trail
- Edge cases and validation
"""

from __future__ import annotations

import pytest

from quant_nanggroe.exchange.order_types import (
    ExtendedOrderStatus,
    TrailingStopOrder,
    BracketOrder,
    BracketLegStatus,
    OCOOrder,
    IcebergOrder,
    StateTransitionError,
    TransitionRecord,
    transition_status,
    TERMINAL_STATES,
    _VALID_TRANSITIONS,
)


# ======================================================================
# 1. State machine transitions
# ======================================================================

class TestStateMachine:

    def test_valid_transition_pending_to_submitted(self):
        record = transition_status(ExtendedOrderStatus.PENDING, ExtendedOrderStatus.SUBMITTED, "test")
        assert isinstance(record, TransitionRecord)
        assert record.from_state == ExtendedOrderStatus.PENDING
        assert record.to_state == ExtendedOrderStatus.SUBMITTED
        assert record.reason == "test"

    def test_valid_transition_submitted_to_filled(self):
        record = transition_status(ExtendedOrderStatus.SUBMITTED, ExtendedOrderStatus.FILLED)
        assert record.to_state == ExtendedOrderStatus.FILLED

    def test_valid_transition_submitted_to_triggered(self):
        record = transition_status(ExtendedOrderStatus.SUBMITTED, ExtendedOrderStatus.TRIGGERED)
        assert record.to_state == ExtendedOrderStatus.TRIGGERED

    def test_valid_transition_triggered_to_filled(self):
        record = transition_status(ExtendedOrderStatus.TRIGGERED, ExtendedOrderStatus.FILLED)
        assert record.to_state == ExtendedOrderStatus.FILLED

    def test_invalid_transition_filled_to_submitted(self):
        with pytest.raises(StateTransitionError, match="Invalid state transition"):
            transition_status(ExtendedOrderStatus.FILLED, ExtendedOrderStatus.SUBMITTED)

    def test_invalid_transition_canceled_to_submitted(self):
        with pytest.raises(StateTransitionError):
            transition_status(ExtendedOrderStatus.CANCELED, ExtendedOrderStatus.SUBMITTED)

    def test_invalid_transition_rejected_to_pending(self):
        with pytest.raises(StateTransitionError):
            transition_status(ExtendedOrderStatus.REJECTED, ExtendedOrderStatus.PENDING)

    def test_partial_fill_to_partial_fill(self):
        """Partial fill can transition to another partial fill."""
        record = transition_status(
            ExtendedOrderStatus.PARTIALLY_FILLED,
            ExtendedOrderStatus.PARTIALLY_FILLED,
        )
        assert record.to_state == ExtendedOrderStatus.PARTIALLY_FILLED

    def test_terminal_states_no_transitions(self):
        for state in TERMINAL_STATES:
            assert len(_VALID_TRANSITIONS[state]) == 0

    def test_transition_record_has_timestamp(self):
        record = transition_status(
            ExtendedOrderStatus.PENDING,
            ExtendedOrderStatus.SUBMITTED,
        )
        assert record.timestamp is not None

    def test_state_transition_error_has_states(self):
        try:
            transition_status(ExtendedOrderStatus.FILLED, ExtendedOrderStatus.PENDING)
        except StateTransitionError as e:
            assert e.from_state == ExtendedOrderStatus.FILLED
            assert e.to_state == ExtendedOrderStatus.PENDING


# ======================================================================
# 2. TrailingStopOrder
# ======================================================================

class TestTrailingStopOrder:

    def test_create_sell_with_trail_amount(self):
        order = TrailingStopOrder(
            symbol="BTC/USDT",
            side="sell",
            quantity=1.0,
            trail_amount=500.0,
        )
        assert order.trail_amount == 500.0
        assert order.status == ExtendedOrderStatus.PENDING
        assert order.stop_price is None

    def test_create_buy_with_trail_percentage(self):
        order = TrailingStopOrder(
            symbol="BTC/USDT",
            side="buy",
            quantity=1.0,
            trail_percentage=5.0,
        )
        assert order.trail_percentage == 5.0

    def test_no_trail_param_raises(self):
        with pytest.raises(ValueError, match="Either trail_amount or trail_percentage"):
            TrailingStopOrder(symbol="BTC/USDT", side="sell", quantity=1.0)

    def test_sell_trailing_stop_trails_up(self):
        """For sell trailing stop, stop trails UP with price."""
        order = TrailingStopOrder(
            symbol="BTC/USDT", side="sell", quantity=1.0, trail_amount=500.0,
        )
        order.submit()

        # Price rises from 42000 to 43000
        updated = order.update_price(42000.0)
        assert updated
        assert order.peak_price == 42000.0
        assert order.stop_price == 41500.0

        updated = order.update_price(43000.0)
        assert updated
        assert order.peak_price == 43000.0
        assert order.stop_price == 42500.0

        # Price drops — stop holds
        updated = order.update_price(42800.0)
        assert not updated
        assert order.stop_price == 42500.0

    def test_buy_trailing_stop_trails_down(self):
        """For buy trailing stop, stop trails DOWN with price."""
        order = TrailingStopOrder(
            symbol="BTC/USDT", side="buy", quantity=1.0, trail_amount=500.0,
        )
        order.submit()

        # Price drops from 42000 to 41000
        updated = order.update_price(42000.0)
        assert updated
        assert order.peak_price == 42000.0
        assert order.stop_price == 42500.0

        updated = order.update_price(41000.0)
        assert updated
        assert order.peak_price == 41000.0
        assert order.stop_price == 41500.0

        # Price rises — stop holds
        updated = order.update_price(41200.0)
        assert not updated
        assert order.stop_price == 41500.0

    def test_sell_trailing_stop_triggered(self):
        """Trailing stop triggers when price hits stop."""
        order = TrailingStopOrder(
            symbol="BTC/USDT", side="sell", quantity=1.0, trail_amount=500.0,
        )
        order.submit()
        order.update_price(42000.0)  # stop at 41500
        assert not order.is_triggered

        # Price drops to stop
        order.update_price(41500.0)
        assert order.is_triggered
        assert order.status == ExtendedOrderStatus.TRIGGERED

    def test_buy_trailing_stop_triggered(self):
        """Buy trailing stop triggers when price rises to stop."""
        order = TrailingStopOrder(
            symbol="BTC/USDT", side="buy", quantity=1.0, trail_amount=500.0,
        )
        order.submit()
        order.update_price(42000.0)  # stop at 42500
        assert not order.is_triggered

        # Price rises to stop
        order.update_price(42500.0)
        assert order.is_triggered

    def test_trailing_with_percentage(self):
        order = TrailingStopOrder(
            symbol="BTC/USDT", side="sell", quantity=1.0, trail_percentage=2.0,
        )
        order.submit()
        order.update_price(50000.0)
        # 2% of 50000 = 1000
        assert order.stop_price == 49000.0

    def test_submit(self):
        order = TrailingStopOrder(
            symbol="BTC/USDT", side="sell", quantity=1.0, trail_amount=500.0,
        )
        order.submit()
        assert order.status == ExtendedOrderStatus.SUBMITTED

    def test_cancel(self):
        order = TrailingStopOrder(
            symbol="BTC/USDT", side="sell", quantity=1.0, trail_amount=500.0,
        )
        order.cancel()
        assert order.status == ExtendedOrderStatus.CANCELED

    def test_reject(self):
        order = TrailingStopOrder(
            symbol="BTC/USDT", side="sell", quantity=1.0, trail_amount=500.0,
        )
        order.reject()
        assert order.status == ExtendedOrderStatus.REJECTED

    def test_is_active(self):
        order = TrailingStopOrder(
            symbol="BTC/USDT", side="sell", quantity=1.0, trail_amount=500.0,
        )
        assert order.is_active
        order.cancel()
        assert not order.is_active

    def test_no_update_after_terminal(self):
        order = TrailingStopOrder(
            symbol="BTC/USDT", side="sell", quantity=1.0, trail_amount=500.0,
        )
        order.cancel()
        updated = order.update_price(50000.0)
        assert not updated

    def test_transitions_recorded(self):
        order = TrailingStopOrder(
            symbol="BTC/USDT", side="sell", quantity=1.0, trail_amount=500.0,
        )
        order.submit()
        assert len(order.transitions) == 1
        assert order.transitions[0].from_state == ExtendedOrderStatus.PENDING
        assert order.transitions[0].to_state == ExtendedOrderStatus.SUBMITTED


# ======================================================================
# 3. BracketOrder
# ======================================================================

class TestBracketOrder:

    def test_create_buy_bracket(self):
        bracket = BracketOrder(
            symbol="BTC/USDT",
            side="buy",
            quantity=1.0,
            entry_price=42000.0,
            take_profit_price=44000.0,
            stop_loss_price=41000.0,
        )
        assert bracket.entry_price == 42000.0
        assert bracket.take_profit_price == 44000.0
        assert bracket.stop_loss_price == 41000.0
        assert bracket.status == ExtendedOrderStatus.PENDING

    def test_create_sell_bracket(self):
        bracket = BracketOrder(
            symbol="BTC/USDT",
            side="sell",
            quantity=1.0,
            entry_price=42000.0,
            take_profit_price=40000.0,
            stop_loss_price=43000.0,
        )
        assert bracket.take_profit_price == 40000.0

    def test_buy_bracket_tp_below_entry_raises(self):
        with pytest.raises(ValueError, match="must be > entry"):
            BracketOrder(
                symbol="BTC/USDT", side="buy", quantity=1.0,
                entry_price=42000.0, take_profit_price=41000.0,
                stop_loss_price=40000.0,
            )

    def test_buy_bracket_sl_above_entry_raises(self):
        with pytest.raises(ValueError, match="must be < entry"):
            BracketOrder(
                symbol="BTC/USDT", side="buy", quantity=1.0,
                entry_price=42000.0, take_profit_price=44000.0,
                stop_loss_price=43000.0,
            )

    def test_sell_bracket_tp_above_entry_raises(self):
        with pytest.raises(ValueError, match="must be < entry"):
            BracketOrder(
                symbol="BTC/USDT", side="sell", quantity=1.0,
                entry_price=42000.0, take_profit_price=43000.0,
                stop_loss_price=44000.0,
            )

    def test_sell_bracket_sl_below_entry_raises(self):
        with pytest.raises(ValueError, match="must be > entry"):
            BracketOrder(
                symbol="BTC/USDT", side="sell", quantity=1.0,
                entry_price=42000.0, take_profit_price=40000.0,
                stop_loss_price=41000.0,
            )

    def test_market_entry_bracket(self):
        """Bracket with no entry price (market entry) should skip price validation."""
        bracket = BracketOrder(
            symbol="BTC/USDT", side="buy", quantity=1.0,
            take_profit_price=44000.0,
            stop_loss_price=41000.0,
        )
        assert bracket.entry_price is None

    def test_submit(self):
        bracket = BracketOrder(
            symbol="BTC/USDT", side="buy", quantity=1.0,
            entry_price=42000.0, take_profit_price=44000.0,
            stop_loss_price=41000.0,
        )
        bracket.submit()
        assert bracket.status == ExtendedOrderStatus.SUBMITTED
        assert bracket.entry_status == BracketLegStatus.SUBMITTED
        assert bracket.take_profit_status == BracketLegStatus.PENDING
        assert bracket.stop_loss_status == BracketLegStatus.PENDING

    def test_fill_entry_activates_tp_sl(self):
        bracket = BracketOrder(
            symbol="BTC/USDT", side="buy", quantity=1.0,
            entry_price=42000.0, take_profit_price=44000.0,
            stop_loss_price=41000.0,
        )
        bracket.submit()
        bracket.fill_entry()
        assert bracket.entry_status == BracketLegStatus.FILLED
        assert bracket.take_profit_status == BracketLegStatus.SUBMITTED
        assert bracket.stop_loss_status == BracketLegStatus.SUBMITTED
        assert bracket.status == ExtendedOrderStatus.TRIGGERED

    def test_fill_take_profit_cancels_sl(self):
        bracket = BracketOrder(
            symbol="BTC/USDT", side="buy", quantity=1.0,
            entry_price=42000.0, take_profit_price=44000.0,
            stop_loss_price=41000.0,
        )
        bracket.submit()
        bracket.fill_entry()
        bracket.fill_take_profit()
        assert bracket.take_profit_status == BracketLegStatus.FILLED
        assert bracket.stop_loss_status == BracketLegStatus.CANCELED
        assert bracket.status == ExtendedOrderStatus.FILLED

    def test_fill_stop_loss_cancels_tp(self):
        bracket = BracketOrder(
            symbol="BTC/USDT", side="buy", quantity=1.0,
            entry_price=42000.0, take_profit_price=44000.0,
            stop_loss_price=41000.0,
        )
        bracket.submit()
        bracket.fill_entry()
        bracket.fill_stop_loss()
        assert bracket.stop_loss_status == BracketLegStatus.FILLED
        assert bracket.take_profit_status == BracketLegStatus.CANCELED
        assert bracket.status == ExtendedOrderStatus.FILLED

    def test_cancel_before_fill(self):
        bracket = BracketOrder(
            symbol="BTC/USDT", side="buy", quantity=1.0,
            entry_price=42000.0, take_profit_price=44000.0,
            stop_loss_price=41000.0,
        )
        bracket.cancel()
        assert bracket.status == ExtendedOrderStatus.CANCELED
        assert bracket.entry_status == BracketLegStatus.CANCELED

    def test_cancel_after_fill(self):
        bracket = BracketOrder(
            symbol="BTC/USDT", side="buy", quantity=1.0,
            entry_price=42000.0, take_profit_price=44000.0,
            stop_loss_price=41000.0,
        )
        bracket.submit()
        bracket.fill_entry()
        bracket.cancel()
        assert bracket.take_profit_status == BracketLegStatus.CANCELED
        assert bracket.stop_loss_status == BracketLegStatus.CANCELED

    def test_risk_reward_ratio(self):
        bracket = BracketOrder(
            symbol="BTC/USDT", side="buy", quantity=1.0,
            entry_price=42000.0, take_profit_price=44000.0,
            stop_loss_price=41000.0,
        )
        rr = bracket.risk_reward_ratio
        assert rr is not None
        # Risk: 42000 - 41000 = 1000, Reward: 44000 - 42000 = 2000, RR = 2.0
        assert abs(rr - 2.0) < 0.01

    def test_risk_reward_ratio_no_entry(self):
        bracket = BracketOrder(
            symbol="BTC/USDT", side="buy", quantity=1.0,
            take_profit_price=44000.0, stop_loss_price=41000.0,
        )
        assert bracket.risk_reward_ratio is None

    def test_is_active(self):
        bracket = BracketOrder(
            symbol="BTC/USDT", side="buy", quantity=1.0,
            entry_price=42000.0, take_profit_price=44000.0,
            stop_loss_price=41000.0,
        )
        assert bracket.is_active
        bracket.submit()
        assert bracket.is_active
        bracket.fill_entry()
        assert bracket.is_active
        bracket.fill_take_profit()
        assert not bracket.is_active

    def test_fill_entry_without_submit_raises(self):
        bracket = BracketOrder(
            symbol="BTC/USDT", side="buy", quantity=1.0,
            entry_price=42000.0, take_profit_price=44000.0,
            stop_loss_price=41000.0,
        )
        with pytest.raises(StateTransitionError):
            bracket.fill_entry()

    def test_fill_tp_without_entry_raises(self):
        bracket = BracketOrder(
            symbol="BTC/USDT", side="buy", quantity=1.0,
            entry_price=42000.0, take_profit_price=44000.0,
            stop_loss_price=41000.0,
        )
        bracket.submit()
        with pytest.raises(StateTransitionError):
            bracket.fill_take_profit()


# ======================================================================
# 4. OCOOrder
# ======================================================================

class TestOCOOrder:

    def test_create_limit_limit_oco(self):
        oco = OCOOrder(
            symbol="BTC/USDT", side="sell", quantity=1.0,
            order_a_price=44000.0, order_b_price=41000.0,
        )
        assert oco.order_a_price == 44000.0
        assert oco.order_b_price == 41000.0
        assert oco.order_b_is_stop is False

    def test_create_limit_stop_oco(self):
        oco = OCOOrder(
            symbol="BTC/USDT", side="sell", quantity=1.0,
            order_a_price=44000.0, order_b_is_stop=True,
            order_b_stop_price=41000.0,
        )
        assert oco.order_b_is_stop is True
        assert oco.order_b_stop_price == 41000.0

    def test_limit_oco_requires_order_b_price(self):
        with pytest.raises(ValueError, match="order_b_price is required"):
            OCOOrder(
                symbol="BTC/USDT", side="sell", quantity=1.0,
                order_a_price=44000.0,
            )

    def test_stop_oco_requires_stop_price(self):
        with pytest.raises(ValueError, match="order_b_stop_price is required"):
            OCOOrder(
                symbol="BTC/USDT", side="sell", quantity=1.0,
                order_a_price=44000.0, order_b_is_stop=True,
            )

    def test_submit(self):
        oco = OCOOrder(
            symbol="BTC/USDT", side="sell", quantity=1.0,
            order_a_price=44000.0, order_b_price=41000.0,
        )
        oco.submit()
        assert oco.status == ExtendedOrderStatus.SUBMITTED
        assert oco.order_a_status == BracketLegStatus.SUBMITTED
        assert oco.order_b_status == BracketLegStatus.SUBMITTED

    def test_fill_a_cancels_b(self):
        oco = OCOOrder(
            symbol="BTC/USDT", side="sell", quantity=1.0,
            order_a_price=44000.0, order_b_price=41000.0,
        )
        oco.submit()
        oco.fill_a()
        assert oco.order_a_status == BracketLegStatus.FILLED
        assert oco.order_b_status == BracketLegStatus.CANCELED
        assert oco.status == ExtendedOrderStatus.FILLED

    def test_fill_b_cancels_a(self):
        oco = OCOOrder(
            symbol="BTC/USDT", side="sell", quantity=1.0,
            order_a_price=44000.0, order_b_price=41000.0,
        )
        oco.submit()
        oco.fill_b()
        assert oco.order_b_status == BracketLegStatus.FILLED
        assert oco.order_a_status == BracketLegStatus.CANCELED
        assert oco.status == ExtendedOrderStatus.FILLED

    def test_cancel(self):
        oco = OCOOrder(
            symbol="BTC/USDT", side="sell", quantity=1.0,
            order_a_price=44000.0, order_b_price=41000.0,
        )
        oco.cancel()
        assert oco.status == ExtendedOrderStatus.CANCELED
        assert oco.order_a_status == BracketLegStatus.CANCELED
        assert oco.order_b_status == BracketLegStatus.CANCELED

    def test_is_active(self):
        oco = OCOOrder(
            symbol="BTC/USDT", side="sell", quantity=1.0,
            order_a_price=44000.0, order_b_price=41000.0,
        )
        assert oco.is_active
        oco.submit()
        assert oco.is_active
        oco.fill_a()
        assert not oco.is_active

    def test_fill_without_submit_raises(self):
        oco = OCOOrder(
            symbol="BTC/USDT", side="sell", quantity=1.0,
            order_a_price=44000.0, order_b_price=41000.0,
        )
        with pytest.raises(StateTransitionError):
            oco.fill_a()

    def test_transitions_recorded(self):
        oco = OCOOrder(
            symbol="BTC/USDT", side="sell", quantity=1.0,
            order_a_price=44000.0, order_b_price=41000.0,
        )
        oco.submit()
        assert len(oco.transitions) == 1
        oco.fill_a()
        assert len(oco.transitions) == 2


# ======================================================================
# 5. IcebergOrder
# ======================================================================

class TestIcebergOrder:

    def test_create_iceberg(self):
        order = IcebergOrder(
            symbol="BTC/USDT", side="buy",
            total_quantity=100.0, display_quantity=10.0,
            price=42000.0,
        )
        assert order.total_quantity == 100.0
        assert order.display_quantity == 10.0
        assert order.current_display_quantity == 10.0

    def test_display_exceeds_total_raises(self):
        with pytest.raises(ValueError, match="display_quantity"):
            IcebergOrder(
                symbol="BTC/USDT", side="buy",
                total_quantity=5.0, display_quantity=10.0,
                price=42000.0,
            )

    def test_submit(self):
        order = IcebergOrder(
            symbol="BTC/USDT", side="buy",
            total_quantity=100.0, display_quantity=10.0,
            price=42000.0,
        )
        order.submit()
        assert order.status == ExtendedOrderStatus.SUBMITTED

    def test_fill_portion(self):
        order = IcebergOrder(
            symbol="BTC/USDT", side="buy",
            total_quantity=100.0, display_quantity=10.0,
            price=42000.0,
        )
        order.submit()
        filled = order.fill_portion(5.0)
        assert filled == 5.0
        assert order.filled_quantity == 5.0
        assert order.current_display_quantity == 5.0

    def test_fill_replenishes_display(self):
        order = IcebergOrder(
            symbol="BTC/USDT", side="buy",
            total_quantity=30.0, display_quantity=10.0,
            price=42000.0,
        )
        order.submit()

        # Fill entire visible portion
        filled = order.fill_portion(10.0)
        assert filled == 10.0
        assert order.filled_quantity == 10.0
        # Should replenish from hidden
        assert order.current_display_quantity == 10.0

    def test_fill_to_completion(self):
        order = IcebergOrder(
            symbol="BTC/USDT", side="buy",
            total_quantity=20.0, display_quantity=10.0,
            price=42000.0,
        )
        order.submit()

        # Fill first display
        order.fill_portion(10.0)
        assert order.filled_quantity == 10.0

        # Fill remaining
        order.fill_portion(10.0)
        assert order.filled_quantity == 20.0
        assert order.status == ExtendedOrderStatus.FILLED
        assert order.current_display_quantity == 0.0

    def test_fill_capped_at_visible(self):
        order = IcebergOrder(
            symbol="BTC/USDT", side="buy",
            total_quantity=100.0, display_quantity=10.0,
            price=42000.0,
        )
        order.submit()

        # Try to fill more than visible
        filled = order.fill_portion(50.0)
        assert filled == 10.0  # Capped at display quantity

    def test_fill_negative_raises(self):
        order = IcebergOrder(
            symbol="BTC/USDT", side="buy",
            total_quantity=100.0, display_quantity=10.0,
            price=42000.0,
        )
        order.submit()
        with pytest.raises(ValueError, match="positive"):
            order.fill_portion(-1.0)

    def test_fill_zero_raises(self):
        order = IcebergOrder(
            symbol="BTC/USDT", side="buy",
            total_quantity=100.0, display_quantity=10.0,
            price=42000.0,
        )
        order.submit()
        with pytest.raises(ValueError, match="positive"):
            order.fill_portion(0.0)

    def test_fill_after_filled_raises(self):
        order = IcebergOrder(
            symbol="BTC/USDT", side="buy",
            total_quantity=20.0, display_quantity=10.0,
            price=42000.0,
        )
        order.submit()
        order.fill_portion(10.0)
        order.fill_portion(10.0)
        assert order.status == ExtendedOrderStatus.FILLED

        with pytest.raises(ValueError, match="Cannot fill"):
            order.fill_portion(5.0)

    def test_fill_after_cancel_raises(self):
        order = IcebergOrder(
            symbol="BTC/USDT", side="buy",
            total_quantity=100.0, display_quantity=10.0,
            price=42000.0,
        )
        order.cancel()
        with pytest.raises(ValueError, match="Cannot fill"):
            order.fill_portion(5.0)

    def test_cancel(self):
        order = IcebergOrder(
            symbol="BTC/USDT", side="buy",
            total_quantity=100.0, display_quantity=10.0,
            price=42000.0,
        )
        order.cancel()
        assert order.status == ExtendedOrderStatus.CANCELED

    def test_hidden_quantity(self):
        order = IcebergOrder(
            symbol="BTC/USDT", side="buy",
            total_quantity=100.0, display_quantity=10.0,
            price=42000.0,
        )
        assert order.hidden_quantity == 90.0

    def test_hidden_quantity_after_partial_fill(self):
        order = IcebergOrder(
            symbol="BTC/USDT", side="buy",
            total_quantity=100.0, display_quantity=10.0,
            price=42000.0,
        )
        order.submit()
        order.fill_portion(5.0)
        # filled=5, display=5, total=100, hidden = 100 - 5 - 5 = 90
        assert order.hidden_quantity == 90.0

    def test_remaining_quantity(self):
        order = IcebergOrder(
            symbol="BTC/USDT", side="buy",
            total_quantity=100.0, display_quantity=10.0,
            price=42000.0,
        )
        assert order.remaining_quantity == 100.0

    def test_remaining_quantity_after_fill(self):
        order = IcebergOrder(
            symbol="BTC/USDT", side="buy",
            total_quantity=100.0, display_quantity=10.0,
            price=42000.0,
        )
        order.submit()
        order.fill_portion(10.0)
        assert order.remaining_quantity == 90.0

    def test_fill_progress(self):
        order = IcebergOrder(
            symbol="BTC/USDT", side="buy",
            total_quantity=100.0, display_quantity=10.0,
            price=42000.0,
        )
        assert order.fill_progress == 0.0
        order.submit()
        # Fill is capped at display_quantity=10, so fill 10 then get another 10
        order.fill_portion(10.0)  # fills first display, replenishes
        order.fill_portion(10.0)  # fills second display, replenishes
        order.fill_portion(5.0)   # partial fill of third display
        # Total filled: 25 out of 100
        assert abs(order.fill_progress - 0.25) < 0.01

    def test_is_active(self):
        order = IcebergOrder(
            symbol="BTC/USDT", side="buy",
            total_quantity=100.0, display_quantity=10.0,
            price=42000.0,
        )
        assert order.is_active
        order.cancel()
        assert not order.is_active

    def test_display_equals_total(self):
        """Display quantity equal to total should work (no hidden portion)."""
        order = IcebergOrder(
            symbol="BTC/USDT", side="buy",
            total_quantity=10.0, display_quantity=10.0,
            price=42000.0,
        )
        assert order.hidden_quantity == 0.0
        assert order.current_display_quantity == 10.0


# ======================================================================
# 6. ExtendedOrderStatus enum
# ======================================================================

class TestExtendedOrderStatus:

    def test_all_statuses(self):
        expected = [
            "pending", "submitted", "partially_filled", "filled",
            "canceled", "rejected", "expired", "triggered", "error",
        ]
        actual = [s.value for s in ExtendedOrderStatus]
        for e in expected:
            assert e in actual

    def test_triggered_status(self):
        assert ExtendedOrderStatus.TRIGGERED.value == "triggered"


# ======================================================================
# 7. Integration / lifecycle tests
# ======================================================================

class TestFullLifecycle:

    def test_trailing_stop_full_lifecycle(self):
        """Full lifecycle: create → submit → price update → trigger."""
        order = TrailingStopOrder(
            symbol="BTC/USDT", side="sell", quantity=1.0,
            trail_amount=1000.0,
        )
        assert order.status == ExtendedOrderStatus.PENDING

        order.submit()
        assert order.status == ExtendedOrderStatus.SUBMITTED

        order.update_price(50000.0)
        assert order.peak_price == 50000.0
        assert order.stop_price == 49000.0

        order.update_price(52000.0)
        assert order.stop_price == 51000.0

        # Price drops to stop
        order.update_price(51000.0)
        assert order.is_triggered
        assert order.status == ExtendedOrderStatus.TRIGGERED

        # Audit trail should have 2 transitions
        assert len(order.transitions) == 2

    def test_bracket_full_lifecycle_tp(self):
        """Full bracket lifecycle ending with take-profit."""
        bracket = BracketOrder(
            symbol="BTC/USDT", side="buy", quantity=1.0,
            entry_price=42000.0, take_profit_price=44000.0,
            stop_loss_price=41000.0,
        )
        bracket.submit()
        bracket.fill_entry()
        bracket.fill_take_profit()

        assert bracket.status == ExtendedOrderStatus.FILLED
        assert bracket.entry_status == BracketLegStatus.FILLED
        assert bracket.take_profit_status == BracketLegStatus.FILLED
        assert bracket.stop_loss_status == BracketLegStatus.CANCELED

    def test_bracket_full_lifecycle_sl(self):
        """Full bracket lifecycle ending with stop-loss."""
        bracket = BracketOrder(
            symbol="BTC/USDT", side="buy", quantity=1.0,
            entry_price=42000.0, take_profit_price=44000.0,
            stop_loss_price=41000.0,
        )
        bracket.submit()
        bracket.fill_entry()
        bracket.fill_stop_loss()

        assert bracket.status == ExtendedOrderStatus.FILLED
        assert bracket.stop_loss_status == BracketLegStatus.FILLED
        assert bracket.take_profit_status == BracketLegStatus.CANCELED

    def test_oco_full_lifecycle(self):
        """Full OCO lifecycle."""
        oco = OCOOrder(
            symbol="BTC/USDT", side="sell", quantity=1.0,
            order_a_price=44000.0, order_b_price=41000.0,
        )
        oco.submit()
        oco.fill_a()

        assert oco.status == ExtendedOrderStatus.FILLED
        assert oco.order_a_status == BracketLegStatus.FILLED
        assert oco.order_b_status == BracketLegStatus.CANCELED

    def test_iceberg_full_lifecycle(self):
        """Full iceberg lifecycle with multiple fills."""
        order = IcebergOrder(
            symbol="BTC/USDT", side="buy",
            total_quantity=30.0, display_quantity=10.0,
            price=42000.0,
        )
        order.submit()

        # Fill in 3 rounds
        order.fill_portion(10.0)
        assert order.filled_quantity == 10.0
        assert order.current_display_quantity == 10.0

        order.fill_portion(10.0)
        assert order.filled_quantity == 20.0
        assert order.current_display_quantity == 10.0

        order.fill_portion(10.0)
        assert order.filled_quantity == 30.0
        assert order.status == ExtendedOrderStatus.FILLED
        assert order.current_display_quantity == 0.0
