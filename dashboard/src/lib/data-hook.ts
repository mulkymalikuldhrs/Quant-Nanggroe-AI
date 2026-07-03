import { monitorApi, tradingApi, backtestApi, colonyApi, ecosystemApi } from "./api-client";

export async function fetchMonitorSummary() {
  try {
    return await monitorApi.getSummary();
  } catch {
    return null;
  }
}

export async function fetchAgents() {
  try {
    return await monitorApi.getHealth();
  } catch {
    return null;
  }
}

export async function fetchPortfolio() {
  try {
    return await monitorApi.getPnl();
  } catch {
    return null;
  }
}

export async function fetchMarket() {
  try {
    return await monitorApi.getRegime();
  } catch {
    return null;
  }
}

export async function fetchRisk() {
  try {
    return await monitorApi.getRisk();
  } catch {
    return null;
  }
}

export async function fetchPositions() {
  try {
    return await tradingApi.getPositions();
  } catch {
    return null;
  }
}

export async function fetchStrategies() {
  try {
    return await backtestApi.getStrategies();
  } catch {
    return [];
  }
}

export async function fetchColonies() {
  try {
    return await colonyApi.list();
  } catch {
    return [];
  }
}

export async function fetchExchanges() {
  try {
    return await ecosystemApi.exchangeList();
  } catch {
    return [];
  }
}