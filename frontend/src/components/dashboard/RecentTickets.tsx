'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { CheckCircle, Clock, AlertCircle, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import { ticketsApi, type Ticket } from '@/lib/api'

const statusConfig = {
  'classified': {
    icon: CheckCircle,
    text: 'Classified',
    className: 'text-green-400 bg-green-500/20',
  },
  'open': {
    icon: AlertCircle,
    text: 'Open',
    className: 'text-orange-400 bg-orange-500/20',
  },
  'pending': {
    icon: Clock,
    text: 'Pending',
    className: 'text-blue-400 bg-blue-500/20',
  },
  'resolved': {
    icon: CheckCircle,
    text: 'Resolved',
    className: 'text-purple-400 bg-purple-500/20',
  },
}

function ConfidenceBar({ confidence }: { confidence: number }) {
  const color = confidence >= 0.8 ? 'bg-green-500' : confidence >= 0.6 ? 'bg-orange-500' : 'bg-red-500'
  
  return (
    <div className="w-20">
      <div className="flex items-center justify-between text-xs mb-1">
        <span className={clsx(
          confidence >= 0.8 ? 'text-green-400' : confidence >= 0.6 ? 'text-orange-400' : 'text-red-400'
        )}>
          {(confidence * 100).toFixed(0)}%
        </span>
      </div>
      <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${confidence * 100}%` }} />
      </div>
    </div>
  )
}

function timeAgo(date: string) {
  const now = new Date()
  const then = new Date(date)
  const diffMs = now.getTime() - then.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  
  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins} min ago`
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)} hours ago`
  return `${Math.floor(diffMins / 1440)} days ago`
}

export function RecentTickets() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const fetchTickets = async () => {
      try {
        const res = await ticketsApi.list({ page: 1 })
        setTickets(res.tickets.slice(0, 5))
      } catch (e) {
        console.error('Failed to fetch tickets')
      } finally {
        setIsLoading(false)
      }
    }
    fetchTickets()
    const interval = setInterval(fetchTickets, 15000)
    return () => clearInterval(interval)
  }, [])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-white/30" />
      </div>
    )
  }

  if (tickets.length === 0) {
    return (
      <div className="text-center py-8 text-white/50">
        <p>No recent tickets</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {tickets.map((ticket, index) => {
        const statusKey = (ticket.status || 'open') as keyof typeof statusConfig
        const status = statusConfig[statusKey] || statusConfig.open
        const category = ticket.level1_category 
          ? `${ticket.level1_category} > ${ticket.level2_category} > ${ticket.level3_category}`
          : 'Pending classification'
        
        return (
          <motion.div
            key={ticket.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
            className="p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors cursor-pointer group"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-white/40">
                    {ticket.id.substring(0, 8)}
                  </span>
                  <span className="text-xs text-white/30">•</span>
                  <span className="text-xs text-white/40">{timeAgo(ticket.created_at)}</span>
                </div>
                <p className="font-medium mt-1 truncate group-hover:text-nexus-400 transition-colors">
                  {ticket.title}
                </p>
                <p className="text-xs text-white/40 mt-1 truncate">{category}</p>
              </div>
              
              <div className="flex items-center gap-4">
                {ticket.classification_confidence && (
                  <ConfidenceBar confidence={ticket.classification_confidence} />
                )}
                
                <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs ${status.className}`}>
                  <status.icon className="w-3 h-3" />
                  <span>{status.text}</span>
                </div>
              </div>
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}
