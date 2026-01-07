'use client'

import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Download,
  FileText,
  Layers,
  Loader2,
  Play,
  RefreshCw,
  Target,
  Terminal,
  Upload,
  X,
  Zap,
  Activity,
  Brain,
  Database,
  Network
} from 'lucide-react'
import { Sidebar } from '@/components/layout/Sidebar'
import { batchApi, type BatchResult } from '@/lib/api'

interface StreamEvent {
  type: string
  batch_id?: string
  ticket_index?: number
  total?: number
  title?: string
  classification?: {
    level1: string
    level2: string
    level3: string
  }
  confidence?: {
    graph: number
    vector: number
    llm: number
    final: number
  }
  routing?: {
    auto_resolved: boolean
    requires_hitl: boolean
  }
  processing_ms?: number
  timestamp?: string
  progress?: number
  auto_resolved_so_far?: number
  hitl_so_far?: number
  total_tickets?: number
  auto_resolved?: number
  requires_hitl?: number
  processing_time_ms?: number
  message?: string
}

export default function BatchPage() {
  const [batches, setBatches] = useState<BatchResult[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedBatch, setSelectedBatch] = useState<BatchResult | null>(null)
  const [batchResults, setBatchResults] = useState<any>(null)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [uploadData, setUploadData] = useState<string>('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [pollingBatchId, setPollingBatchId] = useState<string | null>(null)
  
  // Live streaming state
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamEvents, setStreamEvents] = useState<StreamEvent[]>([])
  const [currentProgress, setCurrentProgress] = useState(0)
  const [streamStats, setStreamStats] = useState({
    processed: 0,
    total: 0,
    autoResolved: 0,
    hitl: 0,
    avgTime: 0,
  })
  const wsRef = useRef<WebSocket | null>(null)
  const terminalRef = useRef<HTMLDivElement>(null)

  const fetchBatches = async () => {
    try {
      const res = await batchApi.list()
      setBatches(res.batches)
    } catch (e) {
      console.error('Failed to fetch batches')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchBatches()
    const interval = setInterval(fetchBatches, 10000)
    return () => clearInterval(interval)
  }, [])

  // Auto-scroll terminal
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight
    }
  }, [streamEvents])

  // Poll for batch status updates
  useEffect(() => {
    if (!pollingBatchId) return
    
    const pollStatus = async () => {
      try {
        const status = await batchApi.getStatus(pollingBatchId)
        setBatches(prev => prev.map(b => 
          b.batch_id === pollingBatchId ? { ...b, ...status } : b
        ))
        
        if (status.status === 'completed' || status.status === 'failed') {
          setPollingBatchId(null)
        }
      } catch (e) {
        console.error('Failed to poll batch status')
      }
    }
    
    const interval = setInterval(pollStatus, 2000)
    return () => clearInterval(interval)
  }, [pollingBatchId])

  const connectToStream = (batchId: string) => {
    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.close()
    }
    
    const wsUrl = `ws://localhost:8000/api/v1/batch/stream/${batchId}`
    console.log('[Batch] Connecting to WebSocket:', wsUrl)
    
    const ws = new WebSocket(wsUrl)
    
    ws.onopen = () => {
      console.log('[Batch] WebSocket connected')
      setIsStreaming(true)
      setStreamEvents(prev => [...prev, {
        type: 'system',
        message: `[CONNECTED] Live stream active for ${batchId}`,
        timestamp: new Date().toISOString()
      }])
    }
    
    ws.onmessage = (event) => {
      try {
        const data: StreamEvent = JSON.parse(event.data)
        console.log('[Batch] Event:', data.type)
        
        if (data.type === 'heartbeat') return
        
        setStreamEvents(prev => [...prev.slice(-200), data]) // Keep last 200 events
        
        if (data.type === 'ticket_classified') {
          setCurrentProgress(data.progress || 0)
          setStreamStats({
            processed: data.ticket_index || 0,
            total: data.total || 0,
            autoResolved: data.auto_resolved_so_far || 0,
            hitl: data.hitl_so_far || 0,
            avgTime: data.processing_ms || 0,
          })
        }
        
        if (data.type === 'batch_completed') {
          setIsStreaming(false)
          fetchBatches()
        }
      } catch (e) {
        console.error('[Batch] Parse error:', e)
      }
    }
    
    ws.onerror = (error) => {
      console.error('[Batch] WebSocket error:', error)
      setStreamEvents(prev => [...prev, {
        type: 'error',
        message: '[ERROR] WebSocket connection failed - check console',
        timestamp: new Date().toISOString()
      }])
    }
    
    ws.onclose = (event) => {
      console.log('[Batch] WebSocket closed:', event.code, event.reason)
      setIsStreaming(false)
      if (event.code !== 1000) {
        setStreamEvents(prev => [...prev, {
          type: 'system',
          message: `[DISCONNECTED] Connection closed (${event.code})`,
          timestamp: new Date().toISOString()
        }])
      }
    }
    
    wsRef.current = ws
  }

  const handleSubmitBatch = async (withStreaming: boolean = false) => {
    if (!uploadData.trim()) return
    
    setIsSubmitting(true)
    try {
      let tickets
      const parsed = JSON.parse(uploadData)
      
      // Handle both array and {tickets: [...]} format
      if (Array.isArray(parsed)) {
        tickets = parsed
      } else if (parsed.tickets && Array.isArray(parsed.tickets)) {
        tickets = parsed.tickets
      } else {
        throw new Error('Input must be an array of tickets or {tickets: [...]}')
      }
      
      const result = await batchApi.submit(tickets)
      setShowUploadModal(false)
      setUploadData('')
      
      if (withStreaming) {
        // Reset stream state and connect
        setStreamEvents([])
        setCurrentProgress(0)
        setStreamStats({ processed: 0, total: tickets.length, autoResolved: 0, hitl: 0, avgTime: 0 })
        connectToStream(result.batch_id)
      } else {
        setPollingBatchId(result.batch_id)
      }
      
      fetchBatches()
    } catch (e: any) {
      alert(e.message || 'Failed to submit batch')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleViewResults = async (batchId: string) => {
    try {
      const results = await batchApi.getResult(batchId)
      setBatchResults(results)
    } catch (e) {
      console.error('Failed to fetch results')
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-500/20 text-green-400'
      case 'processing': return 'bg-blue-500/20 text-blue-400'
      case 'pending': return 'bg-yellow-500/20 text-yellow-400'
      case 'failed': return 'bg-red-500/20 text-red-400'
      default: return 'bg-gray-500/20 text-gray-400'
    }
  }

  const formatEventLine = (event: StreamEvent) => {
    const time = event.timestamp ? new Date(event.timestamp).toLocaleTimeString('en-US', { hour12: false }) : ''
    
    switch (event.type) {
      case 'connected':
      case 'system':
        return { color: 'text-emerald-400', text: `${time} ${event.message}` }
      case 'batch_started':
        return { color: 'text-cyan-400', text: `${time} [BATCH] Started processing ${event.total_tickets} tickets` }
      case 'ticket_processing':
        return { color: 'text-slate-500', text: `${time} [${event.ticket_index}/${event.total}] Processing: ${event.title}...` }
      case 'ticket_classified':
        const conf = (event.confidence?.final || 0) * 100
        const autoText = event.routing?.auto_resolved ? '✓ AUTO' : '→ HITL'
        const autoColor = event.routing?.auto_resolved ? 'text-emerald-400' : 'text-amber-400'
        return { 
          color: autoColor, 
          text: `${time} [${event.ticket_index}/${event.total}] ${autoText} | ${conf.toFixed(1)}% | ${event.classification?.level3 || 'Unknown'} | ${event.processing_ms}ms`
        }
      case 'batch_completed':
        return { 
          color: 'text-emerald-400', 
          text: `${time} [COMPLETE] ${event.total_tickets} tickets | ${event.auto_resolved} auto-resolved | ${event.requires_hitl} HITL | ${(event.processing_time_ms || 0) / 1000}s total`
        }
      case 'error':
        return { color: 'text-red-400', text: `${time} ${event.message}` }
      default:
        return { color: 'text-slate-400', text: `${time} ${JSON.stringify(event)}` }
    }
  }

  const sampleBatchData = JSON.stringify([
    { title: "Cannot access dashboard", description: "Getting 403 error when trying to access the main dashboard" },
    { title: "Payment failed", description: "Credit card payment keeps failing with no error message" },
    { title: "Password reset not working", description: "Reset link expires immediately after clicking" }
  ], null, 2)

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      
      <main className="flex-1 overflow-y-auto bg-slate-950">
        {/* Header */}
        <header className="sticky top-0 z-10 bg-slate-950/95 border-b border-slate-800 px-8 py-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 shadow-lg">
                <Layers className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-100">Batch Processing</h1>
                <p className="text-slate-500 text-sm font-mono">Process multiple tickets with live streaming</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <button 
                onClick={() => fetchBatches()}
                className="btn-secondary flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh
              </button>
              <button 
                onClick={() => setShowUploadModal(true)}
                className="btn-primary flex items-center gap-2"
              >
                <Upload className="w-4 h-4" />
                New Batch
              </button>
            </div>
          </div>
        </header>

        <div className="p-8 space-y-6">
          {/* Live Streaming Terminal */}
          {(isStreaming || streamEvents.length > 0) && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-black border border-emerald-500/30 rounded-lg overflow-hidden"
            >
              {/* Terminal Header */}
              <div className="flex items-center justify-between px-4 py-2 bg-slate-900 border-b border-slate-800">
                <div className="flex items-center gap-3">
                  <Terminal className="w-4 h-4 text-emerald-400" />
                  <span className="text-emerald-400 font-mono text-sm">BATCH PROCESSING TERMINAL</span>
                  {isStreaming && (
                    <span className="flex items-center gap-1 text-emerald-400 text-xs">
                      <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                      LIVE
                    </span>
                  )}
                </div>
                <button 
                  onClick={() => { setStreamEvents([]); setIsStreaming(false); }}
                  className="text-slate-500 hover:text-slate-300"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              
              {/* Progress Bar */}
              {streamStats.total > 0 && (
                <div className="px-4 py-3 bg-slate-900/50 border-b border-slate-800">
                  <div className="flex items-center justify-between text-xs font-mono mb-2">
                    <div className="flex items-center gap-4">
                      <span className="text-emerald-400">
                        {streamStats.processed}/{streamStats.total} processed
                      </span>
                      <span className="text-emerald-400/70">
                        ✓ {streamStats.autoResolved} auto
                      </span>
                      <span className="text-amber-400/70">
                        → {streamStats.hitl} HITL
                      </span>
                    </div>
                    <span className="text-slate-500">{currentProgress}%</span>
                  </div>
                  <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500"
                      initial={{ width: 0 }}
                      animate={{ width: `${currentProgress}%` }}
                      transition={{ duration: 0.3 }}
                    />
                  </div>
                </div>
              )}
              
              {/* Live Stats Grid */}
              {isStreaming && (
                <div className="grid grid-cols-4 gap-px bg-slate-800 border-b border-slate-800">
                  <div className="bg-slate-900 px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Network className="w-4 h-4 text-violet-400" />
                      <span className="text-xs text-slate-500 font-mono">GRAPH</span>
                    </div>
                    <p className="text-lg font-mono text-violet-400 mt-1">
                      {streamEvents.length > 0 && streamEvents[streamEvents.length - 1].confidence 
                        ? `${(streamEvents[streamEvents.length - 1].confidence!.graph * 100).toFixed(0)}%` 
                        : '--'}
                    </p>
                  </div>
                  <div className="bg-slate-900 px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Database className="w-4 h-4 text-sky-400" />
                      <span className="text-xs text-slate-500 font-mono">VECTOR</span>
                    </div>
                    <p className="text-lg font-mono text-sky-400 mt-1">
                      {streamEvents.length > 0 && streamEvents[streamEvents.length - 1].confidence 
                        ? `${(streamEvents[streamEvents.length - 1].confidence!.vector * 100).toFixed(0)}%` 
                        : '--'}
                    </p>
                  </div>
                  <div className="bg-slate-900 px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Brain className="w-4 h-4 text-amber-400" />
                      <span className="text-xs text-slate-500 font-mono">LLM</span>
                    </div>
                    <p className="text-lg font-mono text-amber-400 mt-1">
                      {streamEvents.length > 0 && streamEvents[streamEvents.length - 1].confidence 
                        ? `${(streamEvents[streamEvents.length - 1].confidence!.llm * 100).toFixed(0)}%` 
                        : '--'}
                    </p>
                  </div>
                  <div className="bg-slate-900 px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Zap className="w-4 h-4 text-emerald-400" />
                      <span className="text-xs text-slate-500 font-mono">FINAL</span>
                    </div>
                    <p className="text-lg font-mono text-emerald-400 mt-1">
                      {streamEvents.length > 0 && streamEvents[streamEvents.length - 1].confidence 
                        ? `${(streamEvents[streamEvents.length - 1].confidence!.final * 100).toFixed(0)}%` 
                        : '--'}
                    </p>
                  </div>
                </div>
              )}
              
              {/* Terminal Output */}
              <div 
                ref={terminalRef}
                className="h-72 overflow-y-auto p-4 font-mono text-xs leading-relaxed"
              >
                {streamEvents.map((event, i) => {
                  const { color, text } = formatEventLine(event)
                  return (
                    <div key={i} className={`${color} whitespace-pre-wrap`}>
                      {text}
                    </div>
                  )
                })}
                {isStreaming && (
                  <span className="text-emerald-400 animate-pulse">█</span>
                )}
              </div>
            </motion.div>
          )}

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-5">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-purple-500/20">
                  <Layers className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-100">{batches.length}</p>
                  <p className="text-sm text-slate-500">Total Batches</p>
                </div>
              </div>
            </div>

            <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-5">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-500/20">
                  <Loader2 className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-100">
                    {batches.filter(b => b.status === 'processing').length}
                  </p>
                  <p className="text-sm text-slate-500">Processing</p>
                </div>
              </div>
            </div>

            <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-5">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/20">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-100">
                    {batches.filter(b => b.status === 'completed').length}
                  </p>
                  <p className="text-sm text-slate-500">Completed</p>
                </div>
              </div>
            </div>

            <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-5">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-pink-500/20">
                  <FileText className="w-5 h-5 text-pink-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-100">
                    {batches.reduce((sum, b) => sum + b.ticket_count, 0)}
                  </p>
                  <p className="text-sm text-slate-500">Total Tickets</p>
                </div>
              </div>
            </div>
          </div>

          {/* Batch List */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-slate-100 mb-6">Batch Jobs</h2>
            
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-slate-600" />
              </div>
            ) : batches.length === 0 ? (
              <div className="text-center py-12">
                <Layers className="w-12 h-12 mx-auto mb-4 text-slate-700" />
                <p className="text-slate-500 mb-4">No batch jobs yet</p>
                <button 
                  onClick={() => setShowUploadModal(true)}
                  className="text-emerald-400 hover:text-emerald-300"
                >
                  Submit your first batch →
                </button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-800">
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Batch ID</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Status</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Tickets</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Progress</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Created</th>
                      <th className="text-right py-3 px-4 text-sm font-medium text-slate-500">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {batches.map((batch) => (
                      <motion.tr
                        key={batch.batch_id}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="border-b border-slate-800/50 hover:bg-slate-800/30"
                      >
                        <td className="py-4 px-4">
                          <span className="font-mono text-sm text-slate-300">{batch.batch_id}</span>
                        </td>
                        <td className="py-4 px-4">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(batch.status)}`}>
                            {batch.status}
                          </span>
                        </td>
                        <td className="py-4 px-4 text-sm text-slate-400">{batch.ticket_count}</td>
                        <td className="py-4 px-4">
                          <div className="w-32">
                            <div className="flex items-center justify-between text-xs mb-1">
                              <span className="text-slate-500">
                                {Math.round(batch.progress)}%
                              </span>
                            </div>
                            <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                              <motion.div
                                className="h-full bg-emerald-500 rounded-full"
                                initial={{ width: 0 }}
                                animate={{ width: `${batch.progress}%` }}
                              />
                            </div>
                          </div>
                        </td>
                        <td className="py-4 px-4 text-sm text-slate-500">
                          {batch.created_at ? new Date(batch.created_at).toLocaleString() : '-'}
                        </td>
                        <td className="py-4 px-4 text-right">
                          {batch.status === 'completed' && (
                            <button
                              onClick={() => handleViewResults(batch.batch_id)}
                              className="text-emerald-400 hover:text-emerald-300 text-sm"
                            >
                              View Results →
                            </button>
                          )}
                          {batch.status === 'processing' && (
                            <button
                              onClick={() => {
                                // Reset and connect
                                setStreamEvents([{
                                  type: 'system',
                                  message: `[CONNECTING] Joining batch ${batch.batch_id} stream...`,
                                  timestamp: new Date().toISOString()
                                }])
                                setStreamStats({ 
                                  processed: 0, 
                                  total: batch.ticket_count, 
                                  autoResolved: 0, 
                                  hitl: 0, 
                                  avgTime: 0 
                                })
                                setCurrentProgress(batch.progress)
                                connectToStream(batch.batch_id)
                              }}
                              className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300"
                            >
                              <Activity className="w-3 h-3" />
                              Watch Live
                            </button>
                          )}
                        </td>
                      </motion.tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Results Preview */}
          {batchResults && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-slate-900/50 border border-slate-800 rounded-lg p-6"
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold text-slate-100">Batch Results</h2>
                <button
                  onClick={() => setBatchResults(null)}
                  className="text-slate-500 hover:text-slate-300"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              <div className="space-y-4 max-h-96 overflow-y-auto">
                {batchResults.results?.map((result: any, idx: number) => (
                  <div key={idx} className="p-4 rounded-lg bg-slate-800/50 border border-slate-700">
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="font-medium text-slate-200">{result.title}</h4>
                      <span className={`px-2 py-1 rounded text-xs ${
                        result.routing?.auto_resolved ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'
                      }`}>
                        {result.routing?.auto_resolved ? 'Auto-Resolved' : 'HITL'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-purple-400">{result.classification?.level1}</span>
                      <ArrowRight className="w-3 h-3 text-slate-600" />
                      <span className="text-blue-400">{result.classification?.level2}</span>
                      <ArrowRight className="w-3 h-3 text-slate-600" />
                      <span className="text-emerald-400">{result.classification?.level3}</span>
                      <span className="ml-auto font-mono text-emerald-400">
                        {((result.confidence?.calibrated_score || 0) * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </div>

        {/* Upload Modal */}
        <AnimatePresence>
          {showUploadModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
              onClick={() => setShowUploadModal(false)}
            >
              <motion.div
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.95, opacity: 0 }}
                onClick={(e) => e.stopPropagation()}
                className="w-full max-w-2xl bg-slate-900 border border-slate-700 rounded-lg p-6"
              >
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold text-slate-100">Submit Batch</h2>
                  <button 
                    onClick={() => setShowUploadModal(false)}
                    className="p-1 text-slate-500 hover:text-slate-300"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-2">
                      Tickets JSON (array or {"{"} tickets: [...] {"}"})
                    </label>
                    <textarea
                      value={uploadData}
                      onChange={(e) => setUploadData(e.target.value)}
                      placeholder={sampleBatchData}
                      rows={12}
                      className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg font-mono text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-emerald-500"
                    />
                    <p className="text-xs text-slate-500 mt-2">
                      Each ticket needs: title, description. Optional: priority, metadata
                    </p>
                  </div>
                  
                  <div className="flex gap-2 flex-wrap">
                    <button
                      onClick={() => setUploadData(sampleBatchData)}
                      className="text-sm text-slate-400 hover:text-slate-300"
                    >
                      3 tickets →
                    </button>
                    <button
                      onClick={async () => {
                        try {
                          const res = await fetch('/batch_50_sample.json')
                          const data = await res.json()
                          setUploadData(JSON.stringify(data, null, 2))
                        } catch {
                          alert('Could not load sample')
                        }
                      }}
                      className="text-sm text-emerald-400 hover:text-emerald-300"
                    >
                      50 tickets →
                    </button>
                    <button
                      onClick={async () => {
                        try {
                          const res = await fetch('/batch_100_sample.json')
                          const data = await res.json()
                          setUploadData(JSON.stringify(data, null, 2))
                        } catch {
                          alert('Could not load sample')
                        }
                      }}
                      className="text-sm text-sky-400 hover:text-sky-300"
                    >
                      100 tickets →
                    </button>
                  </div>
                  
                  <div className="flex gap-3 pt-4">
                    <button
                      onClick={() => setShowUploadModal(false)}
                      className="flex-1 px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-300 hover:bg-slate-700"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => handleSubmitBatch(false)}
                      disabled={!uploadData.trim() || isSubmitting}
                      className="flex-1 px-4 py-2 bg-slate-700 rounded-lg text-slate-300 hover:bg-slate-600 disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      <Play className="w-4 h-4" />
                      Submit
                    </button>
                    <button
                      onClick={() => handleSubmitBatch(true)}
                      disabled={!uploadData.trim() || isSubmitting}
                      className="flex-1 px-4 py-2 bg-emerald-600 rounded-lg text-white hover:bg-emerald-500 disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      {isSubmitting ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Submitting...
                        </>
                      ) : (
                        <>
                          <Terminal className="w-4 h-4" />
                          Submit + Stream Live
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  )
}
