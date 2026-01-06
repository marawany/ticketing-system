'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Activity, CheckCircle2, Clock, Database, TrendingUp, Zap, Loader2, ArrowUpRight, ArrowDownRight } from 'lucide-react'
import { analyticsApi, type DashboardStats as DashboardStatsType } from '@/lib/api'

export function DashboardStats() {
  const [data, setData] = useState<DashboardStatsType | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const stats = await analyticsApi.getDashboard()
        setData(stats)
      } catch (e) {
        console.error('Failed to fetch dashboard stats')
      } finally {
        setIsLoading(false)
      }
    }
    fetchStats()
    const interval = setInterval(fetchStats, 10000)
    return () => clearInterval(interval)
  }, [])

  if (isLoading) {
    return (
      <div className="grid grid-cols-6 gap-3">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="bg-terminal-panel border border-terminal-border p-3 animate-pulse">
            <div className="h-16 bg-terminal-surface rounded-terminal" />
          </div>
        ))}
      </div>
    )
  }

  const stats = [
    {
      label: 'PROCESSED',
      value: data?.total_tickets_processed?.toLocaleString() || '0',
      change: `+${data?.tickets_today || 0}`,
      changeType: 'positive',
      color: 'cyan',
    },
    {
      label: 'AUTO-RESOLVED',
      value: `${((data?.auto_resolved_rate || 0) * 100).toFixed(1)}%`,
      subValue: Math.round((data?.total_tickets_processed || 0) * (data?.auto_resolved_rate || 0)).toLocaleString(),
      changeType: 'positive',
      color: 'green',
    },
    {
      label: 'AVG CONFIDENCE',
      value: `${((data?.avg_confidence || 0) * 100).toFixed(1)}%`,
      changeType: (data?.avg_confidence || 0) >= 0.7 ? 'positive' : 'neutral',
      color: (data?.avg_confidence || 0) >= 0.7 ? 'green' : 'amber',
    },
    {
      label: 'AVG LATENCY',
      value: `${data?.avg_processing_time_ms || 0}ms`,
      changeType: (data?.avg_processing_time_ms || 0) < 5000 ? 'positive' : 'negative',
      color: (data?.avg_processing_time_ms || 0) < 5000 ? 'green' : 'red',
    },
    {
      label: 'HITL QUEUE',
      value: data?.hitl_queue_size?.toString() || '0',
      changeType: (data?.hitl_queue_size || 0) === 0 ? 'positive' : 'neutral',
      color: (data?.hitl_queue_size || 0) === 0 ? 'green' : 'amber',
    },
    {
      label: 'CATEGORIES',
      value: data?.graph_categories?.toString() || '0',
      subValue: `${data?.vector_count?.toLocaleString() || 0} vectors`,
      color: 'blue',
    },
  ]

  const colorMap: Record<string, { text: string; border: string; bg: string }> = {
    cyan: { text: 'text-data-cyan', border: 'border-data-cyan/30', bg: 'bg-data-cyan/10' },
    green: { text: 'text-data-green', border: 'border-data-green/30', bg: 'bg-data-green/10' },
    amber: { text: 'text-data-amber', border: 'border-data-amber/30', bg: 'bg-data-amber/10' },
    red: { text: 'text-data-red', border: 'border-data-red/30', bg: 'bg-data-red/10' },
    blue: { text: 'text-data-blue', border: 'border-data-blue/30', bg: 'bg-data-blue/10' },
  }

  return (
    <div className="grid grid-cols-6 gap-px bg-terminal-border">
      {stats.map((stat, index) => {
        const colors = colorMap[stat.color] || colorMap.cyan
        return (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            className="bg-terminal-panel p-3"
          >
            <div className="text-xxs text-white/40 uppercase tracking-widest mb-2">
              {stat.label}
            </div>
            <div className={`text-2xl font-mono font-bold ${colors.text} tracking-tight`}>
              {stat.value}
            </div>
            {stat.subValue && (
              <div className="text-xxs text-white/40 mt-1 font-mono">
                {stat.subValue}
              </div>
            )}
            {stat.change && (
              <div className={`flex items-center gap-1 mt-1 text-xxs ${
                stat.changeType === 'positive' ? 'text-data-green' :
                stat.changeType === 'negative' ? 'text-data-red' : 'text-data-amber'
              }`}>
                {stat.changeType === 'positive' ? (
                  <ArrowUpRight className="w-3 h-3" />
                ) : stat.changeType === 'negative' ? (
                  <ArrowDownRight className="w-3 h-3" />
                ) : null}
                <span className="font-mono">{stat.change}</span>
                <span className="text-white/30 ml-1">today</span>
              </div>
            )}
          </motion.div>
        )
      })}
    </div>
  )
}
