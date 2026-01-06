'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { ArrowRight, Brain, Database, GitBranch, Search, Sparkles } from 'lucide-react'
import { analyticsApi } from '@/lib/api'

const flowSteps = [
  {
    id: 'input',
    name: 'Ticket Input',
    icon: Sparkles,
    color: 'from-nexus-500 to-cyan-500',
    description: 'Receive ticket',
  },
  {
    id: 'graph',
    name: 'Graph Query',
    icon: GitBranch,
    color: 'from-purple-500 to-pink-500',
    description: 'Neo4j traversal',
  },
  {
    id: 'vector',
    name: 'Vector Search',
    icon: Search,
    color: 'from-blue-500 to-indigo-500',
    description: 'Milvus similarity',
  },
  {
    id: 'llm',
    name: 'LLM Judge',
    icon: Brain,
    color: 'from-orange-500 to-amber-500',
    description: 'Final decision',
  },
  {
    id: 'output',
    name: 'Classification',
    icon: Database,
    color: 'from-green-500 to-emerald-500',
    description: 'Result + confidence',
  },
]

export function ClassificationFlow() {
  const [stats, setStats] = useState<any>(null)
  const [confidence, setConfidence] = useState<any>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [dashboardRes, confRes] = await Promise.all([
          analyticsApi.getDashboard(),
          analyticsApi.getConfidenceMetrics(),
        ])
        setStats(dashboardRes)
        setConfidence(confRes)
      } catch (e) {
        console.error('Failed to fetch flow data')
      }
    }
    fetchData()
    const interval = setInterval(fetchData, 15000)
    return () => clearInterval(interval)
  }, [])

  // Calculate progress based on real auto-resolved rate
  const progressWidth = stats?.auto_resolved_rate ? `${stats.auto_resolved_rate * 100}%` : '0%'
  const avgTime = stats?.avg_processing_time_ms || 0
  
  // Get real confidence scores
  const graphConf = confidence?.avg_graph_confidence || stats?.avg_confidence || 0
  const vectorConf = confidence?.avg_vector_confidence || stats?.avg_confidence || 0
  const llmConf = confidence?.avg_llm_confidence || stats?.avg_confidence || 0

  return (
    <div className="relative">
      {/* Flow visualization */}
      <div className="flex items-center justify-between relative">
        {flowSteps.map((step, index) => (
          <motion.div
            key={step.id}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: index * 0.1 }}
            className="flex flex-col items-center relative z-10"
          >
            <div
              className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${step.color} flex items-center justify-center shadow-lg`}
            >
              <step.icon className="w-6 h-6 text-white" />
            </div>
            <p className="mt-3 text-sm font-medium">{step.name}</p>
            <p className="text-xs text-white/40">{step.description}</p>
            
            {/* Connector arrow */}
            {index < flowSteps.length - 1 && (
              <div className="absolute left-[calc(100%+0.5rem)] top-7 flex items-center">
                <div className="w-8 h-0.5 bg-gradient-to-r from-white/20 to-white/10" />
                <ArrowRight className="w-4 h-4 text-white/30 -ml-1" />
              </div>
            )}
          </motion.div>
        ))}
      </div>
      
      {/* Static data flow line */}
      <div
        className="absolute top-7 left-7 right-7 h-0.5 bg-gradient-to-r from-nexus-500/50 via-purple-500/50 to-green-500/50 -z-10"
      />
      
      {/* Processing indicator - NO ANIMATION */}
      <div className="mt-8 p-4 rounded-lg bg-gradient-to-r from-nexus-500/10 to-purple-500/10 border border-nexus-500/20">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="pulse-dot" />
            <span className="text-sm text-white/70">Processing</span>
          </div>
          <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
            {/* Static bar - no animation, shows real auto-resolve rate */}
            <div
              className="h-full bg-nexus-gradient rounded-full transition-all duration-500"
              style={{ width: progressWidth }}
            />
          </div>
          <span className="text-sm text-white/50">~{avgTime}ms avg</span>
        </div>
        
        <div className="grid grid-cols-3 gap-4 mt-4">
          <div className="text-center">
            <p className="text-2xl font-bold text-purple-400">{graphConf.toFixed(2)}</p>
            <p className="text-xs text-white/40">Graph Confidence</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-blue-400">{vectorConf.toFixed(2)}</p>
            <p className="text-xs text-white/40">Vector Confidence</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-orange-400">{llmConf.toFixed(2)}</p>
            <p className="text-xs text-white/40">LLM Confidence</p>
          </div>
        </div>
      </div>
    </div>
  )
}

