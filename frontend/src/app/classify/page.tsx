'use client'

import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  AlertCircle, 
  ArrowRight, 
  Brain, 
  CheckCircle2, 
  Database,
  GitBranch, 
  Loader2, 
  Network,
  Search, 
  Sparkles,
  Target,
  Zap,
  Clock,
  TrendingUp,
  Activity
} from 'lucide-react'
import { Sidebar } from '@/components/layout/Sidebar'
import { classificationApi, analyticsApi, type ClassificationResult } from '@/lib/api'

interface Stage {
  id: string
  name: string
  description: string
  icon: any
  color: string
  status: 'pending' | 'processing' | 'completed' | 'error'
  result?: any
  duration?: number
}

const priorityOptions = [
  { value: 'low', label: 'Low', color: 'bg-gray-500' },
  { value: 'medium', label: 'Medium', color: 'bg-blue-500' },
  { value: 'high', label: 'High', color: 'bg-orange-500' },
  { value: 'critical', label: 'Critical', color: 'bg-red-500' },
]

export default function ClassifyPage() {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState('medium')
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<ClassificationResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [currentStage, setCurrentStage] = useState<number>(-1)
  const [stages, setStages] = useState<Stage[]>([])
  const [liveStats, setLiveStats] = useState<any>(null)
  const startTimeRef = useRef<number>(0)
  const stageTimesRef = useRef<number[]>([])

  // Fetch live stats periodically
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const stats = await analyticsApi.getDashboard()
        setLiveStats(stats)
      } catch (e) {
        console.error('Failed to fetch stats')
      }
    }
    fetchStats()
    const interval = setInterval(fetchStats, 5000)
    return () => clearInterval(interval)
  }, [])

  const initializeStages = () => {
    return [
      {
        id: 'keywords',
        name: 'Keyword Extraction',
        description: 'Analyzing ticket content for key terms',
        icon: Zap,
        color: 'cyan',
        status: 'pending' as const,
      },
      {
        id: 'graph',
        name: 'Graph Database Query',
        description: 'Traversing Neo4j classification hierarchy',
        icon: Network,
        color: 'purple',
        status: 'pending' as const,
      },
      {
        id: 'vector',
        name: 'Vector Similarity Search',
        description: 'Finding similar tickets in Milvus',
        icon: Database,
        color: 'blue',
        status: 'pending' as const,
      },
      {
        id: 'llm',
        name: 'LLM Judgment',
        description: 'GPT-4o analyzing classification',
        icon: Brain,
        color: 'orange',
        status: 'pending' as const,
      },
      {
        id: 'ensemble',
        name: 'Ensemble Confidence',
        description: 'Combining scores with calibration',
        icon: TrendingUp,
        color: 'green',
        status: 'pending' as const,
      },
      {
        id: 'routing',
        name: 'Routing Decision',
        description: 'Determining auto-resolve or HITL',
        icon: GitBranch,
        color: 'nexus',
        status: 'pending' as const,
      },
    ]
  }

  const simulateStageProgress = async () => {
    const stageDurations = [300, 800, 600, 2000, 200, 100]
    stageTimesRef.current = []
    
    for (let i = 0; i < 6; i++) {
      setCurrentStage(i)
      setStages(prev => prev.map((s, idx) => ({
        ...s,
        status: idx === i ? 'processing' : idx < i ? 'completed' : 'pending'
      })))
      
      const stageStart = Date.now()
      await new Promise(resolve => setTimeout(resolve, stageDurations[i]))
      stageTimesRef.current.push(Date.now() - stageStart)
      
      setStages(prev => prev.map((s, idx) => ({
        ...s,
        status: idx <= i ? 'completed' : 'pending',
        duration: idx <= i ? stageTimesRef.current[idx] : undefined
      })))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError(null)
    setResult(null)
    setStages(initializeStages())
    setCurrentStage(0)
    startTimeRef.current = Date.now()

    // Start stage simulation in parallel with API call
    const stagePromise = simulateStageProgress()

    try {
      const response = await classificationApi.classify({
        title,
        description,
        priority,
      })
      
      await stagePromise // Ensure stages complete
      
      // Update stages with real results
      setStages(prev => prev.map(s => {
        if (s.id === 'graph') {
          return { ...s, result: { confidence: response.confidence.graph_confidence } }
        }
        if (s.id === 'vector') {
          return { ...s, result: { confidence: response.confidence.vector_confidence } }
        }
        if (s.id === 'llm') {
          return { ...s, result: { confidence: response.confidence.llm_confidence } }
        }
        if (s.id === 'ensemble') {
          return { ...s, result: { score: response.confidence.calibrated_score } }
        }
        return s
      }))
      
      setResult(response)
    } catch (err: any) {
      setError(err.response?.data?.message || 'Classification failed. Please try again.')
      setStages(prev => prev.map((s, idx) => ({
        ...s,
        status: idx === currentStage ? 'error' : s.status
      })))
    } finally {
      setIsLoading(false)
    }
  }

  const handleReset = () => {
    setTitle('')
    setDescription('')
    setPriority('medium')
    setResult(null)
    setError(null)
    setStages([])
    setCurrentStage(-1)
  }

  const getStageColor = (stage: Stage) => {
    const colors: Record<string, string> = {
      cyan: 'from-cyan-500 to-cyan-600',
      purple: 'from-purple-500 to-purple-600',
      blue: 'from-blue-500 to-blue-600',
      orange: 'from-orange-500 to-orange-600',
      green: 'from-green-500 to-green-600',
      nexus: 'from-nexus-500 to-nexus-600',
    }
    return colors[stage.color] || 'from-gray-500 to-gray-600'
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      
      <main className="flex-1 overflow-y-auto bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
        {/* Header */}
        <header className="sticky top-0 z-10 glass border-b border-white/10 px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-nexus-gradient shadow-nexus">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">Live Classification</h1>
                <p className="text-white/50 text-sm">Real-time AI-powered ticket classification</p>
              </div>
            </div>
            
            {/* Live Stats */}
            {liveStats && (
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-green-400 animate-pulse" />
                  <span className="text-sm text-white/70">
                    {liveStats.total_tickets_processed.toLocaleString()} processed
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Target className="w-4 h-4 text-nexus-400" />
                  <span className="text-sm text-white/70">
                    {(liveStats.auto_resolved_rate * 100).toFixed(1)}% auto-resolved
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-blue-400" />
                  <span className="text-sm text-white/70">
                    {liveStats.avg_processing_time_ms}ms avg
                  </span>
                </div>
              </div>
            )}
          </div>
        </header>

        <div className="p-8">
          <div className="max-w-7xl mx-auto">
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
              {/* Input Form */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                className="card xl:col-span-1"
              >
                <h2 className="text-lg font-semibold mb-6 flex items-center gap-2">
                  <MessageSquareIcon className="w-5 h-5 text-nexus-400" />
                  Ticket Details
                </h2>
                
                <form onSubmit={handleSubmit} className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-2">
                      Title
                    </label>
                    <input
                      type="text"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="Enter ticket title..."
                      className="input"
                      required
                      disabled={isLoading}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-2">
                      Description
                    </label>
                    <textarea
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="Describe the issue in detail..."
                      rows={6}
                      className="input resize-none"
                      required
                      disabled={isLoading}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-2">
                      Priority
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      {priorityOptions.map((option) => (
                        <button
                          key={option.value}
                          type="button"
                          onClick={() => setPriority(option.value)}
                          disabled={isLoading}
                          className={`px-4 py-2 rounded-lg border transition-all flex items-center gap-2 ${
                            priority === option.value
                              ? 'border-nexus-500 bg-nexus-500/20'
                              : 'border-white/10 hover:border-white/20'
                          } disabled:opacity-50`}
                        >
                          <span className={`w-2 h-2 rounded-full ${option.color}`} />
                          <span className="text-sm">{option.label}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="flex gap-3 pt-4">
                    <button
                      type="submit"
                      disabled={isLoading || !title || !description}
                      className="btn-primary flex-1 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isLoading ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Processing...
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-4 h-4" />
                          Classify Now
                        </>
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={handleReset}
                      disabled={isLoading}
                      className="btn-secondary disabled:opacity-50"
                    >
                      Reset
                    </button>
                  </div>
                </form>
              </motion.div>

              {/* Pipeline Visualization */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="xl:col-span-2 space-y-6"
              >
                {/* Stage Pipeline */}
                <div className="card">
                  <h2 className="text-lg font-semibold mb-6 flex items-center gap-2">
                    <Activity className="w-5 h-5 text-green-400" />
                    Classification Pipeline
                    {isLoading && (
                      <span className="ml-auto text-sm text-white/50 flex items-center gap-2">
                        <span className="pulse-dot" />
                        Live Processing
                      </span>
                    )}
                  </h2>
                  
                  <div className="relative">
                    {/* Progress Line */}
                    <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-white/10" />
                    {stages.length > 0 && (
                      <motion.div 
                        className="absolute left-6 top-0 w-0.5 bg-nexus-gradient"
                        initial={{ height: 0 }}
                        animate={{ 
                          height: `${((currentStage + 1) / stages.length) * 100}%` 
                        }}
                        transition={{ duration: 0.5 }}
                      />
                    )}
                    
                    <div className="space-y-4">
                      {stages.length > 0 ? stages.map((stage, index) => (
                        <motion.div
                          key={stage.id}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: index * 0.1 }}
                          className={`relative flex items-start gap-4 pl-4 ${
                            stage.status === 'processing' ? 'animate-pulse' : ''
                          }`}
                        >
                          {/* Stage Icon */}
                          <div className={`
                            relative z-10 w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300
                            ${stage.status === 'completed' 
                              ? `bg-gradient-to-br ${getStageColor(stage)} shadow-lg` 
                              : stage.status === 'processing'
                              ? `bg-gradient-to-br ${getStageColor(stage)} shadow-lg animate-pulse`
                              : stage.status === 'error'
                              ? 'bg-red-500/20 border border-red-500/50'
                              : 'bg-white/5 border border-white/10'
                            }
                          `}>
                            {stage.status === 'processing' ? (
                              <Loader2 className="w-5 h-5 text-white animate-spin" />
                            ) : stage.status === 'completed' ? (
                              <CheckCircle2 className="w-5 h-5 text-white" />
                            ) : stage.status === 'error' ? (
                              <AlertCircle className="w-5 h-5 text-red-400" />
                            ) : (
                              <stage.icon className="w-5 h-5 text-white/40" />
                            )}
                          </div>
                          
                          {/* Stage Content */}
                          <div className="flex-1 min-w-0 pb-6">
                            <div className="flex items-center justify-between">
                              <h3 className={`font-semibold ${
                                stage.status === 'completed' ? 'text-white' :
                                stage.status === 'processing' ? 'text-white' :
                                'text-white/50'
                              }`}>
                                {stage.name}
                              </h3>
                              {stage.duration && (
                                <span className="text-xs text-white/40">
                                  {stage.duration}ms
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-white/40 mt-0.5">
                              {stage.description}
                            </p>
                            
                            {/* Stage Result */}
                            {stage.result && (
                              <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                className="mt-3 p-3 rounded-lg bg-white/5 border border-white/10"
                              >
                                {stage.id === 'graph' && (
                                  <div className="flex items-center justify-between">
                                    <span className="text-sm text-white/60">Graph Confidence</span>
                                    <span className="font-mono text-purple-400">
                                      {(stage.result.confidence * 100).toFixed(1)}%
                                    </span>
                                  </div>
                                )}
                                {stage.id === 'vector' && (
                                  <div className="flex items-center justify-between">
                                    <span className="text-sm text-white/60">Vector Confidence</span>
                                    <span className="font-mono text-blue-400">
                                      {(stage.result.confidence * 100).toFixed(1)}%
                                    </span>
                                  </div>
                                )}
                                {stage.id === 'llm' && (
                                  <div className="flex items-center justify-between">
                                    <span className="text-sm text-white/60">LLM Confidence</span>
                                    <span className="font-mono text-orange-400">
                                      {(stage.result.confidence * 100).toFixed(1)}%
                                    </span>
                                  </div>
                                )}
                                {stage.id === 'ensemble' && (
                                  <div className="flex items-center justify-between">
                                    <span className="text-sm text-white/60">Calibrated Score</span>
                                    <span className={`font-mono font-bold ${
                                      stage.result.score >= 0.7 ? 'text-green-400' : 'text-orange-400'
                                    }`}>
                                      {(stage.result.score * 100).toFixed(1)}%
                                    </span>
                                  </div>
                                )}
                              </motion.div>
                            )}
                          </div>
                        </motion.div>
                      )) : (
                        <div className="text-center py-12 text-white/30">
                          <Network className="w-12 h-12 mx-auto mb-4 opacity-50" />
                          <p>Submit a ticket to see the classification pipeline</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Results */}
                <AnimatePresence mode="wait">
                  {error && (
                    <motion.div
                      key="error"
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      className="card border-red-500/30 bg-red-500/10"
                    >
                      <div className="flex items-center gap-3 text-red-400">
                        <AlertCircle className="w-5 h-5" />
                        <span>{error}</span>
                      </div>
                    </motion.div>
                  )}

                  {result && (
                    <motion.div
                      key="result"
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="grid grid-cols-1 md:grid-cols-2 gap-6"
                    >
                      {/* Classification Path */}
                      <div className="card">
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                          <Target className="w-5 h-5 text-green-400" />
                          Classification Result
                        </h3>
                        
                        <div className="space-y-3">
                          <div className="flex items-center gap-3">
                            <span className="px-3 py-2 rounded-lg bg-purple-500/20 text-purple-400 font-medium">
                              {result.classification.level1}
                            </span>
                          </div>
                          <div className="flex items-center gap-3 pl-4">
                            <ArrowRight className="w-4 h-4 text-white/30" />
                            <span className="px-3 py-2 rounded-lg bg-blue-500/20 text-blue-400 font-medium">
                              {result.classification.level2}
                            </span>
                          </div>
                          <div className="flex items-center gap-3 pl-8">
                            <ArrowRight className="w-4 h-4 text-white/30" />
                            <span className="px-3 py-2 rounded-lg bg-nexus-500/20 text-nexus-400 font-medium">
                              {result.classification.level3}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Routing Decision */}
                      <div className={`card ${
                        result.routing.auto_resolved 
                          ? 'border-green-500/30 bg-gradient-to-br from-green-500/10 to-emerald-500/5' 
                          : 'border-orange-500/30 bg-gradient-to-br from-orange-500/10 to-amber-500/5'
                      }`}>
                        <div className="flex items-start gap-4">
                          {result.routing.auto_resolved ? (
                            <div className="p-3 rounded-xl bg-green-500/20">
                              <CheckCircle2 className="w-8 h-8 text-green-400" />
                            </div>
                          ) : (
                            <div className="p-3 rounded-xl bg-orange-500/20">
                              <AlertCircle className="w-8 h-8 text-orange-400" />
                            </div>
                          )}
                          <div>
                            <p className={`text-xl font-bold ${
                              result.routing.auto_resolved ? 'text-green-400' : 'text-orange-400'
                            }`}>
                              {result.routing.auto_resolved ? 'Auto-Resolved' : 'Requires Review'}
                            </p>
                            <p className="text-sm text-white/50 mt-1">
                              {result.routing.auto_resolved 
                                ? `High confidence classification completed in ${result.processing.time_ms}ms`
                                : result.routing.hitl_reason || 'Low confidence - routed to HITL queue'
                              }
                            </p>
                            <div className="mt-4 flex items-center gap-4 text-sm">
                              <div>
                                <span className="text-white/40">Confidence</span>
                                <p className="font-mono font-bold text-lg">
                                  {(result.confidence.calibrated_score * 100).toFixed(1)}%
                                </p>
                              </div>
                              <div>
                                <span className="text-white/40">Agreement</span>
                                <p className="font-mono font-bold text-lg">
                                  {(result.confidence.component_agreement * 100).toFixed(0)}%
                                </p>
                              </div>
                              <div>
                                <span className="text-white/40">Time</span>
                                <p className="font-mono font-bold text-lg">
                                  {result.processing.time_ms}ms
                                </p>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

// Import icon component
function MessageSquareIcon(props: any) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
    </svg>
  )
}
