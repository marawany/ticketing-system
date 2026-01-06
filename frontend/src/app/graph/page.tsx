'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Activity,
  ArrowRight,
  Brain,
  CheckCircle2,
  ChevronDown,
  Database,
  Filter,
  GitBranch,
  Info,
  Layers,
  Loader2,
  Network,
  RefreshCw,
  Search,
  Sparkles,
  Target,
  TrendingUp,
  Zap,
  ZoomIn,
  ZoomOut
} from 'lucide-react'
import { Sidebar } from '@/components/layout/Sidebar'
import { analyticsApi, type GraphVisualization } from '@/lib/api'
import dynamic from 'next/dynamic'

// Dynamic import for force graph (client-side only)
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false })

interface GraphNode {
  id: string
  label: string
  level: number
  type: string
  ticket_count?: number
  accuracy?: number
  val?: number
  color?: string
}

interface GraphLink {
  source: string
  target: string
  type: string
}

export default function GraphPage() {
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[], links: GraphLink[] } | null>(null)
  const [stats, setStats] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [filterLevel, setFilterLevel] = useState<number | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [isLive, setIsLive] = useState(true)
  const [recentUpdates, setRecentUpdates] = useState<any[]>([])
  const graphRef = useRef<any>(null)

  const fetchGraph = useCallback(async () => {
    try {
      const res = await analyticsApi.getGraphVisualization()
      
      // Transform nodes with visual properties
      const nodes = res.nodes.map((node) => ({
        ...node,
        val: node.level === 1 ? 20 : node.level === 2 ? 12 : 8 + (node.ticket_count || 0) / 10,
        color: getNodeColor(node.level, node.accuracy || 1),
      }))

      // Transform edges to links
      const links = res.edges.map((edge) => ({
        source: edge.source,
        target: edge.target,
        type: edge.type,
      }))

      setGraphData({ nodes, links })
      setStats(res.statistics)
    } catch (e) {
      console.error('Failed to fetch graph')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchGraph()
    
    if (isLive) {
      const interval = setInterval(() => {
        fetchGraph()
        // Simulate update notification
        if (Math.random() > 0.7) {
          const updateTypes = [
            { type: 'classification', message: 'New ticket classified', icon: Sparkles },
            { type: 'correction', message: 'HITL correction applied', icon: CheckCircle2 },
            { type: 'learning', message: 'Graph weights updated', icon: TrendingUp },
          ]
          const update = updateTypes[Math.floor(Math.random() * updateTypes.length)]
          setRecentUpdates(prev => [{
            ...update,
            id: Date.now(),
            timestamp: new Date().toLocaleTimeString(),
          }, ...prev.slice(0, 4)])
        }
      }, 8000)
      return () => clearInterval(interval)
    }
  }, [fetchGraph, isLive])

  const getNodeColor = (level: number, accuracy: number) => {
    const alpha = 0.5 + (accuracy * 0.5)
    switch (level) {
      case 1: return `rgba(168, 85, 247, ${alpha})` // Purple
      case 2: return `rgba(59, 130, 246, ${alpha})` // Blue
      case 3: return `rgba(0, 186, 199, ${alpha})` // Nexus cyan
      default: return `rgba(156, 163, 175, ${alpha})` // Gray
    }
  }

  const filteredNodes = graphData?.nodes.filter(node => {
    if (filterLevel !== null && node.level !== filterLevel) return false
    if (searchQuery && !node.label.toLowerCase().includes(searchQuery.toLowerCase())) return false
    return true
  }) || []

  const filteredLinks = graphData?.links.filter(link => {
    const sourceExists = filteredNodes.some(n => n.id === link.source || (link.source as any).id === n.id)
    const targetExists = filteredNodes.some(n => n.id === link.target || (link.target as any).id === n.id)
    return sourceExists && targetExists
  }) || []

  const handleNodeClick = (node: any) => {
    setSelectedNode(node)
    if (graphRef.current) {
      graphRef.current.centerAt(node.x, node.y, 500)
      graphRef.current.zoom(2.5, 500)
    }
  }

  const handleZoomIn = () => {
    if (graphRef.current) {
      graphRef.current.zoom(graphRef.current.zoom() * 1.5, 300)
    }
  }

  const handleZoomOut = () => {
    if (graphRef.current) {
      graphRef.current.zoom(graphRef.current.zoom() / 1.5, 300)
    }
  }

  const handleResetView = () => {
    if (graphRef.current) {
      graphRef.current.zoomToFit(400)
    }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      
      <main className="flex-1 overflow-hidden bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
        {/* Header */}
        <header className="sticky top-0 z-10 glass border-b border-white/10 px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-gradient-to-br from-purple-500 to-nexus-500 shadow-lg">
                <Network className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">Classification Graph</h1>
                <p className="text-white/50 text-sm">Real-time Neo4j knowledge graph visualization</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              {/* Live Toggle */}
              <button
                onClick={() => setIsLive(!isLive)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                  isLive 
                    ? 'bg-green-500/20 text-green-400 border border-green-500/50' 
                    : 'bg-white/5 text-white/60 border border-white/10'
                }`}
              >
                {isLive ? (
                  <>
                    <span className="pulse-dot" />
                    Live Updates
                  </>
                ) : (
                  <>
                    <Activity className="w-4 h-4" />
                    Paused
                  </>
                )}
              </button>

              <button 
                onClick={() => fetchGraph()}
                className="btn-secondary flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh
              </button>
            </div>
          </div>
        </header>

        <div className="flex h-[calc(100vh-80px)]">
          {/* Left Panel - Controls & Stats */}
          <div className="w-80 border-r border-white/10 p-6 overflow-y-auto">
            {/* Stats */}
            {stats && (
              <div className="space-y-4 mb-6">
                <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider">
                  Graph Statistics
                </h3>
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/20">
                    <p className="text-2xl font-bold text-purple-400">{stats.level1_categories}</p>
                    <p className="text-xs text-white/50">Level 1</p>
                  </div>
                  <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                    <p className="text-2xl font-bold text-blue-400">{stats.level2_categories}</p>
                    <p className="text-xs text-white/50">Level 2</p>
                  </div>
                  <div className="p-3 rounded-lg bg-nexus-500/10 border border-nexus-500/20">
                    <p className="text-2xl font-bold text-nexus-400">{stats.level3_categories}</p>
                    <p className="text-xs text-white/50">Level 3</p>
                  </div>
                  <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20">
                    <p className="text-2xl font-bold text-green-400">{stats.total_tickets?.toLocaleString() || '0'}</p>
                    <p className="text-xs text-white/50">Tickets</p>
                  </div>
                </div>
              </div>
            )}

            {/* Search */}
            <div className="mb-6">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search categories..."
                  className="input pl-10"
                />
              </div>
            </div>

            {/* Filter */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-3">
                Filter by Level
              </h3>
              <div className="flex gap-2">
                {[null, 1, 2, 3].map((level) => (
                  <button
                    key={level ?? 'all'}
                    onClick={() => setFilterLevel(level)}
                    className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                      filterLevel === level
                        ? 'bg-nexus-500/20 text-nexus-400 border border-nexus-500/50'
                        : 'bg-white/5 text-white/60 border border-white/10 hover:border-white/20'
                    }`}
                  >
                    {level === null ? 'All' : `L${level}`}
                  </button>
                ))}
              </div>
            </div>

            {/* Zoom Controls */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-3">
                View Controls
              </h3>
              <div className="flex gap-2">
                <button onClick={handleZoomIn} className="btn-secondary flex-1 flex items-center justify-center gap-2">
                  <ZoomIn className="w-4 h-4" />
                </button>
                <button onClick={handleZoomOut} className="btn-secondary flex-1 flex items-center justify-center gap-2">
                  <ZoomOut className="w-4 h-4" />
                </button>
                <button onClick={handleResetView} className="btn-secondary flex-1 flex items-center justify-center gap-2">
                  <Target className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Legend */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-3">
                Legend
              </h3>
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <span className="w-4 h-4 rounded-full bg-purple-500" />
                  <span className="text-sm text-white/70">Level 1 Categories</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="w-4 h-4 rounded-full bg-blue-500" />
                  <span className="text-sm text-white/70">Level 2 Subcategories</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="w-4 h-4 rounded-full bg-nexus-500" />
                  <span className="text-sm text-white/70">Level 3 Issues</span>
                </div>
                <div className="flex items-center gap-3 mt-3 pt-3 border-t border-white/10">
                  <Info className="w-4 h-4 text-white/40" />
                  <span className="text-xs text-white/40">Node size = ticket count</span>
                </div>
                <div className="flex items-center gap-3">
                  <Info className="w-4 h-4 text-white/40" />
                  <span className="text-xs text-white/40">Opacity = accuracy score</span>
                </div>
              </div>
            </div>

            {/* Recent Updates */}
            <div>
              <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-3">
                Recent Updates
              </h3>
              <AnimatePresence mode="popLayout">
                {recentUpdates.length > 0 ? (
                  <div className="space-y-2">
                    {recentUpdates.map((update) => (
                      <motion.div
                        key={update.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 20 }}
                        className="flex items-center gap-3 p-2 rounded-lg bg-white/5"
                      >
                        <update.icon className="w-4 h-4 text-nexus-400" />
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-white/70 truncate">{update.message}</p>
                          <p className="text-xs text-white/40">{update.timestamp}</p>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-white/40">No recent updates</p>
                )}
              </AnimatePresence>
            </div>
          </div>

          {/* Graph Visualization */}
          <div className="flex-1 relative">
            {isLoading ? (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center">
                  <Loader2 className="w-12 h-12 animate-spin text-nexus-400 mx-auto mb-4" />
                  <p className="text-white/50">Loading graph...</p>
                </div>
              </div>
            ) : graphData ? (
              <ForceGraph2D
                ref={graphRef}
                graphData={{ nodes: filteredNodes, links: filteredLinks }}
                nodeLabel={(node: any) => `${node.label}\n${node.ticket_count || 0} tickets`}
                nodeColor={(node: any) => node.color}
                nodeVal={(node: any) => node.val}
                nodeCanvasObject={(node: any, ctx, globalScale) => {
                  const label = node.label
                  const fontSize = Math.max(8, 12 / globalScale)
                  ctx.font = `${fontSize}px Sans-Serif`
                  
                  // Draw node
                  ctx.beginPath()
                  ctx.arc(node.x, node.y, node.val, 0, 2 * Math.PI)
                  ctx.fillStyle = node.color
                  ctx.fill()
                  
                  // Draw label for larger nodes
                  if (globalScale > 0.5 || node.level === 1) {
                    ctx.textAlign = 'center'
                    ctx.textBaseline = 'top'
                    ctx.fillStyle = 'rgba(255, 255, 255, 0.8)'
                    ctx.fillText(label, node.x, node.y + node.val + 2)
                  }
                }}
                linkColor={() => 'rgba(255, 255, 255, 0.1)'}
                linkWidth={1}
                onNodeClick={handleNodeClick}
                backgroundColor="transparent"
                width={typeof window !== 'undefined' ? window.innerWidth - 320 - 256 : 800}
                height={typeof window !== 'undefined' ? window.innerHeight - 80 : 600}
              />
            ) : null}

            {/* Selected Node Details */}
            <AnimatePresence>
              {selectedNode && (
                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  className="absolute top-4 right-4 w-80 card"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className={`px-2 py-1 rounded text-xs font-medium ${
                      selectedNode.level === 1 ? 'bg-purple-500/20 text-purple-400' :
                      selectedNode.level === 2 ? 'bg-blue-500/20 text-blue-400' :
                      'bg-nexus-500/20 text-nexus-400'
                    }`}>
                      Level {selectedNode.level}
                    </div>
                    <button 
                      onClick={() => setSelectedNode(null)}
                      className="text-white/40 hover:text-white"
                    >
                      ×
                    </button>
                  </div>
                  <h3 className="text-lg font-semibold mb-4">{selectedNode.label}</h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-white/60">Tickets</span>
                      <span className="font-mono">{selectedNode.ticket_count || 0}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-white/60">Accuracy</span>
                      <span className={`font-mono ${
                        (selectedNode.accuracy || 1) >= 0.9 ? 'text-green-400' :
                        (selectedNode.accuracy || 1) >= 0.7 ? 'text-orange-400' : 'text-red-400'
                      }`}>
                        {((selectedNode.accuracy || 1) * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-white/60">Node Type</span>
                      <span className="font-mono">{selectedNode.type}</span>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </main>
    </div>
  )
}

