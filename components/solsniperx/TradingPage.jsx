import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useApi } from '../contexts/ApiContext'
import { useWebSocket } from '../contexts/WebSocketContext'
import { 
  TrendingUp, 
  TrendingDown, 
  Zap, 
  Target, 
  Shield, 
  Settings,
  Play,
  Pause,
  DollarSign,
  Percent,
  Clock,
  Activity,
  AlertTriangle,
  CheckCircle,
  BarChart3
} from 'lucide-react'

export default function TradingPage() {
  const {
    buyToken,
    sellToken,
    placeLimitOrder,
    startAutoTrader,
    stopAutoTrader,
    getDashboardData,
    getAutoTraderConfig,
    updateAutoTraderConfig
  } = useApi()
  const { lastMessage, autoTraderStatus } = useWebSocket()

  const [autoTrading, setAutoTrading] = useState(false)
  const [tradingSettings, setTradingSettings] = useState({
    buyAmount: 0.05,
    slippage: 1.0,
    takeProfit: 200,
    stopLoss: 20,
    maxRisk: 30
  })
  const [manualBuyTokenAddress, setManualBuyTokenAddress] = useState('')
  const [manualBuyAmount, setManualBuyAmount] = useState(0.01)
  const [limitOrderAddress, setLimitOrderAddress] = useState('')
  const [limitOrderTarget, setLimitOrderTarget] = useState(0)
  const [limitOrderAmount, setLimitOrderAmount] = useState(0.01)
  const [limitOrderSide, setLimitOrderSide] = useState('buy')
  const [recentTrades, setRecentTrades] = useState([])
  const [activePositions, setActivePositions] = useState([])
  const [dashboardStats, setDashboardStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setAutoTrading(autoTraderStatus.enabled)
  }, [autoTraderStatus])

  useEffect(() => {
    loadInitialData()
  }, [])

  const loadInitialData = async () => {
    try {
      setLoading(true)

      // Load Dashboard Stats
      const dashboardResult = await getDashboardData()
      if (dashboardResult.success) {
        setDashboardStats(dashboardResult.data.stats)
        setRecentTrades(dashboardResult.data.recentTrades || [])
        setActivePositions(dashboardResult.data.activePositions || [])
      }

      // Load Auto Trader Config
      const configResult = await getAutoTraderConfig()
      if (configResult.success) {
        const cfg = configResult.data
        setTradingSettings({
          buyAmount: cfg.buy_amount_sol || 0.05,
          slippage: cfg.slippage || 1.0,
          takeProfit: (cfg.profit_target_x - 1) * 100 || 200,
          stopLoss: cfg.stop_loss_percentage * 100 || 20,
          maxRisk: cfg.max_risk_score || 30
        })
      }
    } catch (error) {
      console.error('Error loading trading data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveSettings = async () => {
    try {
      const configToSave = {
        buy_amount_sol: tradingSettings.buyAmount,
        slippage: tradingSettings.slippage,
        profit_target_x: 1 + (tradingSettings.takeProfit / 100),
        stop_loss_percentage: tradingSettings.stopLoss / 100,
        max_risk_score: tradingSettings.maxRisk
      }
      const result = await updateAutoTraderConfig(configToSave)
      if (result.success) {
        alert('Settings saved successfully!')
      } else {
        alert(`Failed to save settings: ${result.error}`)
      }
    } catch (error) {
      console.error('Error saving settings:', error)
      alert('Failed to save settings.')
    }
  }

  const handleToggleAutoTrading = async () => {
    try {
      if (autoTrading) {
        await stopAutoTrader()
      } else {
        await startAutoTrader()
      }
    } catch (error) {
      alert(`Error: ${error.message}`)
    }
  }

  const handleManualBuy = async () => {
    if (!manualBuyTokenAddress || manualBuyAmount <= 0) {
      alert('Please enter a valid token address and amount to buy.')
      return
    }
    try {
      const result = await buyToken(manualBuyTokenAddress, manualBuyAmount, tradingSettings.slippage)
      if (result.success) {
        alert('Buy order executed successfully!')
        // Optionally refresh recent trades or positions
      } else {
        alert(`Buy order failed: ${result.error}`)
      }
    } catch (error) {
      console.error('Error executing manual buy:', error)
      alert('Failed to execute buy order.')
    }
  }

  const handleManualSell = async (tokenAddress, amountTokens) => {
    if (!tokenAddress || amountTokens <= 0) {
      alert('Invalid token or amount for sell order.')
      return
    }
    try {
      const result = await sellToken(tokenAddress, amountTokens, tradingSettings.slippage)
      if (result.success) {
        alert('Sell order executed successfully!')
        // Optionally refresh recent trades or positions
      } else {
        alert(`Sell order failed: ${result.error}`)
      }
    } catch (error) {
      console.error('Error executing manual sell:', error)
      alert('Failed to execute sell order.')
    }
  }

  const handlePlaceLimitOrder = async () => {
    if (!limitOrderAddress || limitOrderTarget <= 0 || limitOrderAmount <= 0) {
      alert('Please enter valid token address, target price and amount.')
      return
    }
    try {
      const result = await placeLimitOrder(limitOrderAddress, limitOrderTarget, limitOrderAmount, limitOrderSide)
      if (result.success) {
        alert('Limit order placed successfully!')
        setLimitOrderAddress('')
      } else {
        alert(`Limit order failed: ${result.error}`)
      }
    } catch (error) {
      console.error('Error placing limit order:', error)
      alert('Failed to place limit order.')
    }
  }

  useEffect(() => {
    if (lastMessage && lastMessage.type === 'trade_executed') {
      const newTrade = {
        id: lastMessage.transaction_id,
        token_address: lastMessage.token_address,
        token: lastMessage.token_address.substring(0, 4) + '...' + lastMessage.token_address.substring(lastMessage.token_address.length - 4),
        type: lastMessage.type,
        amount_sol: lastMessage.type === 'buy' ? lastMessage.amount_sol : null,
        amount_tokens: lastMessage.type === 'sell' ? lastMessage.amount_tokens : null,
        price_usd: lastMessage.price_usd || 0,
        timestamp: lastMessage.timestamp || new Date().toISOString(),
        status: lastMessage.status
      }
      setRecentTrades(prevTrades => [newTrade, ...prevTrades].slice(0, 10))
    }
  }, [lastMessage])

  return (
    <div className="p-4 lg:p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4"
      >
        <div>
          <h1 className="text-3xl font-bold text-gradient-primary mb-2">
            Trading Dashboard
          </h1>
          <p className="text-muted-foreground">
            Automated and manual trading with AI-powered execution
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleToggleAutoTrading}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
              autoTrading 
                ? 'bg-green-500/20 text-green-400 border border-green-500/30' 
                : 'bg-accent text-muted-foreground border border-border'
            }`}
          >
            {autoTrading ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
            <span>Auto Trading {autoTrading ? 'ON' : 'OFF'}</span>
          </button>
        </div>
      </motion.div>

      {/* Trading Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="card-modern p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-gradient-success rounded-xl flex items-center justify-center">
              <DollarSign className="w-6 h-6 text-white" />
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-green-400">
                {dashboardStats?.totalProfit?.toFixed(4) || '0.0000'}
              </p>
              <p className="text-sm text-muted-foreground">Total Profit (SOL)</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <TrendingUp className="w-4 h-4 text-green-400" />
            <span className="text-sm text-green-400">Total earnings</span>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card-modern p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-gradient-primary rounded-xl flex items-center justify-center">
              <Target className="w-6 h-6 text-white" />
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold">
                {dashboardStats?.successRate || '0.0'}%
              </p>
              <p className="text-sm text-muted-foreground">Success Rate</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <CheckCircle className="w-4 h-4 text-green-400" />
            <span className="text-sm text-green-400">{dashboardStats?.totalSells || 0} of {dashboardStats?.totalTrades || 0} trades</span>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="card-modern p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-gradient-warning rounded-xl flex items-center justify-center">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold">{dashboardStats?.activeTokens || 0}</p>
              <p className="text-sm text-muted-foreground">Active Positions</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Zap className="w-4 h-4 text-yellow-400" />
            <span className="text-sm text-yellow-400">Real-time monitoring</span>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="card-modern p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-gradient-danger rounded-xl flex items-center justify-center">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold">{dashboardStats?.rugsAvoided || 0}</p>
              <p className="text-sm text-muted-foreground">Rugs Avoided</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Shield className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-blue-400">100% protected</span>
          </div>
        </motion.div>
      </div>

      {/* Main Trading Interface */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Trading Settings */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="card-modern p-6"
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold flex items-center">
              <Settings className="w-5 h-5 mr-2 text-primary" />
              Trading Settings
            </h2>
          </div>

          <div className="space-y-6">
            {/* Buy Amount */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Default Buy Amount (SOL)
              </label>
              <input
                type="number"
                step="0.01"
                value={tradingSettings.buyAmount}
                onChange={(e) => setTradingSettings({
                  ...tradingSettings,
                  buyAmount: parseFloat(e.target.value)
                })}
                className="w-full px-4 py-2 bg-accent border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>

            {/* Slippage */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Slippage Tolerance (%)
              </label>
              <input
                type="number"
                step="0.1"
                value={tradingSettings.slippage}
                onChange={(e) => setTradingSettings({
                  ...tradingSettings,
                  slippage: parseFloat(e.target.value)
                })}
                className="w-full px-4 py-2 bg-accent border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>

            {/* Take Profit */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Take Profit (%)
              </label>
              <input
                type="number"
                value={tradingSettings.takeProfit}
                onChange={(e) => setTradingSettings({
                  ...tradingSettings,
                  takeProfit: parseInt(e.target.value)
                })}
                className="w-full px-4 py-2 bg-accent border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>

            {/* Stop Loss */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Stop Loss (%)
              </label>
              <input
                type="number"
                value={tradingSettings.stopLoss}
                onChange={(e) => setTradingSettings({
                  ...tradingSettings,
                  stopLoss: parseInt(e.target.value)
                })}
                className="w-full px-4 py-2 bg-accent border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>

            {/* Max Risk */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Max Risk Score
              </label>
              <input
                type="number"
                value={tradingSettings.maxRisk}
                onChange={(e) => setTradingSettings({
                  ...tradingSettings,
                  maxRisk: parseInt(e.target.value)
                })}
                className="w-full px-4 py-2 bg-accent border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>

            <button
              onClick={handleSaveSettings}
              className="w-full btn-gradient"
            >
              Save Settings
            </button>
          </div>

          {/* Manual Buy Section */}
          <div className="space-y-4 border-t border-border pt-6 mt-6">
            <h3 className="text-lg font-bold text-white">Manual Buy</h3>
            <div>
              <label className="block text-sm font-medium mb-2">
                Token Address
              </label>
              <input
                type="text"
                placeholder="e.g., 2FPyx1... (SOL address)"
                value={manualBuyTokenAddress}
                onChange={(e) => setManualBuyTokenAddress(e.target.value)}
                className="w-full px-4 py-2 bg-accent border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">
                Amount (SOL)
              </label>
              <input
                type="number"
                step="0.01"
                value={manualBuyAmount}
                onChange={(e) => setManualBuyAmount(parseFloat(e.target.value))}
                className="w-full px-4 py-2 bg-accent border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>
            <button
              onClick={handleManualBuy}
              className="w-full bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 transition-colors font-medium"
            >
              Execute Manual Buy
            </button>
          </div>

          {/* Limit Order Section */}
          <div className="space-y-4 border-t border-border pt-6 mt-6">
            <h3 className="text-lg font-bold text-white">Limit Order</h3>
            <div className="flex bg-accent rounded-lg p-1">
              <button
                onClick={() => setLimitOrderSide('buy')}
                className={`flex-1 py-1 rounded-md text-sm font-medium transition-colors ${limitOrderSide === 'buy' ? 'bg-green-600 text-white' : 'text-muted-foreground'}`}
              >
                BUY
              </button>
              <button
                onClick={() => setLimitOrderSide('sell')}
                className={`flex-1 py-1 rounded-md text-sm font-medium transition-colors ${limitOrderSide === 'sell' ? 'bg-red-600 text-white' : 'text-muted-foreground'}`}
              >
                SELL
              </button>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Token Address</label>
              <input
                type="text"
                value={limitOrderAddress}
                onChange={(e) => setLimitOrderAddress(e.target.value)}
                placeholder="Token Address"
                className="w-full px-4 py-2 bg-accent border border-border rounded-lg focus:outline-none text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Target Price ($)</label>
              <input
                type="number"
                value={limitOrderTarget}
                onChange={(e) => setLimitOrderTarget(parseFloat(e.target.value))}
                placeholder="0.0000"
                className="w-full px-4 py-2 bg-accent border border-border rounded-lg focus:outline-none text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Amount (SOL)</label>
              <input
                type="number"
                value={limitOrderAmount}
                onChange={(e) => setLimitOrderAmount(parseFloat(e.target.value))}
                className="w-full px-4 py-2 bg-accent border border-border rounded-lg focus:outline-none text-sm"
              />
            </div>
            <button
              onClick={handlePlaceLimitOrder}
              className={`w-full py-2 rounded-lg transition-colors font-medium ${limitOrderSide === 'buy' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'} text-white`}
            >
              Place Limit {limitOrderSide.toUpperCase()}
            </button>
          </div>
        </motion.div>

        {/* Active Positions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="lg:col-span-2 card-modern p-6"
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold flex items-center">
              <BarChart3 className="w-5 h-5 mr-2 text-blue-400" />
              Active Positions
            </h2>
            <button className="text-sm text-primary hover:underline">
              View All
            </button>
          </div>

          <div className="space-y-4">
            {activePositions.length > 0 ? (
              activePositions.map((position, index) => (
                <motion.div
                  key={position.token_address}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 * index }}
                  className="flex items-center justify-between p-4 bg-accent rounded-lg"
                >
                  <div className="flex items-center space-x-4">
                    <div className="w-10 h-10 bg-gradient-primary rounded-full flex items-center justify-center">
                      <span className="text-sm font-bold text-white">
                        {position.token_symbol?.slice(0, 2) || '??'}
                      </span>
                    </div>
                    <div>
                      <p className="font-semibold">{position.token_symbol || 'Unknown'}</p>
                      <p className="text-xs text-muted-foreground truncate max-w-[100px]">
                        {position.token_address}
                      </p>
                    </div>
                  </div>

                  <div className="text-center">
                    <p className="text-sm text-muted-foreground">Amount</p>
                    <p className="font-mono text-sm">{position.amount_tokens?.toLocaleString()}</p>
                  </div>

                  <div className="text-center">
                    <p className="text-sm text-muted-foreground">Entry SOL</p>
                    <p className="font-mono text-sm">{position.buy_amount_sol} SOL</p>
                  </div>

                  <div className="text-right">
                    <div className="flex items-center space-x-2 mt-1">
                      <button
                        onClick={() => handleManualSell(position.token_address, position.amount_tokens)}
                        className="px-4 py-1 bg-red-500/20 text-red-400 rounded text-xs hover:bg-red-500/30 transition-colors font-bold"
                      >
                        SELL ALL
                      </button>
                    </div>
                  </div>
                </motion.div>
              ))
            ) : (
              <div className="text-center py-8 text-muted-foreground bg-accent/30 rounded-lg border border-dashed border-border">
                No active positions found.
              </div>
            )}
          </div>
        </motion.div>
      </div>

      {/* Recent Trades */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.7 }}
        className="card-modern p-6"
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold flex items-center">
            <Clock className="w-5 h-5 mr-2 text-yellow-400" />
            Recent Trades
          </h2>
          <button className="text-sm text-primary hover:underline">
            View All
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-accent">
              <tr>
                <th className="text-left p-3 font-semibold">Token</th>
                <th className="text-left p-3 font-semibold">Type</th>
                <th className="text-left p-3 font-semibold">Amount</th>
                <th className="text-left p-3 font-semibold">Price</th>
                <th className="text-left p-3 font-semibold">P&L</th>
                <th className="text-left p-3 font-semibold">Time</th>
                <th className="text-left p-3 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {recentTrades.map((trade, index) => (
                <tr key={index} className="border-b border-border hover:bg-accent/50 transition-colors">
                  <td className="p-3">
                    <div className="flex items-center space-x-2">
                      <div className="w-8 h-8 bg-gradient-primary rounded-full flex items-center justify-center">
                        <span className="text-xs font-bold text-white">
                          {(trade.token_symbol || trade.token_address || trade.token || '').slice(0, 2)}
                        </span>
                      </div>
                      <span className="font-semibold">{trade.token_symbol || trade.token || (trade.token_address ? trade.token_address.slice(0, 8) : 'Unknown')}</span>
                    </div>
                  </td>
                  <td className="p-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      trade.type === 'buy' 
                        ? 'bg-green-500/20 text-green-400' 
                        : 'bg-red-500/20 text-red-400'
                    }`}>
                      {trade.type.toUpperCase()}
                    </span>
                  </td>
                  <td className="p-3">
                    {trade.amount_sol ? `${trade.amount_sol.toFixed(4)} SOL` : trade.amount_tokens ? `${trade.amount_tokens?.toLocaleString()} Tokens` : `${trade.amount || 0} SOL`}
                  </td>
                  <td className="p-3 font-mono">${(trade.price_usd || trade.price || 0).toFixed(8)}</td>
                  <td className="p-3">
                    {(trade.pnl_percent || trade.pnl) ? (
                      <span className={`font-semibold ${
                        (trade.pnl_percent || trade.pnl) > 0 ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {(trade.pnl_percent || trade.pnl) > 0 ? '+' : ''}{(trade.pnl_percent || trade.pnl).toFixed(2)}%
                      </span>
                    ) : '-'}
                  </td>
                  <td className="p-3 text-sm text-muted-foreground">
                    {trade.timestamp ? new Date(trade.timestamp).toLocaleTimeString() : trade.time || 'Unknown'}
                  </td>
                  <td className="p-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      (trade.status === 'confirmed' || trade.status === 'completed')
                        ? 'bg-green-500/20 text-green-400' 
                        : 'bg-yellow-500/20 text-yellow-400'
                    }`}>
                      {trade.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>
    </div>
  )
}
