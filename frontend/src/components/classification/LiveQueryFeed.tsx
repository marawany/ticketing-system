'use client'

import React, { useEffect, useState, useRef } from 'react'
import { Activity, Database, GitBranch, Brain, Zap, Clock, CheckCircle } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface QueryEvent {
  id: string
  timestamp: string
  type: 'graph_query' | 'vector_search' | 'llm_call' | 'confidence_calc' | 'complete'
  details: {
    query?: string
    collection?: string
    model?: string
    duration_ms?: number
    results_count?: number
    confidence?: number
    classification?: {
      level1: string
      level2: string
      level3: string
    }
  }
  status: 'running' | 'complete' | 'error'
}

interface LiveQueryFeedProps {
  ticketId?: string
  websocketUrl?: string
  className?: string
}

const queryTypeConfig = {
  graph_query: {
    icon: GitBranch,
    color: 'text-cyan-400',
    bg: 'bg-cyan-500/10',
    label: 'GRAPH QUERY',
  },
  vector_search: {
    icon: Database,
    color: 'text-purple-400',
    bg: 'bg-purple-500/10',
    label: 'VECTOR SEARCH',
  },
  llm_call: {
    icon: Brain,
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    label: 'LLM INFERENCE',
  },
  confidence_calc: {
    icon: Zap,
    color: 'text-green-400',
    bg: 'bg-green-500/10',
    label: 'CONFIDENCE CALC',
  },
  complete: {
    icon: CheckCircle,
    color: 'text-green-500',
    bg: 'bg-green-500/20',
    label: 'CLASSIFICATION COMPLETE',
  },
}

export default function LiveQueryFeed({
  ticketId,
  websocketUrl,
  className = '',
}: LiveQueryFeedProps) {
  const [events, setEvents] = useState<QueryEvent[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [totalDuration, setTotalDuration] = useState(0)
  const scrollRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)

  // Demo mode - generate sample events
  useEffect(() => {
    if (!websocketUrl && !ticketId) {
      // Demo mode - show sample events
      const demoEvents: QueryEvent[] = [
        {
          id: '1',
          timestamp: new Date().toISOString(),
          type: 'graph_query',
          details: {
            query: "MATCH (l1:Level1Category)-[:CONTAINS]->(l2) WHERE l2.name CONTAINS 'DNA'",
            results_count: 12,
            duration_ms: 45,
          },
          status: 'complete',
        },
        {
          id: '2',
          timestamp: new Date().toISOString(),
          type: 'vector_search',
          details: {
            collection: 'nexusflow_tickets',
            results_count: 10,
            duration_ms: 128,
          },
          status: 'complete',
        },
        {
          id: '3',
          timestamp: new Date().toISOString(),
          type: 'llm_call',
          details: {
            model: 'gpt-4o',
            duration_ms: 1250,
          },
          status: 'complete',
        },
        {
          id: '4',
          timestamp: new Date().toISOString(),
          type: 'confidence_calc',
          details: {
            confidence: 0.87,
            duration_ms: 5,
          },
          status: 'complete',
        },
        {
          id: '5',
          timestamp: new Date().toISOString(),
          type: 'complete',
          details: {
            classification: {
              level1: 'Defect',
              level2: 'DNA',
              level3: 'CAPS DNA',
            },
            confidence: 0.87,
            duration_ms: 1428,
          },
          status: 'complete',
        },
      ]

      // Animate events appearing
      let idx = 0
      const interval = setInterval(() => {
        if (idx < demoEvents.length) {
          setEvents((prev) => [...prev, demoEvents[idx]])
          setTotalDuration((prev) => prev + (demoEvents[idx].details.duration_ms || 0))
          idx++
        } else {
          clearInterval(interval)
        }
      }, 800)

      return () => clearInterval(interval)
    }
  }, [websocketUrl, ticketId])

  // Real WebSocket connection
  useEffect(() => {
    if (websocketUrl) {
      const ws = new WebSocket(websocketUrl)
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'query_event' || data.type === 'classification_complete') {
            const newEvent: QueryEvent = {
              id: Math.random().toString(36).substring(7),
              timestamp: data.timestamp,
              type: data.query_type || 'complete',
              details: {
                ...data.query_details,
                ...data.results,
                duration_ms: data.duration_ms,
              },
              status: 'complete',
            }
            setEvents((prev) => [...prev, newEvent])
            if (data.duration_ms) {
              setTotalDuration((prev) => prev + data.duration_ms)
            }
          }
        } catch (e) {
          console.error('Failed to parse WS message:', e)
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
      }

      return () => {
        ws.close()
      }
    }
  }, [websocketUrl])

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [events])

  return (
    <div className={`bg-terminal-surface border border-terminal-border rounded-lg ${className}`}>
      <div className="border-b border-terminal-border px-4 py-3">
        <div className="flex items-center justify-between">
          <h3 className="flex items-center gap-2 text-data-cyan text-sm uppercase tracking-wide font-semibold">
            <Activity className="h-4 w-4" />
            Live Query Feed
          </h3>
          <div className="flex items-center gap-3 text-xs">
            <div className="flex items-center gap-1 text-white/40">
              <Clock className="h-3 w-3" />
              {totalDuration}ms
            </div>
            <div className={`flex items-center gap-1 ${isConnected || !websocketUrl ? 'text-data-green' : 'text-data-red'}`}>
              <span className={`w-2 h-2 rounded-full ${isConnected || !websocketUrl ? 'bg-data-green animate-pulse' : 'bg-data-red'}`} />
              {isConnected || !websocketUrl ? 'LIVE' : 'DISCONNECTED'}
            </div>
          </div>
        </div>
      </div>
      <div className="p-0">
        <div
          ref={scrollRef}
          className="max-h-[400px] overflow-y-auto scrollbar-thin scrollbar-thumb-gray-700"
        >
          <AnimatePresence>
            {events.length === 0 ? (
              <div className="p-4 text-center text-gray-500 text-sm">
                Waiting for classification queries...
              </div>
            ) : (
              events.map((event, idx) => {
                const config = queryTypeConfig[event.type]
                const Icon = config.icon

                return (
                  <motion.div
                    key={event.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.3 }}
                    className={`p-3 border-b border-terminal-border ${config.bg} hover:bg-white/5 transition-colors`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`p-1.5 rounded ${config.bg}`}>
                        <Icon className={`h-4 w-4 ${config.color}`} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1">
                          <span className={`text-xs font-bold ${config.color} uppercase tracking-wider`}>
                            {config.label}
                          </span>
                          <span className="text-[10px] text-white/40">
                            {event.details.duration_ms}ms
                          </span>
                        </div>

                        {/* Query details */}
                        {event.details.query && (
                          <div className="text-[10px] font-mono text-data-cyan/70 bg-terminal-bg rounded p-1.5 mb-1 overflow-hidden text-ellipsis whitespace-nowrap">
                            {event.details.query}
                          </div>
                        )}

                        {/* Results */}
                        <div className="flex flex-wrap gap-2 text-[10px]">
                          {event.details.results_count !== undefined && (
                            <span className="text-white/40">
                              Results: <span className="text-data-green">{event.details.results_count}</span>
                            </span>
                          )}
                          {event.details.model && (
                            <span className="text-white/40">
                              Model: <span className="text-data-amber">{event.details.model}</span>
                            </span>
                          )}
                          {event.details.collection && (
                            <span className="text-white/40">
                              Collection: <span className="text-purple-400">{event.details.collection}</span>
                            </span>
                          )}
                          {event.details.confidence !== undefined && event.type !== 'complete' && (
                            <span className="text-white/40">
                              Confidence: <span className="text-data-green">{(event.details.confidence * 100).toFixed(1)}%</span>
                            </span>
                          )}
                        </div>

                        {/* Final classification */}
                        {event.type === 'complete' && event.details.classification && (
                          <div className="mt-2 p-2 bg-data-green/10 rounded border border-data-green/30">
                            <div className="text-[10px] text-white/40 mb-1">Classification Result:</div>
                            <div className="text-xs text-data-green font-mono">
                              {event.details.classification.level1} &gt; {event.details.classification.level2} &gt; {event.details.classification.level3}
                            </div>
                            <div className="text-[10px] text-white/40 mt-1">
                              Confidence: <span className="text-data-green font-bold">{((event.details.confidence || 0) * 100).toFixed(1)}%</span>
                              {' '} | Total Time: <span className="text-data-cyan">{totalDuration}ms</span>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </motion.div>
                )
              })
            )}
          </AnimatePresence>
        </div>

        {/* Summary bar */}
        {events.length > 0 && (
          <div className="p-2 bg-terminal-bg/50 border-t border-terminal-border flex items-center justify-between text-[10px] text-white/40">
            <span>{events.length} queries executed</span>
            <span>Avg: {events.length > 0 ? Math.round(totalDuration / events.length) : 0}ms/query</span>
          </div>
        )}
      </div>
    </div>
  )
}

