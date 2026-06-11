
export enum MessageRole {
  USER = 'user',
  MODEL = 'model',
  SYSTEM = 'system'
}

export interface GroundingSource {
  title: string;
  uri: string;
  type?: 'REAL_TIME' | 'KNOWLEDGE_BASE' | 'SYSTEM_SNAPSHOT' | 'NEURAL_INFERENCE';
  trustScore?: number;
}

export interface Attachment {
  mimeType: string;
  data: string; // Base64 string
  name?: string;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  text: string;
  isThinking?: boolean;
  timestamp: number;
  groundingSources?: GroundingSource[];
  attachments?: Attachment[];
  error?: boolean;
}

// --- QUANT NANGGROE AI CORE TYPES (BLUEPRINT FINAL) ---

export type MarketRegime = 'TRENDING' | 'RANGE' | 'MEAN_REVERT' | 'RISK_OFF' | 'PANIC' | 'NO_TRADE';

export interface TradingConstitution {
    riskGreaterThanOpportunity: boolean;
    regimeGreaterThanStrategy: boolean;
    structureGreaterThanIndicator: boolean;
    invalidationGreaterThanRR: boolean;
    noTradeIsValidDecision: boolean;
    maxLeverage: number;
    maxCorrelation: number;
    maxExposurePerAsset: number;
    dailyDrawdownLimit: number;
}

export interface DataMetadata {
  source: string;
  trustScore: number; // 0.0 - 1.0
  latencyEstimate: number; // ms
  updateFrequency: string;
  domainType: string;
}

export interface PressureState {
    buyPressure: number;  // 0.0 - 1.0
    sellPressure: number; // 0.0 - 1.0
    volatilityRisk: 'LOW' | 'MID' | 'HIGH';
    liquidityCondition: 'THIN' | 'NORMAL' | 'DEEP';
    confidenceScore: number; // 0.0 - 1.0
}

export interface ConfluenceStatus {
    isAllowed: boolean;
    reason?: string;
    score: number;
}

export interface MarketState {
    regime: MarketRegime;
    volatility: 'LOW' | 'NORMAL' | 'HIGH';
    liquidity: 'THIN' | 'NORMAL' | 'DEEP';
    timestamp: number;
}

export interface AgentContract {
    agentId: string;
    inputDomain: string[];
    decisionScope: string[];
    hardConstraints: string[];
}

export interface QuantScannerOutput {
    trendStrength: number; // 0.0 - 1.0
    structureState: 'BULL' | 'BEAR' | 'NEUTRAL';
    volatilityExpansion: boolean;
}

export interface SMCOutput {
    liquiditySweep: boolean;
    displacementStrength: number; // 0.0 - 1.0
    poiValidity: number; // 0.0 - 1.0
}

export interface NewsSentinelOutput {
    eventType: 'MACRO' | 'SCHEDULED' | 'SHOCK' | 'NOISE';
    impactScore: number; // 0.0 - 1.0
    directionalUncertainty: number; // 0.0 - 1.0
    timeDecay: number; // seconds
}

export interface FlowWhaleOutput {
    positioningBias: 'LONG' | 'SHORT' | 'NEUTRAL';
    flowImbalance: number; // 0.0 - 1.0
}

export interface DecisionTableEntry {
    regime: MarketRegime[];
    minBuyPressure: number;
    maxSellPressure: number;
    allowedVolatility: ('LOW' | 'NORMAL' | 'HIGH')[];
    minConfidence: number;
    action: 'ALLOW_ENTRY' | 'NO_TRADE';
}

export interface DecisionSynthesis {
    regime: MarketRegime;
    pressures: PressureState;
    confluence: ConfluenceStatus;
    entryParameters?: {
        location: string;
        trigger: string;
        execution: 'LIMIT' | 'MARKET';
        entry: number;
        sl: number;
        tp: number[];
    };
    riskClearance: 'CLEAR' | 'BLOCKED';
    action: 'BUY' | 'SELL' | 'HOLD' | 'WAIT';
}

export interface ExecutionReality {
    spread: number;
    slippage: number;
    partialFill: boolean;
    orderReject: boolean;
    latency: number;
}

export interface StrategyLifecycle {
    id: string;
    name: string;
    status: 'ACTIVE' | 'HIBERNATING' | 'KILLED';
    metrics: {
        expectancy: number;
        maxDrawdown: number;
        sharpeRatio: number;
        winRate: number;
        sampleSize: number;
    };
    tradesCount: number;
    deathThreshold: number; // N trades with expectancy < 0
}

// --- AGENT SYSTEM TYPES ---

export type AgentCapability = 
  | 'portfolio-manager' // Alpha Prime
  | 'quant'             // Technical Analyst
  | 'fundamental'       // News/Macro Analyst
  | 'risk-manager'      // Risk Control
  | 'algo-dev'          // Coder (Backtesting)
  | 'general';

export type AgentRole = AgentCapability | 'reviewer';
export type AgentTool = 'googleSearch' | 'codeExecution' | 'browserNavigation' | 'googleDrive' | 'systemUpgrade' | 'marketData' | 'spawnAgent';

export interface SwarmAgent {
  id: string;
  name: string;
  capability: AgentCapability;
  instructions: string;
  tools: AgentTool[];
  health?: 'healthy' | 'recovering' | 'critical'; 
}

export interface KnowledgeItem {
  id: string;
  category: string;
  content: string;
  sourceAgentId: string;
  timestamp: number;
  confidence: number;
  tags: string[];
  path?: string;
}

export interface AgentTask {
  id: string;
  agentId: string;
  role: AgentRole;
  description: string;
  status: 'pending' | 'active' | 'completed' | 'failed' | 'scheduled' | 'rejected';
  result?: string;
}

export interface ApiKeys {
  google: string;
  groq: string;
  openai: string;
  huggingface: string;
  llm7: string;
  alphaVantage: string;
  finnhub: string;
  fred: string;
  polygon: string;
}

export interface SystemConfiguration {
  enableAutoLearning: boolean;
  enableSelfHealing?: boolean;
  enableAutoScaling?: boolean;
  enableDynamicTools?: boolean;
  enableScheduling?: boolean;
  enableAutoSwitch?: boolean;
  enableVoiceResponse?: boolean;
  apiKeys: ApiKeys;
}

// --- MARKET DATA TYPES ---

export interface TechnicalIndicators {
    rsi: number;
    stoch: { k: number; d: number };
    cci: number;
    adx: number;
    macd: { macdLine: number; signalLine: number; histogram: number; };
    bollinger: { upper: number; middle: number; lower: number };
    vwap: number;
    atr: number;
    sma: { ma10: number; ma20: number; ma50: number; ma100: number; ma200: number; };
}

export interface MarketTicker {
    id: string;
    symbol: string;
    name?: string;
    currentPrice: number;
    priceChange24h: number;
    volume?: number;
    technicals?: TechnicalIndicators;
    metadata: DataMetadata; // Required by Blueprint Final
}

export interface CandleData {
    timestamp: number;
    open: number;
    high: number;
    low: number;
    close: number;
    volume?: number;
}

// --- AGENT UI TYPES ---

export interface AgentState {
  isActive: boolean;
  currentAgent?: string;
  currentAction?: string;
  emotion?: string;
  activeSwarm?: SwarmAgent[];
  activeBrowserUrl?: string;
  logs?: string[];
}

export interface ModelOption {
  id: string;
  name: string;
  provider: string;
}

export type SystemActionType = 'OPEN_WINDOW' | 'NAVIGATE_BROWSER' | 'FETCH_MARKET' | 'EXECUTE_TRADE' | 'ANALYZE_SENTIMENT';

export interface SystemAction {
  type: SystemActionType;
  payload: string;
}

export interface SystemNotification {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  message: string;
  timestamp: number;
}

// --- DATA DISPLAY TYPES ---

export interface NewsItem {
  id: string;
  headline: string;
  source: string;
  url: string;
  summary: string;
  timestamp: number;
}

export interface ChartPoint {
  timestamp: number;
  price: number;
}

export interface ResearchSource {
  id: string;
  name: string;
  url: string;
  type: 'news' | 'market' | 'geo' | 'sentiment' | 'institutional' | 'ai';
  lastScanned?: number;
}

// --- PORTFOLIO & FILE TYPES ---

export interface VirtualFile {
  name: string;
  content: string;
  type: string;
  lastModified: number;
}

export interface PortfolioPosition {
  ticker: string;
  amount: number;
  avgPrice: number;
  currentPrice: number;
  pnl: number;
  lastUpdated: number;
}

export interface DataSource {
  id: string;
  name: string;
  endpoint: string;
}

export interface TradeHistoryItem {
  id: string;
  timestamp: number;
  ticker: string;
  action: 'BUY' | 'SELL';
  amount: number;
  price: number;
  totalValue: number;
  fees: number;
  realizedPnL?: number;
  triggeredBySignals?: string[];
}

export interface SystemPatch {
  id: string;
  code: string;
  description: string;
  timestamp: number;
}

export interface WindowState {
  id: string;
  isOpen: boolean;
  isMinimized: boolean;
  zIndex: number;
}

export type LLMProvider = 'google' | 'groq' | 'openai' | 'llm7';

// --- STRATEGY & CONSENSUS TYPES ---

export interface StrategySignal {
    name: string;
    category: 'SMC' | 'STRUCTURE' | 'RETAIL';
    type: 'BUY' | 'SELL';
    strength: number;
    weight: number;
    description: string;
}

export interface ConsensusReport {
    score: number;
    verdict: 'STRONG BUY' | 'BUY' | 'NEUTRAL' | 'SELL' | 'STRONG SELL';
    totalSignals: number;
    bullishCount: number;
    bearishCount: number;
    topFactors: string[];
}

// --- VIRTUAL DISK NODE (Knowledge Base) ---

export interface VirtualDiskNode {
    id: string;
    name: string;
    type: 'folder' | 'file';
    path: string;
    children?: VirtualDiskNode[];
    contentId?: string;
    lastModified?: number;
}

// --- ML / EVOLUTION TYPES ---

export interface NeuralWeights {
    [signalName: string]: number;
}

export interface EvolutionState {
    generation: number;
    lastOptimization: number;
    bestStrategies: string[];
    weights: NeuralWeights;
}
