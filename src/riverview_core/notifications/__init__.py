# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/notifications/__init__.py
# Component: NOTIFICATION-DELIVERY
# Revision: 1.0.1
# Purpose: Export durable notification projection, receipts, and push delivery manager
# Execution Model: Continuous dispatcher plus request-driven receipt operations
# Observability: PostgreSQL notification rows, event ledger, and service health
# Dependencies: PostgreSQL 16; Psycopg 3; CME migration 0005
# Authority: Records notices and client receipt only; never resolves decisions
# Changed: 2026-10-18 UTC | RV-IPHONE-NOTIFICATIONS-001 | Export provider delivery contract
# Contracts: docs/components/NOTIFICATION_DELIVERY.md
# Tests: tests/test_notifications.py
# History: New file; Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Durable attention notification delivery and receipt recording."""

from .dispatcher import NotificationDispatcher
from .service import (NotificationConflict, NotificationNotFound,
                      NotificationService, NotificationUnavailable)
from .push import (HttpPushTransport, NotificationDeliveryManager,
                   PushConfigurationError, PushConfig, PushProviderError)

__all__ = ["HttpPushTransport", "NotificationConflict", "NotificationDeliveryManager",
           "NotificationDispatcher", "NotificationNotFound", "NotificationService",
           "NotificationUnavailable", "PushConfigurationError", "PushConfig",
           "PushProviderError"]
