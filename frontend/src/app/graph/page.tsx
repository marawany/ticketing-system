'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import dynamic from 'next/dynamic'
import {
  Plus,
  Edit2,
  Trash2,
  Upload,
  Sparkles,
  RefreshCw,
  Search,
  ChevronRight,
  ChevronDown,
  Network,
  Brain,
  Zap,
  AlertCircle,
  Check,
  X,
  FileUp,
  Loader2,
} from 'lucide-react'
import { Sidebar } from '@/components/layout/Sidebar'
import { graphApi, type GraphNode, type GraphEdge } from '@/lib/api'

// Dynamically import ForceGraph to avoid SSR issues
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false })

interface Category {
  name: string
  level: number
  description?: string
  keywords?: string[]
  ticket_count: number
  accuracy: number
  children_count: number
  parent?: string
}

interface HierarchyItem {
  name: string
  ticket_count: number
  accuracy?: number
  children?: HierarchyItem[]
}

export default function GraphManagementPage() {
  const [categories, setCategories] = useState<Category[]>([])
  const [hierarchy, setHierarchy] = useState<HierarchyItem[]>([])
  const [graphData, setGraphData] = useState<{ nodes: any[]; links: any[] }>({ nodes: [], links: [] })
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'tree' | 'graph' | 'ai'>('tree')
  const [selectedCategory, setSelectedCategory] = useState<Category | null>(null)
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set())
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createLevel, setCreateLevel] = useState<1 | 2 | 3>(1)
  const [aiSuggestions, setAiSuggestions] = useState<any[]>([])
  const [aiLoading, setAiLoading] = useState(false)
  const [aiReasoning, setAiReasoning] = useState('')
  const [uploadResult, setUploadResult] = useState<any>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Fetch data
  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [statsRes, hierarchyRes, vizRes] = await Promise.all([
        graphApi.getStats(),
        graphApi.getHierarchy(),
        graphApi.getVisualization(),
      ])
      
      setStats(statsRes)
      setHierarchy(hierarchyRes.hierarchy || [])
      
      // Transform for force graph
      const nodes = vizRes.nodes.map((n: any) => ({
        id: n.id,
        name: n.name,
        level: n.level,
        val: Math.max(5, Math.log(n.ticket_count + 1) * 3),
        color: n.level === 1 ? '#6366f1' : n.level === 2 ? '#0088ff' : '#00bac7',
      }))
      
      const links = vizRes.edges.map((e: any) => ({
        source: e.source,
        target: e.target,
        value: e.weight,
      }))
      
      setGraphData({ nodes, links })
    } catch (e) {
      console.error('Failed to fetch graph data:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Toggle node expansion
  const toggleExpand = (name: string) => {
    setExpandedNodes(prev => {
      const next = new Set(prev)
      if (next.has(name)) {
        next.delete(name)
      } else {
        next.add(name)
      }
      return next
    })
  }

  // AI Expand category
  const handleAiExpand = async (categoryName: string, level: number) => {
    setAiLoading(true)
    setAiSuggestions([])
    setAiReasoning('')
    
    try {
      const result = await graphApi.aiExpand({
        category_name: categoryName,
        level,
        num_suggestions: 5,
      })
      
      setAiSuggestions(result.suggestions || [])
      setAiReasoning(result.reasoning || '')
    } catch (e) {
      console.error('AI expansion failed:', e)
    } finally {
      setAiLoading(false)
    }
  }

  // Apply AI suggestion
  const handleApplySuggestion = async (categoryName: string, level: number, suggestion: any) => {
    try {
      await graphApi.applyExpansion(categoryName, level, [suggestion])
      // Refresh data
      fetchData()
      setAiSuggestions(prev => prev.filter(s => s.name !== suggestion.name))
    } catch (e) {
      console.error('Failed to apply suggestion:', e)
    }
  }

  // Handle file upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    
    setAiLoading(true)
    setUploadResult(null)
    
    try {
      const result = await graphApi.analyzeDataset(file)
      setUploadResult(result)
    } catch (e) {
      console.error('Dataset analysis failed:', e)
    } finally {
      setAiLoading(false)
    }
  }

  // Render tree item
  const renderTreeItem = (item: HierarchyItem, level: number, parentPath: string = '') => {
    const path = parentPath ? `${parentPath} > ${item.name}` : item.name
    const isExpanded = expandedNodes.has(path)
    const hasChildren = item.children && item.children.length > 0
    const matchesSearch = !searchQuery || item.name.toLowerCase().includes(searchQuery.toLowerCase())
    
    if (!matchesSearch && !hasChildren) return null
    
    return (
      <div key={path} className="select-none">
        <div
          className={`flex items-center gap-2 py-1.5 px-2 rounded-terminal cursor-pointer transition-colors ${
            selectedCategory?.name === item.name
              ? 'bg-data-cyan/10 text-data-cyan'
              : 'hover:bg-white/5'
          }`}
          style={{ paddingLeft: `${level * 16 + 8}px` }}
          onClick={() => {
            setSelectedCategory({
              name: item.name,
              level: level + 1,
              ticket_count: item.ticket_count,
              accuracy: item.accuracy || 1,
              children_count: item.children?.length || 0,
            })
            if (hasChildren) toggleExpand(path)
          }}
        >
          {hasChildren ? (
            isExpanded ? (
              <ChevronDown className="w-3 h-3 text-white/40" />
            ) : (
              <ChevronRight className="w-3 h-3 text-white/40" />
            )
          ) : (
            <span className="w-3" />
          )}
          
          <span className={`w-2 h-2 rounded-full ${
            level === 0 ? 'bg-indigo-500' : level === 1 ? 'bg-data-blue' : 'bg-data-cyan'
          }`} />
          
          <span className="flex-1 text-sm truncate">{item.name}</span>
          
          <span className="text-xxs font-mono text-white/30">
            {item.ticket_count || 0}
          </span>
        </div>
        
        <AnimatePresence>
          {isExpanded && hasChildren && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              {item.children!.map(child => renderTreeItem(child, level + 1, path))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden bg-terminal-bg">
      <Sidebar />
      
      <main className="flex-1 overflow-hidden flex flex-col">
        {/* Header */}
        <header className="bg-terminal-surface border-b border-terminal-border px-6 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Network className="w-5 h-5 text-data-cyan" />
              <div>
                <h1 className="text-sm font-bold text-data-cyan uppercase tracking-wider">
                  Graph Management
                </h1>
                <p className="text-xxs text-white/40">
                  Manage classification taxonomy with AI-powered evolution
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              {/* Stats */}
              {stats && (
                <div className="flex items-center gap-4 mr-4">
                  <div className="text-center">
                    <p className="text-lg font-mono font-bold text-data-cyan">{stats.level1_count}</p>
                    <p className="text-xxs text-white/40">L1</p>
                  </div>
                  <div className="text-center">
                    <p className="text-lg font-mono font-bold text-data-blue">{stats.level2_count}</p>
                    <p className="text-xxs text-white/40">L2</p>
                  </div>
                  <div className="text-center">
                    <p className="text-lg font-mono font-bold text-indigo-400">{stats.level3_count}</p>
                    <p className="text-xxs text-white/40">L3</p>
                  </div>
                </div>
              )}
              
              <button
                onClick={() => setShowCreateModal(true)}
                className="btn-primary flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Add Category
              </button>
              
              <button
                onClick={fetchData}
                className="btn-secondary flex items-center gap-2"
                disabled={loading}
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        </header>
        
        {/* Tab Navigation */}
        <div className="bg-terminal-panel border-b border-terminal-border px-6">
          <div className="flex gap-1">
            {[
              { id: 'tree', label: 'Tree View', icon: Network },
              { id: 'graph', label: 'Force Graph', icon: Zap },
              { id: 'ai', label: 'AI Evolution', icon: Brain },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'text-data-cyan border-b-2 border-data-cyan'
                    : 'text-white/50 hover:text-white/80'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </div>
        
        {/* Content */}
        <div className="flex-1 overflow-hidden flex">
          {/* Main Panel */}
          <div className="flex-1 overflow-auto p-4">
            {activeTab === 'tree' && (
              <div className="grid grid-cols-12 gap-4 h-full">
                {/* Tree */}
                <div className="col-span-7 panel h-full flex flex-col">
                  <div className="panel-header">
                    <span className="panel-title">Category Hierarchy</span>
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                      <input
                        type="text"
                        placeholder="Search..."
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                        className="input pl-9 py-1 text-xs w-48"
                      />
                    </div>
                  </div>
                  <div className="panel-body overflow-auto">
                    {hierarchy.map(item => renderTreeItem(item, 0))}
                  </div>
                </div>
                
                {/* Details Panel */}
                <div className="col-span-5 flex flex-col gap-4">
                  {/* Selected Category */}
                  <div className="panel">
                    <div className="panel-header">
                      <span className="panel-title">Category Details</span>
                    </div>
                    <div className="panel-body">
                      {selectedCategory ? (
                        <div className="space-y-4">
                          <div>
                            <p className="text-xxs text-white/40 uppercase tracking-wider mb-1">Name</p>
                            <p className="text-lg font-semibold text-white">{selectedCategory.name}</p>
                          </div>
                          
                          <div className="grid grid-cols-3 gap-3">
                            <div>
                              <p className="text-xxs text-white/40 uppercase">Level</p>
                              <p className="text-xl font-mono font-bold text-data-cyan">
                                L{selectedCategory.level}
                              </p>
                            </div>
                            <div>
                              <p className="text-xxs text-white/40 uppercase">Tickets</p>
                              <p className="text-xl font-mono font-bold text-data-blue">
                                {selectedCategory.ticket_count}
                              </p>
                            </div>
                            <div>
                              <p className="text-xxs text-white/40 uppercase">Accuracy</p>
                              <p className={`text-xl font-mono font-bold ${
                                selectedCategory.accuracy >= 0.8 ? 'text-data-green' :
                                selectedCategory.accuracy >= 0.6 ? 'text-data-amber' : 'text-data-red'
                              }`}>
                                {(selectedCategory.accuracy * 100).toFixed(0)}%
                              </p>
                            </div>
                          </div>
                          
                          <div className="flex gap-2 pt-2 border-t border-terminal-border">
                            <button className="btn-secondary flex-1 flex items-center justify-center gap-2">
                              <Edit2 className="w-4 h-4" />
                              Edit
                            </button>
                            {selectedCategory.level < 3 && (
                              <button
                                onClick={() => handleAiExpand(selectedCategory.name, selectedCategory.level)}
                                className="btn-primary flex-1 flex items-center justify-center gap-2"
                                disabled={aiLoading}
                              >
                                <Sparkles className="w-4 h-4" />
                                AI Expand
                              </button>
                            )}
                          </div>
                        </div>
                      ) : (
                        <p className="text-white/40 text-sm text-center py-8">
                          Select a category to view details
                        </p>
                      )}
                    </div>
                  </div>
                  
                  {/* AI Suggestions */}
                  {(aiSuggestions.length > 0 || aiLoading) && (
                    <div className="panel flex-1">
                      <div className="panel-header">
                        <span className="panel-title flex items-center gap-2">
                          <Sparkles className="w-4 h-4 text-data-amber" />
                          AI Suggestions
                        </span>
                      </div>
                      <div className="panel-body overflow-auto">
                        {aiLoading ? (
                          <div className="flex items-center justify-center py-8">
                            <Loader2 className="w-6 h-6 text-data-cyan animate-spin" />
                          </div>
                        ) : (
                          <div className="space-y-3">
                            {aiReasoning && (
                              <p className="text-xs text-white/60 italic mb-3">{aiReasoning}</p>
                            )}
                            {aiSuggestions.map((suggestion, i) => (
                              <div key={i} className="bg-terminal-surface p-3 rounded-terminal">
                                <div className="flex items-start justify-between">
                                  <div className="flex-1">
                                    <p className="font-medium text-white">{suggestion.name}</p>
                                    <p className="text-xs text-white/50 mt-1">{suggestion.description}</p>
                                  </div>
                                  <button
                                    onClick={() => handleApplySuggestion(
                                      selectedCategory!.name,
                                      selectedCategory!.level,
                                      suggestion
                                    )}
                                    className="p-1.5 bg-data-green/20 text-data-green rounded-terminal hover:bg-data-green/30 transition-colors"
                                  >
                                    <Check className="w-4 h-4" />
                                  </button>
                                </div>
                                {suggestion.keywords && (
                                  <div className="flex gap-1 mt-2 flex-wrap">
                                    {suggestion.keywords.slice(0, 4).map((kw: string) => (
                                      <span key={kw} className="text-xxs px-1.5 py-0.5 bg-terminal-bg rounded text-white/50">
                                        {kw}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
            
            {activeTab === 'graph' && (
              <div className="panel h-full">
                <div className="panel-header">
                  <span className="panel-title">Interactive Force Graph</span>
                  <span className="text-xxs text-white/40">
                    {graphData.nodes.length} nodes • {graphData.links.length} edges
                  </span>
                </div>
                <div className="panel-body h-[calc(100%-48px)] bg-terminal-bg">
                  {typeof window !== 'undefined' && graphData.nodes.length > 0 && (
                    <ForceGraph2D
                      graphData={graphData}
                      nodeLabel="name"
                      nodeColor={(node: any) => node.color}
                      nodeRelSize={6}
                      linkColor={() => 'rgba(255,255,255,0.1)'}
                      linkWidth={1}
                      backgroundColor="#0a0a0a"
                      onNodeClick={(node: any) => {
                        setSelectedCategory({
                          name: node.name,
                          level: node.level,
                          ticket_count: 0,
                          accuracy: 1,
                          children_count: 0,
                        })
                      }}
                    />
                  )}
                </div>
              </div>
            )}
            
            {activeTab === 'ai' && (
              <div className="grid grid-cols-2 gap-4">
                {/* Dataset Upload */}
                <div className="panel">
                  <div className="panel-header">
                    <span className="panel-title flex items-center gap-2">
                      <FileUp className="w-4 h-4" />
                      Dataset Analysis
                    </span>
                  </div>
                  <div className="panel-body">
                    <div className="border-2 border-dashed border-terminal-border rounded-terminal p-6 text-center">
                      <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileUpload}
                        accept=".json,.csv"
                        className="hidden"
                      />
                      <Upload className="w-10 h-10 text-white/30 mx-auto mb-3" />
                      <p className="text-sm text-white/60 mb-2">
                        Upload a dataset to analyze for graph evolution
                      </p>
                      <button
                        onClick={() => fileInputRef.current?.click()}
                        className="btn-primary"
                        disabled={aiLoading}
                      >
                        {aiLoading ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          'Select File'
                        )}
                      </button>
                      <p className="text-xxs text-white/40 mt-2">
                        Supports JSON and CSV files
                      </p>
                    </div>
                    
                    {uploadResult && (
                      <div className="mt-4 space-y-4">
                        {/* New Categories */}
                        {uploadResult.new_categories_suggested?.length > 0 && (
                          <div>
                            <p className="text-xxs uppercase tracking-wider text-data-green mb-2">
                              New Categories Suggested
                            </p>
                            {uploadResult.new_categories_suggested.map((cat: any, i: number) => (
                              <div key={i} className="bg-terminal-surface p-2 rounded-terminal mb-2">
                                <p className="text-sm font-medium">{cat.name}</p>
                                <p className="text-xs text-white/50">{cat.description}</p>
                              </div>
                            ))}
                          </div>
                        )}
                        
                        {/* Recommendations */}
                        {uploadResult.recommendations?.length > 0 && (
                          <div>
                            <p className="text-xxs uppercase tracking-wider text-data-amber mb-2">
                              Recommendations
                            </p>
                            <ul className="space-y-1">
                              {uploadResult.recommendations.map((rec: string, i: number) => (
                                <li key={i} className="text-xs text-white/70 flex items-start gap-2">
                                  <ChevronRight className="w-3 h-3 mt-0.5 text-data-amber" />
                                  {rec}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
                
                {/* HITL Evolution */}
                <div className="panel">
                  <div className="panel-header">
                    <span className="panel-title flex items-center gap-2">
                      <Brain className="w-4 h-4" />
                      HITL-Driven Evolution
                    </span>
                  </div>
                  <div className="panel-body">
                    <div className="space-y-4">
                      <p className="text-sm text-white/60">
                        The system automatically analyzes human corrections to evolve the graph:
                      </p>
                      
                      <div className="space-y-3">
                        <div className="flex items-start gap-3 p-3 bg-terminal-surface rounded-terminal">
                          <div className="p-2 bg-data-cyan/20 rounded-terminal">
                            <AlertCircle className="w-4 h-4 text-data-cyan" />
                          </div>
                          <div>
                            <p className="text-sm font-medium">Misclassification Analysis</p>
                            <p className="text-xs text-white/50">
                              LLM analyzes why corrections were made
                            </p>
                          </div>
                        </div>
                        
                        <div className="flex items-start gap-3 p-3 bg-terminal-surface rounded-terminal">
                          <div className="p-2 bg-data-green/20 rounded-terminal">
                            <Network className="w-4 h-4 text-data-green" />
                          </div>
                          <div>
                            <p className="text-sm font-medium">Keyword Updates</p>
                            <p className="text-xs text-white/50">
                              Auto-updates category keywords from patterns
                            </p>
                          </div>
                        </div>
                        
                        <div className="flex items-start gap-3 p-3 bg-terminal-surface rounded-terminal">
                          <div className="p-2 bg-data-amber/20 rounded-terminal">
                            <Sparkles className="w-4 h-4 text-data-amber" />
                          </div>
                          <div>
                            <p className="text-sm font-medium">New Category Suggestions</p>
                            <p className="text-xs text-white/50">
                              Suggests new categories when patterns emerge
                            </p>
                          </div>
                        </div>
                      </div>
                      
                      <div className="pt-3 border-t border-terminal-border">
                        <p className="text-xxs text-white/40 uppercase tracking-wider mb-2">
                          Recent Evolution Activity
                        </p>
                        <div className="text-xs text-white/60 space-y-1">
                          <p>• Edge weights updated from 3 corrections</p>
                          <p>• 2 keyword additions applied</p>
                          <p>• 1 category description updated</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
      
      {/* Create Modal */}
      <AnimatePresence>
        {showCreateModal && (
          <CreateCategoryModal
            onClose={() => setShowCreateModal(false)}
            onCreated={() => {
              setShowCreateModal(false)
              fetchData()
            }}
            hierarchy={hierarchy}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

// Create Category Modal Component
function CreateCategoryModal({
  onClose,
  onCreated,
  hierarchy,
}: {
  onClose: () => void
  onCreated: () => void
  hierarchy: HierarchyItem[]
}) {
  const [level, setLevel] = useState<1 | 2 | 3>(1)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [parentL1, setParentL1] = useState('')
  const [parentL2, setParentL2] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleCreate = async () => {
    if (!name.trim()) {
      setError('Name is required')
      return
    }
    
    setLoading(true)
    setError('')
    
    try {
      if (level === 1) {
        await graphApi.createLevel1({ name, description })
      } else if (level === 2) {
        if (!parentL1) {
          setError('Parent Level 1 is required')
          setLoading(false)
          return
        }
        await graphApi.createLevel2({ name, description, parent_level1: parentL1 })
      } else {
        if (!parentL1 || !parentL2) {
          setError('Parent categories are required')
          setLoading(false)
          return
        }
        await graphApi.createLevel3({ name, description, parent_level1: parentL1, parent_level2: parentL2 })
      }
      
      onCreated()
    } catch (e: any) {
      setError(e.message || 'Failed to create category')
    } finally {
      setLoading(false)
    }
  }

  // Get L2 options based on selected L1
  const l2Options = parentL1
    ? hierarchy.find(h => h.name === parentL1)?.children || []
    : []

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="bg-terminal-panel border border-terminal-border rounded-terminal w-full max-w-md"
        onClick={e => e.stopPropagation()}
      >
        <div className="panel-header">
          <span className="panel-title">Create Category</span>
          <button onClick={onClose} className="text-white/40 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
        
        <div className="p-4 space-y-4">
          {/* Level Selection */}
          <div>
            <label className="input-label">Level</label>
            <div className="flex gap-2">
              {[1, 2, 3].map(l => (
                <button
                  key={l}
                  onClick={() => setLevel(l as 1 | 2 | 3)}
                  className={`flex-1 py-2 rounded-terminal transition-colors ${
                    level === l
                      ? 'bg-data-cyan text-white'
                      : 'bg-terminal-surface text-white/60 hover:text-white'
                  }`}
                >
                  Level {l}
                </button>
              ))}
            </div>
          </div>
          
          {/* Parent Selection for L2/L3 */}
          {level >= 2 && (
            <div>
              <label className="input-label">Parent Level 1</label>
              <select
                value={parentL1}
                onChange={e => {
                  setParentL1(e.target.value)
                  setParentL2('')
                }}
                className="input"
              >
                <option value="">Select...</option>
                {hierarchy.map(h => (
                  <option key={h.name} value={h.name}>{h.name}</option>
                ))}
              </select>
            </div>
          )}
          
          {level === 3 && parentL1 && (
            <div>
              <label className="input-label">Parent Level 2</label>
              <select
                value={parentL2}
                onChange={e => setParentL2(e.target.value)}
                className="input"
              >
                <option value="">Select...</option>
                {l2Options.map((h: any) => (
                  <option key={h.name} value={h.name}>{h.name}</option>
                ))}
              </select>
            </div>
          )}
          
          {/* Name */}
          <div>
            <label className="input-label">Name</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              className="input"
              placeholder="Category name"
            />
          </div>
          
          {/* Description */}
          <div>
            <label className="input-label">Description (optional)</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              className="input resize-none"
              rows={2}
              placeholder="Brief description"
            />
          </div>
          
          {/* Error */}
          {error && (
            <p className="text-sm text-data-red">{error}</p>
          )}
          
          {/* Actions */}
          <div className="flex gap-2 pt-2">
            <button onClick={onClose} className="btn-secondary flex-1">
              Cancel
            </button>
            <button
              onClick={handleCreate}
              disabled={loading}
              className="btn-primary flex-1 flex items-center justify-center gap-2"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  Create
                </>
              )}
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}
