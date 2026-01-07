'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  AlertCircle, 
  ArrowRight,
  Brain,
  CheckCircle2, 
  ChevronRight,
  Clock,
  Filter,
  Loader2,
  MessageSquare,
  RefreshCw,
  Search,
  Target,
  ThumbsDown,
  ThumbsUp,
  Timer,
  TrendingUp,
  Users,
  X,
  Zap
} from 'lucide-react'
import { Sidebar } from '@/components/layout/Sidebar'
import { hitlApi, classificationApi, type HITLTask } from '@/lib/api'

export default function HITLPage() {
  const [tasks, setTasks] = useState<HITLTask[]>([])
  const [stats, setStats] = useState<any>(null)
  const [selectedTask, setSelectedTask] = useState<HITLTask | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [filter, setFilter] = useState<'pending' | 'in_progress' | 'all'>('pending')
  const [hierarchy, setHierarchy] = useState<any>(null)
  const [correction, setCorrection] = useState({
    level1: '',
    level2: '',
    level3: '',
    isCorrect: false,
    notes: '',
  })
  const [reviewStartTime, setReviewStartTime] = useState<number>(0)

  // Fetch tasks and stats
  const fetchData = async () => {
    try {
      // Fetch tasks and stats (required)
      const [tasksRes, statsRes] = await Promise.all([
        hitlApi.getTasks({ status: filter === 'all' ? undefined : filter }),
        hitlApi.getStats(),
      ])
      setTasks(tasksRes.tasks || [])
      setStats(statsRes)
      
      // Fetch hierarchy separately (optional - for correction dropdowns)
      try {
        const hierRes = await classificationApi.getHierarchy()
        setHierarchy(hierRes.hierarchy)
      } catch (hierError) {
        console.warn('Failed to fetch hierarchy, corrections may be limited:', hierError)
        // Set a basic hierarchy structure so the page still works
        setHierarchy({})
      }
    } catch (e) {
      console.error('Failed to fetch HITL data:', e)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 10000) // Refresh every 10s
    return () => clearInterval(interval)
  }, [filter])

  const handleSelectTask = (task: HITLTask) => {
    setSelectedTask(task)
    setCorrection({
      level1: task.ai_level1,
      level2: task.ai_level2,
      level3: task.ai_level3,
      isCorrect: false,
      notes: '',
    })
    setReviewStartTime(Date.now())
  }

  const handleConfirmCorrect = async () => {
    if (!selectedTask) return
    setIsSubmitting(true)
    
    try {
      await hitlApi.submitCorrection({
        task_id: selectedTask.id,
        corrected_level1: selectedTask.ai_level1,
        corrected_level2: selectedTask.ai_level2,
        corrected_level3: selectedTask.ai_level3,
        is_correct: true,
        correction_notes: 'AI classification confirmed as correct',
        review_time_seconds: Math.floor((Date.now() - reviewStartTime) / 1000),
      })
      
      setSelectedTask(null)
      fetchData()
    } catch (e) {
      console.error('Failed to submit correction')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleSubmitCorrection = async () => {
    if (!selectedTask) return
    setIsSubmitting(true)
    
    try {
      await hitlApi.submitCorrection({
        task_id: selectedTask.id,
        corrected_level1: correction.level1,
        corrected_level2: correction.level2,
        corrected_level3: correction.level3,
        is_correct: false,
        correction_notes: correction.notes,
        review_time_seconds: Math.floor((Date.now() - reviewStartTime) / 1000),
      })
      
      setSelectedTask(null)
      fetchData()
    } catch (e) {
      console.error('Failed to submit correction')
    } finally {
      setIsSubmitting(false)
    }
  }

  const getLevel2Options = (level1: string) => {
    if (!hierarchy || !hierarchy[level1]) return []
    return Object.keys(hierarchy[level1].subcategories || {})
  }

  const getLevel3Options = (level1: string, level2: string) => {
    if (!hierarchy || !hierarchy[level1]?.subcategories?.[level2]) return []
    return hierarchy[level1].subcategories[level2].issues?.map((i: any) => i.name) || []
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'text-red-400 bg-red-500/20'
      case 'high': return 'text-orange-400 bg-orange-500/20'
      case 'normal': return 'text-blue-400 bg-blue-500/20'
      default: return 'text-gray-400 bg-gray-500/20'
    }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      
      <main className="flex-1 overflow-y-auto bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
        {/* Header */}
        <header className="sticky top-0 z-10 glass border-b border-white/10 px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-gradient-to-br from-orange-500 to-amber-500 shadow-lg">
                <Users className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">Human-in-the-Loop Review</h1>
                <p className="text-white/50 text-sm">Review and correct AI classifications</p>
              </div>
            </div>
            
            <button 
              onClick={() => fetchData()}
              className="btn-secondary flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>
        </header>

        <div className="p-8">
          {/* Stats Cards */}
          {stats && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="card bg-gradient-to-br from-orange-500/10 to-amber-500/5"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-orange-500/20">
                    <Clock className="w-5 h-5 text-orange-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{stats.total_pending}</p>
                    <p className="text-sm text-white/50">Pending Tasks</p>
                  </div>
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="card bg-gradient-to-br from-blue-500/10 to-cyan-500/5"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-blue-500/20">
                    <Loader2 className="w-5 h-5 text-blue-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{stats.total_in_progress}</p>
                    <p className="text-sm text-white/50">In Progress</p>
                  </div>
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="card bg-gradient-to-br from-green-500/10 to-emerald-500/5"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-green-500/20">
                    <Target className="w-5 h-5 text-green-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{(stats.ai_accuracy_rate * 100).toFixed(1)}%</p>
                    <p className="text-sm text-white/50">AI Accuracy</p>
                  </div>
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="card bg-gradient-to-br from-purple-500/10 to-pink-500/5"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-purple-500/20">
                    <Timer className="w-5 h-5 text-purple-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{stats.avg_review_time_seconds}s</p>
                    <p className="text-sm text-white/50">Avg Review Time</p>
                  </div>
                </div>
              </motion.div>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Task List */}
            <div className="lg:col-span-1 space-y-4">
              {/* Filter */}
              <div className="flex gap-2">
                {(['pending', 'in_progress', 'all'] as const).map((f) => (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      filter === f
                        ? 'bg-nexus-500/20 text-nexus-400 border border-nexus-500/50'
                        : 'bg-white/5 text-white/60 border border-white/10 hover:border-white/20'
                    }`}
                  >
                    {f === 'all' ? 'All' : f === 'pending' ? 'Pending' : 'In Progress'}
                  </button>
                ))}
              </div>

              {/* Task Cards */}
              <div className="space-y-3 max-h-[calc(100vh-400px)] overflow-y-auto">
                {isLoading ? (
                  <div className="card flex items-center justify-center py-12">
                    <Loader2 className="w-8 h-8 animate-spin text-white/30" />
                  </div>
                ) : tasks.length === 0 ? (
                  <div className="card text-center py-12">
                    <CheckCircle2 className="w-12 h-12 mx-auto mb-4 text-green-400/50" />
                    <p className="text-white/50">No tasks in queue</p>
                    <p className="text-sm text-white/30 mt-1">All caught up! 🎉</p>
                  </div>
                ) : (
                  tasks.map((task) => (
                    <motion.div
                      key={task.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      onClick={() => handleSelectTask(task)}
                      className={`card cursor-pointer transition-all hover:border-nexus-500/50 ${
                        selectedTask?.id === task.id ? 'border-nexus-500 bg-nexus-500/10' : ''
                      }`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getPriorityColor(task.priority)}`}>
                          {task.priority}
                        </span>
                        <span className="text-xs text-white/40">
                          {new Date(task.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <h3 className="font-medium text-sm mb-2 line-clamp-2">{task.ticket_title}</h3>
                      <div className="flex items-center gap-2 text-xs text-white/50">
                        <Brain className="w-3 h-3" />
                        <span>{(task.ai_confidence * 100).toFixed(0)}% confidence</span>
                      </div>
                      <div className="mt-2 text-xs text-orange-400/80 line-clamp-1">
                        {task.routing_reason}
                      </div>
                    </motion.div>
                  ))
                )}
              </div>
            </div>

            {/* Task Detail & Review */}
            <div className="lg:col-span-2">
              <AnimatePresence mode="wait">
                {selectedTask ? (
                  <motion.div
                    key={selectedTask.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    className="space-y-6"
                  >
                    {/* Ticket Details */}
                    <div className="card">
                      <div className="flex items-start justify-between mb-4">
                        <h2 className="text-lg font-semibold">Ticket Details</h2>
                        <button 
                          onClick={() => setSelectedTask(null)}
                          className="p-1 text-white/40 hover:text-white"
                        >
                          <X className="w-5 h-5" />
                        </button>
                      </div>
                      <h3 className="font-medium mb-2">{selectedTask.ticket_title}</h3>
                      <p className="text-sm text-white/60 leading-relaxed">
                        {selectedTask.ticket_description}
                      </p>
                    </div>

                    {/* AI Classification */}
                    <div className="card border-orange-500/30 bg-orange-500/5">
                      <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <Brain className="w-5 h-5 text-orange-400" />
                        AI Classification
                        <span className="ml-auto text-sm font-normal text-orange-400">
                          {(selectedTask.ai_confidence * 100).toFixed(1)}% confidence
                        </span>
                      </h3>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="px-3 py-1.5 rounded-lg bg-purple-500/20 text-purple-400">
                          {selectedTask.ai_level1}
                        </span>
                        <ArrowRight className="w-4 h-4 text-white/30" />
                        <span className="px-3 py-1.5 rounded-lg bg-blue-500/20 text-blue-400">
                          {selectedTask.ai_level2}
                        </span>
                        <ArrowRight className="w-4 h-4 text-white/30" />
                        <span className="px-3 py-1.5 rounded-lg bg-nexus-500/20 text-nexus-400">
                          {selectedTask.ai_level3}
                        </span>
                      </div>
                      <p className="mt-3 text-sm text-orange-400/80">
                        <AlertCircle className="w-4 h-4 inline mr-1" />
                        {selectedTask.routing_reason}
                      </p>
                    </div>

                    {/* Review Actions */}
                    <div className="card">
                      <h3 className="text-lg font-semibold mb-4">Your Review</h3>
                      
                      {/* Quick Actions */}
                      <div className="grid grid-cols-2 gap-4 mb-6">
                        <button
                          onClick={handleConfirmCorrect}
                          disabled={isSubmitting}
                          className="p-4 rounded-xl bg-green-500/10 border border-green-500/30 hover:bg-green-500/20 transition-all flex items-center gap-3 disabled:opacity-50"
                        >
                          <ThumbsUp className="w-6 h-6 text-green-400" />
                          <div className="text-left">
                            <p className="font-semibold text-green-400">AI is Correct</p>
                            <p className="text-xs text-white/50">Confirm classification</p>
                          </div>
                        </button>
                        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center gap-3">
                          <ThumbsDown className="w-6 h-6 text-red-400" />
                          <div className="text-left">
                            <p className="font-semibold text-red-400">Needs Correction</p>
                            <p className="text-xs text-white/50">Update below</p>
                          </div>
                        </div>
                      </div>

                      {/* Correction Form */}
                      <div className="space-y-4">
                        <div className="grid grid-cols-3 gap-4">
                          <div>
                            <label className="block text-sm font-medium text-white/70 mb-2">
                              Level 1
                            </label>
                            <select
                              value={correction.level1}
                              onChange={(e) => setCorrection({
                                ...correction,
                                level1: e.target.value,
                                level2: '',
                                level3: '',
                              })}
                              className="input"
                            >
                              <option value="">Select...</option>
                              {hierarchy && Object.keys(hierarchy).map((l1) => (
                                <option key={l1} value={l1}>{l1}</option>
                              ))}
                            </select>
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-white/70 mb-2">
                              Level 2
                            </label>
                            <select
                              value={correction.level2}
                              onChange={(e) => setCorrection({
                                ...correction,
                                level2: e.target.value,
                                level3: '',
                              })}
                              className="input"
                              disabled={!correction.level1}
                            >
                              <option value="">Select...</option>
                              {getLevel2Options(correction.level1).map((l2) => (
                                <option key={l2} value={l2}>{l2}</option>
                              ))}
                            </select>
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-white/70 mb-2">
                              Level 3
                            </label>
                            <select
                              value={correction.level3}
                              onChange={(e) => setCorrection({
                                ...correction,
                                level3: e.target.value,
                              })}
                              className="input"
                              disabled={!correction.level2}
                            >
                              <option value="">Select...</option>
                              {getLevel3Options(correction.level1, correction.level2).map((l3: string) => (
                                <option key={l3} value={l3}>{l3}</option>
                              ))}
                            </select>
                          </div>
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-white/70 mb-2">
                            Notes (optional)
                          </label>
                          <textarea
                            value={correction.notes}
                            onChange={(e) => setCorrection({
                              ...correction,
                              notes: e.target.value,
                            })}
                            placeholder="Add notes about this correction..."
                            rows={3}
                            className="input resize-none"
                          />
                        </div>

                        <button
                          onClick={handleSubmitCorrection}
                          disabled={isSubmitting || !correction.level1 || !correction.level2 || !correction.level3}
                          className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50"
                        >
                          {isSubmitting ? (
                            <>
                              <Loader2 className="w-4 h-4 animate-spin" />
                              Submitting...
                            </>
                          ) : (
                            <>
                              <CheckCircle2 className="w-4 h-4" />
                              Submit Correction
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  </motion.div>
                ) : (
                  <motion.div
                    key="empty"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="card flex flex-col items-center justify-center py-16"
                  >
                    <div className="w-20 h-20 rounded-2xl bg-white/5 flex items-center justify-center mb-6">
                      <MessageSquare className="w-10 h-10 text-white/20" />
                    </div>
                    <h3 className="text-lg font-semibold mb-2">Select a Task</h3>
                    <p className="text-white/50 text-center max-w-md">
                      Choose a task from the queue to review the AI classification and submit your feedback.
                      Your corrections help improve the system!
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

