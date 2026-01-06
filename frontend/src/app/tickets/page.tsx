'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Filter,
  Loader2,
  MessageSquare,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  Target,
  Trash2,
  X
} from 'lucide-react'
import { Sidebar } from '@/components/layout/Sidebar'
import { ticketsApi, classificationApi, type Ticket } from '@/lib/api'

const priorityColors: Record<string, string> = {
  low: 'bg-gray-500/20 text-gray-400',
  medium: 'bg-blue-500/20 text-blue-400',
  high: 'bg-orange-500/20 text-orange-400',
  critical: 'bg-red-500/20 text-red-400',
}

const statusColors: Record<string, string> = {
  open: 'bg-yellow-500/20 text-yellow-400',
  pending: 'bg-blue-500/20 text-blue-400',
  classified: 'bg-green-500/20 text-green-400',
  resolved: 'bg-purple-500/20 text-purple-400',
}

export default function TicketsPage() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [totalTickets, setTotalTickets] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [priorityFilter, setPriorityFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [page, setPage] = useState(1)
  const [isClassifying, setIsClassifying] = useState(false)
  
  // Form state
  const [newTicket, setNewTicket] = useState({
    title: '',
    description: '',
    priority: 'medium',
  })

  const fetchTickets = async () => {
    setIsLoading(true)
    try {
      const res = await ticketsApi.list({
        page,
        priority: priorityFilter !== 'all' ? priorityFilter : undefined,
        status: statusFilter !== 'all' ? statusFilter : undefined,
      })
      setTickets(res.tickets)
      setTotalTickets(res.total)
    } catch (e) {
      console.error('Failed to fetch tickets')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchTickets()
  }, [page, priorityFilter, statusFilter])

  const handleCreateTicket = async () => {
    if (!newTicket.title || !newTicket.description) return
    
    try {
      const created = await ticketsApi.create(newTicket)
      setShowCreateModal(false)
      setNewTicket({ title: '', description: '', priority: 'medium' })
      fetchTickets()
      
      // Optionally auto-classify
      setSelectedTicket(created)
    } catch (e) {
      console.error('Failed to create ticket')
    }
  }

  const handleClassifyTicket = async (ticket: Ticket) => {
    setIsClassifying(true)
    try {
      const result = await classificationApi.classify({
        title: ticket.title,
        description: ticket.description,
        priority: ticket.priority,
      })
      
      // Refresh tickets to show updated classification
      fetchTickets()
      
      // Update selected ticket view
      if (selectedTicket?.id === ticket.id) {
        setSelectedTicket({
          ...ticket,
          level1_category: result.classification.level1,
          level2_category: result.classification.level2,
          level3_category: result.classification.level3,
          classification_confidence: result.confidence.calibrated_score,
          status: 'classified',
        })
      }
    } catch (e) {
      console.error('Classification failed')
    } finally {
      setIsClassifying(false)
    }
  }

  const handleDeleteTicket = async (ticketId: string) => {
    try {
      await ticketsApi.list() // Simulated delete - you'd call delete endpoint
      setSelectedTicket(null)
      fetchTickets()
    } catch (e) {
      console.error('Failed to delete ticket')
    }
  }

  const filteredTickets = tickets.filter(t => 
    t.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      
      <main className="flex-1 overflow-y-auto bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
        {/* Header */}
        <header className="sticky top-0 z-10 glass border-b border-white/10 px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 shadow-lg">
                <MessageSquare className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">Tickets</h1>
                <p className="text-white/50 text-sm">Manage and classify support tickets</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <button 
                onClick={() => fetchTickets()}
                className="btn-secondary flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh
              </button>
              <button 
                onClick={() => setShowCreateModal(true)}
                className="btn-primary flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                New Ticket
              </button>
            </div>
          </div>
        </header>

        <div className="p-8">
          {/* Filters */}
          <div className="flex items-center gap-4 mb-6">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search tickets..."
                className="input pl-10"
              />
            </div>
            
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="input w-40"
            >
              <option value="all">All Priorities</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
            
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="input w-40"
            >
              <option value="all">All Status</option>
              <option value="open">Open</option>
              <option value="pending">Pending</option>
              <option value="classified">Classified</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Ticket List */}
            <div className="lg:col-span-2 space-y-4">
              {isLoading ? (
                <div className="card flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 animate-spin text-white/30" />
                </div>
              ) : filteredTickets.length === 0 ? (
                <div className="card text-center py-12">
                  <MessageSquare className="w-12 h-12 mx-auto mb-4 text-white/20" />
                  <p className="text-white/50">No tickets found</p>
                  <button 
                    onClick={() => setShowCreateModal(true)}
                    className="mt-4 text-nexus-400 hover:text-nexus-300"
                  >
                    Create your first ticket →
                  </button>
                </div>
              ) : (
                <>
                  {filteredTickets.map((ticket) => (
                    <motion.div
                      key={ticket.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      onClick={() => setSelectedTicket(ticket)}
                      className={`card cursor-pointer transition-all hover:border-nexus-500/50 ${
                        selectedTicket?.id === ticket.id ? 'border-nexus-500 bg-nexus-500/10' : ''
                      }`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${priorityColors[ticket.priority] || priorityColors.medium}`}>
                            {ticket.priority}
                          </span>
                          <span className={`px-2 py-1 rounded text-xs font-medium ${statusColors[ticket.status] || statusColors.open}`}>
                            {ticket.status}
                          </span>
                        </div>
                        <span className="text-xs text-white/40">
                          {new Date(ticket.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      
                      <h3 className="font-medium mb-2">{ticket.title}</h3>
                      <p className="text-sm text-white/60 line-clamp-2">{ticket.description}</p>
                      
                      {ticket.level1_category && (
                        <div className="mt-3 flex items-center gap-2 text-xs">
                          <Target className="w-3 h-3 text-green-400" />
                          <span className="text-white/60">
                            {ticket.level1_category} → {ticket.level2_category} → {ticket.level3_category}
                          </span>
                          {ticket.classification_confidence && (
                            <span className="ml-auto text-green-400">
                              {(ticket.classification_confidence * 100).toFixed(0)}%
                            </span>
                          )}
                        </div>
                      )}
                    </motion.div>
                  ))}
                  
                  {/* Pagination */}
                  <div className="flex items-center justify-between mt-6">
                    <span className="text-sm text-white/50">
                      Showing {filteredTickets.length} of {totalTickets} tickets
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                        disabled={page === 1}
                        className="btn-secondary p-2 disabled:opacity-50"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </button>
                      <span className="px-4 py-2 text-sm">Page {page}</span>
                      <button
                        onClick={() => setPage(p => p + 1)}
                        disabled={filteredTickets.length < 20}
                        className="btn-secondary p-2 disabled:opacity-50"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Ticket Detail */}
            <div className="lg:col-span-1">
              <AnimatePresence mode="wait">
                {selectedTicket ? (
                  <motion.div
                    key={selectedTicket.id}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    className="card sticky top-24"
                  >
                    <div className="flex items-start justify-between mb-4">
                      <h2 className="text-lg font-semibold">Ticket Details</h2>
                      <button 
                        onClick={() => setSelectedTicket(null)}
                        className="p-1 text-white/40 hover:text-white"
                      >
                        <X className="w-5 h-5" />
                      </button>
                    </div>
                    
                    <div className="space-y-4">
                      <div>
                        <span className="text-xs text-white/50 uppercase">Title</span>
                        <p className="font-medium">{selectedTicket.title}</p>
                      </div>
                      
                      <div>
                        <span className="text-xs text-white/50 uppercase">Description</span>
                        <p className="text-sm text-white/70">{selectedTicket.description}</p>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <span className="text-xs text-white/50 uppercase">Priority</span>
                          <p className={`text-sm font-medium ${priorityColors[selectedTicket.priority]?.split(' ')[1] || ''}`}>
                            {selectedTicket.priority}
                          </p>
                        </div>
                        <div>
                          <span className="text-xs text-white/50 uppercase">Status</span>
                          <p className="text-sm">{selectedTicket.status}</p>
                        </div>
                      </div>
                      
                      {selectedTicket.level1_category ? (
                        <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20">
                          <div className="flex items-center gap-2 mb-3">
                            <CheckCircle2 className="w-4 h-4 text-green-400" />
                            <span className="text-sm font-medium text-green-400">Classified</span>
                          </div>
                          <div className="space-y-1 text-sm">
                            <div className="flex items-center gap-2">
                              <span className="px-2 py-1 rounded bg-purple-500/20 text-purple-400">
                                {selectedTicket.level1_category}
                              </span>
                            </div>
                            <div className="flex items-center gap-2 pl-4">
                              <ArrowRight className="w-3 h-3 text-white/30" />
                              <span className="px-2 py-1 rounded bg-blue-500/20 text-blue-400">
                                {selectedTicket.level2_category}
                              </span>
                            </div>
                            <div className="flex items-center gap-2 pl-8">
                              <ArrowRight className="w-3 h-3 text-white/30" />
                              <span className="px-2 py-1 rounded bg-nexus-500/20 text-nexus-400">
                                {selectedTicket.level3_category}
                              </span>
                            </div>
                          </div>
                          {selectedTicket.classification_confidence && (
                            <div className="mt-3 flex items-center justify-between text-sm">
                              <span className="text-white/50">Confidence</span>
                              <span className="font-mono text-green-400">
                                {(selectedTicket.classification_confidence * 100).toFixed(1)}%
                              </span>
                            </div>
                          )}
                        </div>
                      ) : (
                        <button
                          onClick={() => handleClassifyTicket(selectedTicket)}
                          disabled={isClassifying}
                          className="btn-primary w-full flex items-center justify-center gap-2"
                        >
                          {isClassifying ? (
                            <>
                              <Loader2 className="w-4 h-4 animate-spin" />
                              Classifying...
                            </>
                          ) : (
                            <>
                              <Sparkles className="w-4 h-4" />
                              Classify Ticket
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  </motion.div>
                ) : (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="card flex flex-col items-center justify-center py-12"
                  >
                    <MessageSquare className="w-12 h-12 text-white/20 mb-4" />
                    <p className="text-white/50 text-center">
                      Select a ticket to view details
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>

        {/* Create Ticket Modal */}
        <AnimatePresence>
          {showCreateModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
              onClick={() => setShowCreateModal(false)}
            >
              <motion.div
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.95, opacity: 0 }}
                onClick={(e) => e.stopPropagation()}
                className="w-full max-w-lg card"
              >
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold">Create New Ticket</h2>
                  <button 
                    onClick={() => setShowCreateModal(false)}
                    className="p-1 text-white/40 hover:text-white"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-2">Title</label>
                    <input
                      type="text"
                      value={newTicket.title}
                      onChange={(e) => setNewTicket({ ...newTicket, title: e.target.value })}
                      placeholder="Brief description of the issue..."
                      className="input"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-2">Description</label>
                    <textarea
                      value={newTicket.description}
                      onChange={(e) => setNewTicket({ ...newTicket, description: e.target.value })}
                      placeholder="Detailed explanation of the problem..."
                      rows={4}
                      className="input resize-none"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-2">Priority</label>
                    <div className="grid grid-cols-4 gap-2">
                      {['low', 'medium', 'high', 'critical'].map((p) => (
                        <button
                          key={p}
                          type="button"
                          onClick={() => setNewTicket({ ...newTicket, priority: p })}
                          className={`px-3 py-2 rounded-lg text-sm capitalize transition-all ${
                            newTicket.priority === p
                              ? 'bg-nexus-500/20 border-nexus-500 border'
                              : 'bg-white/5 border border-white/10 hover:border-white/20'
                          }`}
                        >
                          {p}
                        </button>
                      ))}
                    </div>
                  </div>
                  
                  <div className="flex gap-3 pt-4">
                    <button
                      onClick={() => setShowCreateModal(false)}
                      className="btn-secondary flex-1"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleCreateTicket}
                      disabled={!newTicket.title || !newTicket.description}
                      className="btn-primary flex-1 disabled:opacity-50"
                    >
                      Create Ticket
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

