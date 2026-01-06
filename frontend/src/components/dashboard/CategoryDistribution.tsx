'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'
import { analyticsApi } from '@/lib/api'

const CATEGORY_COLORS: Record<string, string> = {
  'Technical Support': '#8b5cf6',
  'Billing & Payments': '#00bac7',
  'Account Management': '#10b981',
  'Product Features': '#f59e0b',
  'Sales & Licensing': '#ef4444',
}

export function CategoryDistribution() {
  const [data, setData] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const graphViz = await analyticsApi.getGraphVisualization()
        setData(graphViz)
      } catch (e) {
        console.error('Failed to fetch category data')
      } finally {
        setIsLoading(false)
      }
    }
    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-white/30" />
      </div>
    )
  }

  // Get level 1 nodes from the graph
  const level1Nodes = data?.nodes?.filter((n: any) => n.level === 1) || []
  const totalTickets = level1Nodes.reduce((sum: number, n: any) => sum + (n.ticket_count || 0), 0) || 1
  
  const categoryData = level1Nodes.map((node: any, idx: number) => ({
    name: node.label,
    count: node.ticket_count || 0,
    percentage: Math.round(((node.ticket_count || 0) / totalTickets) * 100),
    color: CATEGORY_COLORS[node.label] || `hsl(${idx * 60}, 70%, 50%)`,
  })).sort((a: any, b: any) => b.count - a.count).slice(0, 5)

  return (
    <div className="space-y-4">
      {/* Donut chart representation */}
      <div className="relative w-40 h-40 mx-auto">
        <svg viewBox="0 0 100 100" className="transform -rotate-90">
          {categoryData.map((cat: any, index: number) => {
            const offset = categoryData
              .slice(0, index)
              .reduce((sum: number, c: any) => sum + c.percentage, 0)
            const dashArray = `${cat.percentage} ${100 - cat.percentage}`
            const dashOffset = -offset
            
            return (
              <motion.circle
                key={cat.name}
                cx="50"
                cy="50"
                r="40"
                fill="none"
                stroke={cat.color}
                strokeWidth="8"
                strokeDasharray={dashArray}
                strokeDashoffset={dashOffset}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: index * 0.1 }}
                className="opacity-80"
              />
            )
          })}
        </svg>
        <div className="absolute inset-0 flex items-center justify-center flex-col">
          <p className="text-2xl font-bold">{totalTickets.toLocaleString()}</p>
          <p className="text-xs text-white/50">Total</p>
        </div>
      </div>
      
      {/* Legend */}
      <div className="space-y-2">
        {categoryData.map((cat: any, index: number) => (
          <motion.div
            key={cat.name}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 + index * 0.05 }}
            className="flex items-center justify-between p-2 rounded-lg hover:bg-white/5 transition-colors cursor-pointer group"
          >
            <div className="flex items-center gap-3">
              <span
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: cat.color }}
              />
              <span className="text-sm text-white/70 group-hover:text-white transition-colors">
                {cat.name}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm text-white/50">
                {cat.count.toLocaleString()}
              </span>
              <span className="text-xs text-white/40 w-10 text-right">
                {cat.percentage}%
              </span>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
