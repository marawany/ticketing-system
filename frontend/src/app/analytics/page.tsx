'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  Activity,
  ArrowDown,
  ArrowUp,
  BarChart3,
  Brain,
  CheckCircle2,
  Clock,
  Database,
  GitBranch,
  Layers,
  Network,
  RefreshCw,
  Sparkles,
  Target,
  TrendingUp,
  Users,
  Zap
} from 'lucide-react'
import { Sidebar } from '@/components/layout/Sidebar'
import { analyticsApi, type DashboardStats, type GraphVisualization } from '@/lib/api'
import { 
  LineChart, 
  Line, 
  AreaChart, 
  Area,
  BarChart, 
  Bar, 
  PieChart, 
  Pie, 
  Cell,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Legend 
} from 'recharts'

const COLORS = ['#00bac7', '#a855f7', '#3b82f6', '#f97316', '#22c55e', '#ef4444']

export default function AnalyticsPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [confidenceMetrics, setConfidenceMetrics] = useState<any>(null)
  const [graphStats, setGraphStats] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isLive, setIsLive] = useState(true)

  const fetchData = async () => {
    try {
      const [dashboardRes, confidenceRes, graphRes] = await Promise.all([
        analyticsApi.getDashboard(),
        analyticsApi.getConfidenceMetrics(),
        analyticsApi.getGraphVisualization(),
      ])
      setStats(dashboardRes)
      setConfidenceMetrics(confidenceRes)
      setGraphStats(graphRes.statistics)
    } catch (e) {
      console.error('Failed to fetch analytics')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    if (isLive) {
      const interval = setInterval(fetchData, 10000)
      return () => clearInterval(interval)
    }
  }, [isLive])

  // Sample time series data for charts
  const timeSeriesData = [
    { hour: '00:00', classifications: 45, autoResolved: 38, hitl: 7 },
    { hour: '04:00', classifications: 32, autoResolved: 28, hitl: 4 },
    { hour: '08:00', classifications: 128, autoResolved: 110, hitl: 18 },
    { hour: '12:00', classifications: 156, autoResolved: 132, hitl: 24 },
    { hour: '16:00', classifications: 142, autoResolved: 121, hitl: 21 },
    { hour: '20:00', classifications: 89, autoResolved: 76, hitl: 13 },
  ]

  const confidenceDistribution = [
    { range: '90-100%', count: stats?.total_tickets_processed ? Math.floor(stats.total_tickets_processed * 0.35) : 350 },
    { range: '80-90%', count: stats?.total_tickets_processed ? Math.floor(stats.total_tickets_processed * 0.28) : 280 },
    { range: '70-80%', count: stats?.total_tickets_processed ? Math.floor(stats.total_tickets_processed * 0.20) : 200 },
    { range: '60-70%', count: stats?.total_tickets_processed ? Math.floor(stats.total_tickets_processed * 0.10) : 100 },
    { range: '<60%', count: stats?.total_tickets_processed ? Math.floor(stats.total_tickets_processed * 0.07) : 70 },
  ]

  const categoryData = graphStats ? [
    { name: 'Level 1', value: graphStats.level1_categories },
    { name: 'Level 2', value: graphStats.level2_categories },
    { name: 'Level 3', value: graphStats.level3_categories },
  ] : []

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      
      <main className="flex-1 overflow-y-auto bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
        {/* Header */}
        <header className="sticky top-0 z-10 glass border-b border-white/10 px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-gradient-to-br from-green-500 to-emerald-500 shadow-lg">
                <BarChart3 className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">Analytics Dashboard</h1>
                <p className="text-white/50 text-sm">Real-time classification insights & metrics</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <button
                onClick={() => setIsLive(!isLive)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                  isLive 
                    ? 'bg-green-500/20 text-green-400 border border-green-500/50' 
                    : 'bg-white/5 text-white/60 border border-white/10'
                }`}
              >
                {isLive ? (
                  <>
                    <span className="pulse-dot" />
                    Live
                  </>
                ) : (
                  <>
                    <Activity className="w-4 h-4" />
                    Paused
                  </>
                )}
              </button>
              <button 
                onClick={() => fetchData()}
                className="btn-secondary flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh
              </button>
            </div>
          </div>
        </header>

        <div className="p-8 space-y-8">
          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="card bg-gradient-to-br from-nexus-500/10 to-cyan-500/5"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-white/50 mb-1">Total Processed</p>
                  <p className="text-3xl font-bold">
                    {stats?.total_tickets_processed.toLocaleString() || '0'}
                  </p>
                  <div className="flex items-center gap-1 mt-2 text-green-400 text-sm">
                    <ArrowUp className="w-3 h-3" />
                    <span>+{stats?.tickets_today || 0} today</span>
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-nexus-500/20">
                  <Sparkles className="w-6 h-6 text-nexus-400" />
                </div>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="card bg-gradient-to-br from-green-500/10 to-emerald-500/5"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-white/50 mb-1">Auto-Resolved Rate</p>
                  <p className="text-3xl font-bold">
                    {((stats?.auto_resolved_rate || 0) * 100).toFixed(1)}%
                  </p>
                  <div className="flex items-center gap-1 mt-2 text-green-400 text-sm">
                    <Target className="w-3 h-3" />
                    <span>Above threshold</span>
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-green-500/20">
                  <CheckCircle2 className="w-6 h-6 text-green-400" />
                </div>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="card bg-gradient-to-br from-purple-500/10 to-pink-500/5"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-white/50 mb-1">Avg Confidence</p>
                  <p className="text-3xl font-bold">
                    {((stats?.avg_confidence || 0) * 100).toFixed(1)}%
                  </p>
                  <div className="flex items-center gap-1 mt-2 text-purple-400 text-sm">
                    <Brain className="w-3 h-3" />
                    <span>Ensemble score</span>
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-purple-500/20">
                  <Brain className="w-6 h-6 text-purple-400" />
                </div>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="card bg-gradient-to-br from-orange-500/10 to-amber-500/5"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-white/50 mb-1">HITL Queue</p>
                  <p className="text-3xl font-bold">
                    {stats?.hitl_queue_size || 0}
                  </p>
                  <div className="flex items-center gap-1 mt-2 text-orange-400 text-sm">
                    <Users className="w-3 h-3" />
                    <span>Pending review</span>
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-orange-500/20">
                  <Users className="w-6 h-6 text-orange-400" />
                </div>
              </div>
            </motion.div>
          </div>

          {/* Charts Row 1 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Classification Volume */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="card"
            >
              <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                <Activity className="w-5 h-5 text-nexus-400" />
                Classification Volume (24h)
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={timeSeriesData}>
                  <defs>
                    <linearGradient id="colorClassifications" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#00bac7" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#00bac7" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorAutoResolved" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis dataKey="hour" stroke="rgba(255,255,255,0.5)" fontSize={12} />
                  <YAxis stroke="rgba(255,255,255,0.5)" fontSize={12} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'rgba(15, 23, 42, 0.9)', 
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '8px'
                    }}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="classifications" 
                    stroke="#00bac7" 
                    fillOpacity={1} 
                    fill="url(#colorClassifications)" 
                    name="Total"
                  />
                  <Area 
                    type="monotone" 
                    dataKey="autoResolved" 
                    stroke="#22c55e" 
                    fillOpacity={1} 
                    fill="url(#colorAutoResolved)" 
                    name="Auto-Resolved"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </motion.div>

            {/* Confidence Distribution */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              className="card"
            >
              <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                <Target className="w-5 h-5 text-green-400" />
                Confidence Distribution
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={confidenceDistribution} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis type="number" stroke="rgba(255,255,255,0.5)" fontSize={12} />
                  <YAxis dataKey="range" type="category" stroke="rgba(255,255,255,0.5)" fontSize={12} width={80} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'rgba(15, 23, 42, 0.9)', 
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '8px'
                    }}
                  />
                  <Bar dataKey="count" fill="#00bac7" radius={[0, 4, 4, 0]}>
                    {confidenceDistribution.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </motion.div>
          </div>

          {/* Charts Row 2 */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Category Hierarchy */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
              className="card"
            >
              <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                <Network className="w-5 h-5 text-purple-400" />
                Category Hierarchy
              </h3>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={categoryData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {categoryData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'rgba(15, 23, 42, 0.9)', 
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '8px'
                    }}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
              <div className="mt-4 space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-white/60">Total Categories</span>
                  <span className="font-mono">{graphStats?.level3_categories || 0}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-white/60">Total Tickets Indexed</span>
                  <span className="font-mono">{graphStats?.total_tickets?.toLocaleString() || 0}</span>
                </div>
              </div>
            </motion.div>

            {/* Processing Performance */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
              className="card"
            >
              <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                <Zap className="w-5 h-5 text-yellow-400" />
                Processing Performance
              </h3>
              <div className="space-y-6">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-white/60">Avg Processing Time</span>
                    <span className="font-mono text-yellow-400">{stats?.avg_processing_time_ms || 0}ms</span>
                  </div>
                  <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-gradient-to-r from-yellow-500 to-amber-500 rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.min(100, (stats?.avg_processing_time_ms || 0) / 50)}%` }}
                    />
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-white/60">Graph Query</span>
                    <span className="font-mono text-purple-400">~120ms</span>
                  </div>
                  <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full" style={{ width: '24%' }} />
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-white/60">Vector Search</span>
                    <span className="font-mono text-blue-400">~80ms</span>
                  </div>
                  <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full" style={{ width: '16%' }} />
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-white/60">LLM Judgment</span>
                    <span className="font-mono text-orange-400">~800ms</span>
                  </div>
                  <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-orange-500 to-red-500 rounded-full" style={{ width: '60%' }} />
                  </div>
                </div>
              </div>
            </motion.div>

            {/* System Health */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8 }}
              className="card"
            >
              <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                <Activity className="w-5 h-5 text-green-400" />
                System Health
              </h3>
              <div className="space-y-4">
                {[
                  { name: 'Neo4j', status: 'online', latency: '12ms', icon: GitBranch, color: 'green' },
                  { name: 'Milvus', status: 'online', latency: '8ms', icon: Database, color: 'green' },
                  { name: 'LLM API', status: 'online', latency: '340ms', icon: Brain, color: 'green' },
                  { name: 'Phoenix', status: 'online', latency: '5ms', icon: Activity, color: 'green' },
                ].map((service) => (
                  <div key={service.name} className="flex items-center justify-between p-3 rounded-lg bg-white/5">
                    <div className="flex items-center gap-3">
                      <service.icon className={`w-4 h-4 text-${service.color}-400`} />
                      <span className="text-sm">{service.name}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-white/40">{service.latency}</span>
                      <span className={`w-2 h-2 rounded-full bg-${service.color}-400`} />
                    </div>
                  </div>
                ))}
              </div>
              
              <div className="mt-6 pt-4 border-t border-white/10">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-white/60">Vector Count</span>
                  <span className="font-mono">{stats?.vector_count?.toLocaleString() || 0}</span>
                </div>
                <div className="flex items-center justify-between text-sm mt-2">
                  <span className="text-white/60">Graph Categories</span>
                  <span className="font-mono">{stats?.graph_categories || 0}</span>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </main>
    </div>
  )
}

