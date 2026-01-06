'use client'

import { useState, useEffect } from 'react'
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
  Upload,
  X
} from 'lucide-react'
import { Sidebar } from '@/components/layout/Sidebar'
import { batchApi, type BatchResult } from '@/lib/api'

export default function BatchPage() {
  const [batches, setBatches] = useState<BatchResult[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedBatch, setSelectedBatch] = useState<BatchResult | null>(null)
  const [batchResults, setBatchResults] = useState<any>(null)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [uploadData, setUploadData] = useState<string>('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [pollingBatchId, setPollingBatchId] = useState<string | null>(null)

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

  const handleSubmitBatch = async () => {
    if (!uploadData.trim()) return
    
    setIsSubmitting(true)
    try {
      // Parse the JSON input
      const tickets = JSON.parse(uploadData)
      
      if (!Array.isArray(tickets)) {
        throw new Error('Input must be an array of tickets')
      }
      
      const result = await batchApi.submit(tickets)
      setShowUploadModal(false)
      setUploadData('')
      setPollingBatchId(result.batch_id)
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

  const sampleBatchData = JSON.stringify([
    { title: "Cannot access dashboard", description: "Getting 403 error when trying to access the main dashboard" },
    { title: "Payment failed", description: "Credit card payment keeps failing with no error message" },
    { title: "Password reset not working", description: "Reset link expires immediately after clicking" }
  ], null, 2)

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      
      <main className="flex-1 overflow-y-auto bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
        {/* Header */}
        <header className="sticky top-0 z-10 glass border-b border-white/10 px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 shadow-lg">
                <Layers className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">Batch Processing</h1>
                <p className="text-white/50 text-sm">Process multiple tickets at once</p>
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

        <div className="p-8">
          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div className="card bg-gradient-to-br from-nexus-500/10 to-cyan-500/5">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-nexus-500/20">
                  <Layers className="w-5 h-5 text-nexus-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{batches.length}</p>
                  <p className="text-sm text-white/50">Total Batches</p>
                </div>
              </div>
            </div>

            <div className="card bg-gradient-to-br from-blue-500/10 to-cyan-500/5">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-500/20">
                  <Loader2 className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {batches.filter(b => b.status === 'processing').length}
                  </p>
                  <p className="text-sm text-white/50">Processing</p>
                </div>
              </div>
            </div>

            <div className="card bg-gradient-to-br from-green-500/10 to-emerald-500/5">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-green-500/20">
                  <CheckCircle2 className="w-5 h-5 text-green-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {batches.filter(b => b.status === 'completed').length}
                  </p>
                  <p className="text-sm text-white/50">Completed</p>
                </div>
              </div>
            </div>

            <div className="card bg-gradient-to-br from-purple-500/10 to-pink-500/5">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-purple-500/20">
                  <FileText className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {batches.reduce((sum, b) => sum + b.ticket_count, 0)}
                  </p>
                  <p className="text-sm text-white/50">Total Tickets</p>
                </div>
              </div>
            </div>
          </div>

          {/* Batch List */}
          <div className="card">
            <h2 className="text-lg font-semibold mb-6">Batch Jobs</h2>
            
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-white/30" />
              </div>
            ) : batches.length === 0 ? (
              <div className="text-center py-12">
                <Layers className="w-12 h-12 mx-auto mb-4 text-white/20" />
                <p className="text-white/50 mb-4">No batch jobs yet</p>
                <button 
                  onClick={() => setShowUploadModal(true)}
                  className="text-nexus-400 hover:text-nexus-300"
                >
                  Submit your first batch →
                </button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-white/10">
                      <th className="text-left py-3 px-4 text-sm font-medium text-white/50">Batch ID</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-white/50">Status</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-white/50">Tickets</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-white/50">Progress</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-white/50">Created</th>
                      <th className="text-right py-3 px-4 text-sm font-medium text-white/50">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {batches.map((batch) => (
                      <motion.tr
                        key={batch.batch_id}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="border-b border-white/5 hover:bg-white/5"
                      >
                        <td className="py-4 px-4">
                          <span className="font-mono text-sm">{batch.batch_id}</span>
                        </td>
                        <td className="py-4 px-4">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(batch.status)}`}>
                            {batch.status}
                          </span>
                        </td>
                        <td className="py-4 px-4 text-sm">{batch.ticket_count}</td>
                        <td className="py-4 px-4">
                          <div className="w-32">
                            <div className="flex items-center justify-between text-xs mb-1">
                              <span className="text-white/50">
                                {Math.round(batch.progress * 100)}%
                              </span>
                            </div>
                            <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                              <motion.div
                                className="h-full bg-nexus-500 rounded-full"
                                initial={{ width: 0 }}
                                animate={{ width: `${batch.progress * 100}%` }}
                              />
                            </div>
                          </div>
                        </td>
                        <td className="py-4 px-4 text-sm text-white/50">
                          {batch.created_at ? new Date(batch.created_at).toLocaleString() : '-'}
                        </td>
                        <td className="py-4 px-4 text-right">
                          {batch.status === 'completed' && (
                            <button
                              onClick={() => handleViewResults(batch.batch_id)}
                              className="text-nexus-400 hover:text-nexus-300 text-sm"
                            >
                              View Results →
                            </button>
                          )}
                          {batch.status === 'processing' && (
                            <span className="flex items-center gap-2 text-sm text-blue-400">
                              <Loader2 className="w-3 h-3 animate-spin" />
                              Processing...
                            </span>
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
              className="card mt-6"
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold">Batch Results</h2>
                <button
                  onClick={() => setBatchResults(null)}
                  className="text-white/40 hover:text-white"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              <div className="space-y-4 max-h-96 overflow-y-auto">
                {batchResults.results?.map((result: any, idx: number) => (
                  <div key={idx} className="p-4 rounded-lg bg-white/5 border border-white/10">
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="font-medium">{result.title}</h4>
                      <span className={`px-2 py-1 rounded text-xs ${
                        result.routing?.auto_resolved ? 'bg-green-500/20 text-green-400' : 'bg-orange-500/20 text-orange-400'
                      }`}>
                        {result.routing?.auto_resolved ? 'Auto-Resolved' : 'HITL'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-purple-400">{result.classification?.level1}</span>
                      <ArrowRight className="w-3 h-3 text-white/30" />
                      <span className="text-blue-400">{result.classification?.level2}</span>
                      <ArrowRight className="w-3 h-3 text-white/30" />
                      <span className="text-nexus-400">{result.classification?.level3}</span>
                      <span className="ml-auto font-mono text-green-400">
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
              className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
              onClick={() => setShowUploadModal(false)}
            >
              <motion.div
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.95, opacity: 0 }}
                onClick={(e) => e.stopPropagation()}
                className="w-full max-w-2xl card"
              >
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold">Submit Batch</h2>
                  <button 
                    onClick={() => setShowUploadModal(false)}
                    className="p-1 text-white/40 hover:text-white"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-2">
                      Tickets JSON Array
                    </label>
                    <textarea
                      value={uploadData}
                      onChange={(e) => setUploadData(e.target.value)}
                      placeholder={sampleBatchData}
                      rows={12}
                      className="input resize-none font-mono text-sm"
                    />
                    <p className="text-xs text-white/40 mt-2">
                      Enter a JSON array of tickets with title and description fields
                    </p>
                  </div>
                  
                  <button
                    onClick={() => setUploadData(sampleBatchData)}
                    className="text-sm text-nexus-400 hover:text-nexus-300"
                  >
                    Load sample data →
                  </button>
                  
                  <div className="flex gap-3 pt-4">
                    <button
                      onClick={() => setShowUploadModal(false)}
                      className="btn-secondary flex-1"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSubmitBatch}
                      disabled={!uploadData.trim() || isSubmitting}
                      className="btn-primary flex-1 flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                      {isSubmitting ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Submitting...
                        </>
                      ) : (
                        <>
                          <Play className="w-4 h-4" />
                          Submit Batch
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

