# Hybrid-Ready Storage Architecture (v1.0)

This document outlines the "Local-First, Hybrid-Later" strategy implemented in Quant Nanggroe AI.

## 1. Core Philosophy
The system is designed to be fully functional offline and in a browser-only environment (Local-First), while providing a seamless upgrade path to cloud-based synchronization (Hybrid).

## 2. The Storage Engine (`services/storage_manager.ts`)
The `StorageManager` is the brain of the persistence layer. It uses the **Adapter Pattern** to abstract the underlying storage mechanism.

### Available Adapters:
- **IndexedDBAdapter (Default)**: Used for high-capacity local storage. Ideal for market data, portfolios, and knowledge base nodes.
- **LocalStorageAdapter**: Used for small, persistent settings like themes or layout preferences.
- **CloudAdapter (Future)**: A placeholder for Supabase/Firebase/AWS S3 integration.

## 3. Data Flow
1. **Application Logic** calls `BrowserFS` or `KnowledgeBase`.
2. **Service Layer** performs operations on the `BrowserFS` (Virtual File System).
3. **Storage Layer** (`StorageManager`) persists the data using the primary adapter (IndexedDB).
4. **Hybrid Sync (Upcoming)**: When enabled, `StorageManager` will automatically broadcast changes to registered Cloud Adapters.

## 4. Local File Ownership
To fulfill the requirement of "Local File Storage", the system provides an explicit **Backup & Restore** mechanism in the **Control Center**:
- **Backup**: Serializes the entire IndexedDB state into a `.json` file and initiates a browser download.
- **Restore**: Parses a `.json` file and re-hydrates the local storage engine.

## 5. Security & Privacy
By default, no data leaves the user's device. All AI research and trading simulations are stored locally within the browser's sandboxed `IndexedDB`.

---
*Documentation v1.0 | 2026-01-06*

---

> **Contact:** Mulky Malikul Dhaher — [mulkymalikuldhaher@email.com](mailto:mulkymalikuldhaher@email.com)
>
> **Disclaimer:** This project is for Education Purpose only. Risiko apapun tidak kita tanggung. (We are not responsible for any risks or damages.)
