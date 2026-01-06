'use client'

import React from 'react'
import { Info, Brain, Database, GitBranch, Calculator } from 'lucide-react'
import { motion } from 'framer-motion'

interface ConfidenceComponent {
  name: string
  score: number
  weight: number
  description: string
  icon: React.ReactNode
}

interface ConfidenceExplainerProps {
  confidence: number
  components?: {
    graph_confidence?: number
    vector_confidence?: number
    llm_confidence?: number
    agreement_bonus?: number
  }
  explanation?: string
  className?: string
}

const defaultComponents: ConfidenceComponent[] = [
  {
    name: 'Graph Path Match',
    score: 0.85,
    weight: 0.3,
    description: 'Confidence from Neo4j graph traversal matching ticket keywords to classification hierarchy paths',
    icon: <GitBranch className="h-4 w-4" />,
  },
  {
    name: 'Vector Similarity',
    score: 0.78,
    weight: 0.3,
    description: 'Cosine similarity score from Milvus vector search comparing embeddings of similar historical tickets',
    icon: <Database className="h-4 w-4" />,
  },
  {
    name: 'LLM Judgment',
    score: 0.92,
    weight: 0.3,
    description: 'Language model confidence in classification based on context from graph and vector results',
    icon: <Brain className="h-4 w-4" />,
  },
  {
    name: 'Agreement Bonus',
    score: 0.1,
    weight: 0.1,
    description: 'Additional confidence when all three classifiers (graph, vector, LLM) agree on the same classification',
    icon: <Calculator className="h-4 w-4" />,
  },
]

export default function ConfidenceExplainer({
  confidence,
  components,
  explanation,
  className = '',
}: ConfidenceExplainerProps) {
  // Calculate actual components if provided
  const actualComponents: ConfidenceComponent[] = components
    ? [
        {
          name: 'Graph Path Match',
          score: components.graph_confidence || 0,
          weight: 0.3,
          description: 'Confidence from Neo4j graph traversal matching ticket keywords to classification hierarchy paths',
          icon: <GitBranch className="h-4 w-4" />,
        },
        {
          name: 'Vector Similarity',
          score: components.vector_confidence || 0,
          weight: 0.3,
          description: 'Cosine similarity score from Milvus vector search comparing embeddings of similar historical tickets',
          icon: <Database className="h-4 w-4" />,
        },
        {
          name: 'LLM Judgment',
          score: components.llm_confidence || 0,
          weight: 0.3,
          description: 'Language model confidence in classification based on context from graph and vector results',
          icon: <Brain className="h-4 w-4" />,
        },
        {
          name: 'Agreement Bonus',
          score: components.agreement_bonus || 0,
          weight: 0.1,
          description: 'Additional confidence when all three classifiers agree on the same classification',
          icon: <Calculator className="h-4 w-4" />,
        },
      ]
    : defaultComponents

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return 'text-data-green'
    if (score >= 0.6) return 'text-data-amber'
    return 'text-data-red'
  }

  const getProgressColor = (score: number) => {
    if (score >= 0.8) return 'bg-data-green'
    if (score >= 0.6) return 'bg-data-amber'
    return 'bg-data-red'
  }

  return (
    <div className={`bg-terminal-surface border border-terminal-border rounded-lg ${className}`}>
      <div className="border-b border-terminal-border px-4 py-3">
        <h3 className="flex items-center gap-2 text-data-cyan text-sm uppercase tracking-wide font-semibold">
          <Info className="h-4 w-4" />
          Confidence Score Breakdown
        </h3>
      </div>
      <div className="p-4 space-y-4">
        {/* Main Score */}
        <div className="text-center pb-4 border-b border-terminal-border">
          <div className="text-xs text-white/40 uppercase tracking-wider mb-1">
            Calibrated Confidence Score
          </div>
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className={`text-4xl font-bold ${getConfidenceColor(confidence)}`}
          >
            {(confidence * 100).toFixed(1)}%
          </motion.div>
          <div className="text-xs text-white/40 mt-1">
            {confidence >= 0.8 ? 'HIGH - Auto-resolved' : confidence >= 0.6 ? 'MEDIUM - Review recommended' : 'LOW - HITL Required'}
          </div>
        </div>

        {/* Formula Explanation */}
        <div className="bg-terminal-bg rounded p-3 text-xs">
          <div className="text-data-cyan font-mono mb-2">// Confidence Calculation Formula</div>
          <div className="text-white/70 font-mono">
            <span className="text-data-green">final_score</span> = (
            <span className="text-data-amber">graph</span> × 0.3) + (
            <span className="text-data-amber">vector</span> × 0.3) + (
            <span className="text-data-amber">llm</span> × 0.3) + (
            <span className="text-data-amber">agreement</span> × 0.1)
          </div>
        </div>

        {/* Component Breakdown */}
        <div className="space-y-3">
          {actualComponents.map((component, idx) => (
            <motion.div
              key={component.name}
              initial={{ x: -20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ delay: idx * 0.1 }}
              className="space-y-1"
            >
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 text-white/70">
                  {component.icon}
                  <span>{component.name}</span>
                  <span className="text-white/40">({(component.weight * 100).toFixed(0)}% weight)</span>
                </div>
                <span className={getConfidenceColor(component.score)}>
                  {(component.score * 100).toFixed(1)}%
                </span>
              </div>
              <div className="h-2 bg-terminal-bg rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${component.score * 100}%` }}
                  transition={{ duration: 0.5, delay: idx * 0.1 }}
                  className={`h-full ${getProgressColor(component.score)}`}
                />
              </div>
              <div className="text-[10px] text-white/40 leading-tight">
                {component.description}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Explanation */}
        {explanation && (
          <div className="bg-terminal-bg/50 rounded p-3 mt-4">
            <div className="text-xs text-data-cyan mb-1">AI Reasoning:</div>
            <div className="text-xs text-white/70 leading-relaxed">
              {explanation}
            </div>
          </div>
        )}

        {/* Thresholds */}
        <div className="border-t border-terminal-border pt-3 mt-4">
          <div className="text-[10px] text-white/40 uppercase tracking-wider mb-2">
            Confidence Thresholds
          </div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="text-center p-2 bg-terminal-bg rounded">
              <div className="text-data-green font-bold">≥80%</div>
              <div className="text-white/40">Auto-resolve</div>
            </div>
            <div className="text-center p-2 bg-terminal-bg rounded">
              <div className="text-data-amber font-bold">60-79%</div>
              <div className="text-white/40">Review</div>
            </div>
            <div className="text-center p-2 bg-terminal-bg rounded">
              <div className="text-data-red font-bold">&lt;60%</div>
              <div className="text-white/40">HITL Queue</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

