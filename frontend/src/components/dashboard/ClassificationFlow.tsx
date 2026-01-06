'use client'

import { motion } from 'framer-motion'
import { ArrowRight, Brain, Database, GitBranch, Search, Sparkles } from 'lucide-react'

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
      
      {/* Animated data flow line */}
      <motion.div
        className="absolute top-7 left-7 right-7 h-0.5 bg-gradient-to-r from-nexus-500/50 via-purple-500/50 to-green-500/50 -z-10"
        initial={{ scaleX: 0 }}
        animate={{ scaleX: 1 }}
        transition={{ duration: 1, delay: 0.5 }}
        style={{ transformOrigin: 'left' }}
      />
      
      {/* Live processing indicator */}
      <motion.div
        className="mt-8 p-4 rounded-lg bg-gradient-to-r from-nexus-500/10 to-purple-500/10 border border-nexus-500/20"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 1 }}
      >
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="pulse-dot" />
            <span className="text-sm text-white/70">Processing</span>
          </div>
          <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-nexus-gradient rounded-full"
              initial={{ width: '0%' }}
              animate={{ width: '75%' }}
              transition={{ duration: 2, repeat: Infinity, repeatType: 'reverse' }}
            />
          </div>
          <span className="text-sm text-white/50">~234ms avg</span>
        </div>
        
        <div className="grid grid-cols-3 gap-4 mt-4">
          <div className="text-center">
            <p className="text-2xl font-bold text-purple-400">0.89</p>
            <p className="text-xs text-white/40">Graph Confidence</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-blue-400">0.91</p>
            <p className="text-xs text-white/40">Vector Confidence</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-orange-400">0.85</p>
            <p className="text-xs text-white/40">LLM Confidence</p>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

