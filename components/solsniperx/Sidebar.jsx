import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  LayoutDashboard,
  Search,
  TrendingUp,
  Wallet,
  BarChart3,
  Settings,
  X,
  Zap,
  Shield,
  Bot,
  Target,
  Activity,
  DollarSign
} from 'lucide-react'

const navigation = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
    description: 'Overview & Analytics'
  },
  {
    name: 'Token Scanner',
    href: '/scanner',
    icon: Search,
    description: 'Real-time Detection'
  },
  {
    name: 'Trading',
    href: '/trading',
    icon: TrendingUp,
    description: 'Auto & Manual Trading'
  },
  {
    name: 'Wallet',
    href: '/wallet',
    icon: Wallet,
    description: 'Balance & Transactions'
  },
  {
    name: 'Analytics',
    href: '/analytics',
    icon: BarChart3,
    description: 'Performance Insights'
  },
  {
    name: 'Settings',
    href: '/settings',
    icon: Settings,
    description: 'Configuration'
  }
]

const features = [
  {
    icon: Bot,
    title: 'AI Detection',
    description: 'Smart token analysis'
  },
  {
    icon: Zap,
    title: 'Lightning Fast',
    description: 'Millisecond execution'
  },
  {
    icon: Shield,
    title: 'Anti-Rug',
    description: 'Protection built-in'
  },
  {
    icon: Target,
    title: 'Precision',
    description: 'AI-powered signals'
  }
]

export default function Sidebar({ onClose }) {
  const location = useLocation()
  const [hoveredItem, setHoveredItem] = useState(null)
  const [stats, setStats] = useState({ totalTrades: 0, successRate: 0, totalProfit: 0 })

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch('/api/analytics/performance?XTransformPort=5000')
        const data = await res.json()
        if (data.success && data.data) {
          setStats({
            totalTrades: data.data.totalTrades || 0,
            successRate: data.data.successRate || 0,
            totalProfit: data.data.totalProfit || 0
          })
        }
      } catch {
        // Stats will show defaults
      }
    }
    fetchStats()
    const interval = setInterval(fetchStats, 60000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="h-full bg-card border-r border-border flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-primary rounded-xl flex items-center justify-center">
              <Wallet className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gradient-primary">SolSniperX</h1>
              <p className="text-xs text-muted-foreground">AI Sniper Bot</p>
            </div>
          </div>
          
          {/* Close button for mobile */}
          <button
            onClick={onClose}
            className="md:hidden p-1 hover:bg-accent rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Status Indicator */}
        <div className="mt-4 flex items-center space-x-2 p-3 bg-accent rounded-lg">
          <div className="status-online" />
          <div className="flex-1">
            <p className="text-sm font-medium text-green-400">System Online</p>
            <p className="text-xs text-muted-foreground">Scanning 24/7</p>
          </div>
          <Activity className="w-4 h-4 text-green-400" />
        </div>
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto py-4">
        <nav className="px-4 space-y-2">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href
            const Icon = item.icon

            return (
              <Link
                key={item.name}
                to={item.href}
                onMouseEnter={() => setHoveredItem(item.name)}
                onMouseLeave={() => setHoveredItem(null)}
                className={`
                  group relative flex items-center space-x-3 px-3 py-2.5 rounded-lg transition-all duration-200
                  ${isActive 
                    ? 'bg-gradient-primary text-white shadow-lg' 
                    : 'hover:bg-accent text-foreground hover:text-primary'
                  }
                `}
              >
                <Icon className={`w-5 h-5 ${isActive ? 'text-white' : 'text-muted-foreground group-hover:text-primary'}`} />
                <div className="flex-1">
                  <p className={`text-sm font-medium ${isActive ? 'text-white' : ''}`}>
                    {item.name}
                  </p>
                  <p className={`text-xs ${isActive ? 'text-white/80' : 'text-muted-foreground'}`}>
                    {item.description}
                  </p>
                </div>

                {/* Active indicator */}
                {isActive && (
                  <motion.div
                    layoutId="activeTab"
                    className="absolute right-2 w-2 h-2 bg-white rounded-full"
                  />
                )}

                {/* Hover effect */}
                {hoveredItem === item.name && !isActive && (
                  <motion.div
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="absolute right-2 w-1 h-6 bg-primary rounded-full"
                  />
                )}
              </Link>
            )
          })}
        </nav>

        {/* Features Section */}
        <div className="mt-8 px-4">
          <h3 className="text-sm font-semibold text-muted-foreground mb-3 px-3">
            Key Features
          </h3>
          <div className="space-y-2">
            {features.map((feature, index) => {
              const Icon = feature.icon
              return (
                <motion.div
                  key={feature.title}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-accent transition-colors group"
                >
                  <div className="w-8 h-8 bg-gradient-primary/10 rounded-lg flex items-center justify-center group-hover:bg-gradient-primary/20 transition-colors">
                    <Icon className="w-4 h-4 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">{feature.title}</p>
                    <p className="text-xs text-muted-foreground">{feature.description}</p>
                  </div>
                </motion.div>
              )
            })}
          </div>
        </div>

        {/* Stats Section */}
        <div className="mt-8 px-4">
          <div className="bg-gradient-card rounded-lg p-4 border border-border">
            <h3 className="text-sm font-semibold mb-3">Performance</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Total Trades</span>
                <span className="text-sm font-medium">{stats.totalTrades}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Success Rate</span>
                <span className="text-sm font-medium text-green-400">{stats.successRate}%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Profit (SOL)</span>
                <span className={`text-sm font-medium ${stats.totalProfit >= 0 ? 'text-green-400' : 'text-red-400'}`}>{stats.totalProfit >= 0 ? '+' : ''}{stats.totalProfit.toFixed(4)}</span>
              </div>
              <div className="w-full bg-accent rounded-full h-2">
                <div className="bg-gradient-success h-2 rounded-full" style={{ width: `${Math.min(100, stats.successRate)}%` }} />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-border">
        <div className="text-center">
          <p className="text-xs text-muted-foreground">
            Created by
          </p>
          <p className="text-sm font-medium text-gradient-primary">
            Mulky Malikul Dhaher
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            v3.3.0 (Ultimate Intelligence Upgrade)
          </p>
        </div>
      </div>
    </div>
  )
}
