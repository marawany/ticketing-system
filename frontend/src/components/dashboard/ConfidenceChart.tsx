'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'
import { analyticsApi } from '@/lib/api'

export function ConfidenceChart() {
  const [data, setData] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [dashboard, confidence] = await Promise.all([
          analyticsApi.getDashboard(),
          analyticsApi.getConfidenceMetrics(),
        ])
        setData({ dashboard, confidence })
      } catch (e) {
        console.error('Failed to fetch confidence data')
      } finally {
        setIsLoading(false)
      }
    }
    fetchData()
    const interval = setInterval(fetchData, 15000)
    return () => clearInterval(interval)
  }, [])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-white/30" />
      </div>
    )
  }

  const total = data?.dashboard?.total_tickets_processed || 0
  const avgConfidence = data?.dashboard?.avg_confidence || 0
  const autoResolvedRate = data?.dashboard?.auto_resolved_rate || 0
  
  // Use REAL histogram data from API, fallback to empty distribution
  const rawHistogram = data?.confidence?.confidence_histogram || []
  
  // Build distribution from real API data
  const colorMap: Record<string, string> = {
    '0.9-1.0': '#10b981',
    '0.8-0.9': '#22c55e', 
    '0.7-0.8': '#84cc16',
    '0.6-0.7': '#eab308',
    '0.5-0.6': '#f97316',
    '0.0-0.5': '#ef4444',
  }
  
  const defaultRanges = ['0.9-1.0', '0.8-0.9', '0.7-0.8', '0.6-0.7', '0.5-0.6', '0.0-0.5']
  
  const confidenceData = defaultRanges.map(range => {
    // Find matching data from API response
    const apiData = rawHistogram.find((h: any) => h.range === range)
    return {
      range,
      count: apiData?.count || 0,
      color: colorMap[range],
    }
  })

  const totalCount = confidenceData.reduce((sum, d) => sum + d.count, 0)

  return (
    <div className="space-y-4">
      {/* Summary stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20">
          <p className="text-2xl font-bold text-green-400">
            {(avgConfidence * 100).toFixed(1)}%
          </p>
          <p className="text-xs text-white/50">Avg. Confidence</p>
        </div>
        <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/20">
          <p className="text-2xl font-bold text-purple-400">
            {(autoResolvedRate * 100).toFixed(1)}%
          </p>
          <p className="text-xs text-white/50">Auto-Resolved</p>
        </div>
      </div>
      
      {/* Distribution bars */}
      <div className="space-y-3">
        {confidenceData.map((item, index) => {
          const percentage = totalCount > 0 ? (item.count / totalCount) * 100 : 0
          
          return (
            <motion.div
              key={item.range}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              className="space-y-1"
            >
              <div className="flex items-center justify-between text-sm">
                <span className="text-white/60">{item.range}</span>
                <span className="text-white/40">{item.count.toLocaleString()}</span>
              </div>
              <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  style={{ backgroundColor: item.color }}
                  initial={{ width: 0 }}
                  animate={{ width: `${percentage}%` }}
                  transition={{ delay: 0.3 + index * 0.05, duration: 0.5 }}
                />
              </div>
            </motion.div>
          )
        })}
      </div>
      
      {/* Legend */}
      <div className="pt-4 border-t border-white/10">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-green-500" />
            <span className="text-white/60">High confidence (≥0.7)</span>
          </div>
          <span className="text-white/40">
            {totalCount > 0 ? ((confidenceData.slice(0, 3).reduce((s, d) => s + d.count, 0) / totalCount) * 100).toFixed(1) : '0.0'}%
          </span>
        </div>
        <div className="flex items-center justify-between text-xs mt-2">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-orange-500" />
            <span className="text-white/60">HITL required (&lt;0.7)</span>
          </div>
          <span className="text-white/40">
            {totalCount > 0 ? ((confidenceData.slice(3).reduce((s, d) => s + d.count, 0) / totalCount) * 100).toFixed(1) : '0.0'}%
          </span>
        </div>
      </div>
    </div>
  )
}
