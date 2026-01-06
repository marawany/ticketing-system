'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  Activity, 
  BarChart3, 
  Brain, 
  CheckCircle2, 
  Clock, 
  Database, 
  GitBranch, 
  Layers, 
  MessageSquare,
  Network,
  Settings,
  Sparkles,
  Target,
  TrendingUp,
  Users,
  Zap,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react'
import Link from 'next/link'
import { Sidebar } from '@/components/layout/Sidebar'
import { DashboardStats } from '@/components/dashboard/DashboardStats'
import { ClassificationFlow } from '@/components/dashboard/ClassificationFlow'
import { RecentTickets } from '@/components/dashboard/RecentTickets'
import { ConfidenceChart } from '@/components/dashboard/ConfidenceChart'
import { CategoryDistribution } from '@/components/dashboard/CategoryDistribution'
import { analyticsApi, healthApi } from '@/lib/api'

export default function Dashboard() {
  const [systemHealth, setSystemHealth] = useState<any>(null)
  const [currentTime, setCurrentTime] = useState<string>('')
  const [currentDate, setCurrentDate] = useState<string>('')

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const health = await healthApi.ready()
        setSystemHealth(health)
      } catch (e) {
        console.error('Failed to fetch health')
      }
    }
    fetchHealth()
    const interval = setInterval(fetchHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const updateTime = () => {
      const now = new Date()
      setCurrentTime(now.toLocaleTimeString('en-US', { hour12: false }))
      setCurrentDate(now.toLocaleDateString('en-US', { 
        weekday: 'short', 
        month: 'short', 
        day: 'numeric',
        year: 'numeric'
      }))
    }
    updateTime()
    const interval = setInterval(updateTime, 1000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex h-screen overflow-hidden bg-terminal-bg">
      <Sidebar />
      
      <main className="flex-1 overflow-y-auto">
        {/* Terminal Header Bar */}
        <header className="sticky top-0 z-10 bg-terminal-surface border-b border-terminal-border px-6 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div>
                <h1 className="text-sm font-bold text-data-cyan uppercase tracking-wider">
                  System Dashboard
                </h1>
                <p className="text-xxs text-white/40 mt-0.5">
                  Real-time classification monitoring
                </p>
              </div>
              
              {/* System Status Indicators */}
              <div className="flex items-center gap-4">
                {systemHealth?.checks && Object.entries(systemHealth.checks).map(([service, status]) => (
                  <div key={service} className="flex items-center gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full ${
                      status ? 'bg-data-green' : 'bg-data-red'
                    }`} />
                    <span className="text-xxs uppercase tracking-wider text-white/40">
                      {service}
                    </span>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="flex items-center gap-6">
              <div className="text-right">
                <p className="text-sm font-mono text-white">{currentTime}</p>
                <p className="text-xxs text-white/40">{currentDate}</p>
              </div>
              
              <div className="flex items-center gap-2 px-3 py-1.5 bg-data-green/10 border border-data-green/30 rounded-terminal">
                <span className="w-1.5 h-1.5 rounded-full bg-data-green animate-pulse" />
                <span className="text-xxs font-medium text-data-green uppercase tracking-wider">Live</span>
              </div>
            </div>
          </div>
        </header>
        
        {/* Content Grid - Bloomberg style dense layout */}
        <div className="p-4 grid-bg min-h-[calc(100vh-60px)]">
          {/* Stats Grid */}
          <DashboardStats />
          
          {/* Main Panels Grid */}
          <div className="grid grid-cols-12 gap-3 mt-4">
            {/* Classification Pipeline - Large Panel */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="col-span-8 panel"
            >
              <div className="panel-header">
                <div className="flex items-center gap-2">
                  <Network className="w-4 h-4 text-data-cyan" />
                  <span className="panel-title">Classification Pipeline</span>
                </div>
                <Link href="/graph" className="text-xxs text-white/40 hover:text-data-cyan transition-colors">
                  FULL VIEW →
                </Link>
              </div>
              <div className="panel-body">
                <ClassificationFlow />
              </div>
            </motion.div>
            
            {/* Confidence Distribution */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="col-span-4 panel"
            >
              <div className="panel-header">
                <div className="flex items-center gap-2">
                  <Target className="w-4 h-4 text-data-green" />
                  <span className="panel-title">Confidence Dist.</span>
                </div>
              </div>
              <div className="panel-body">
                <ConfidenceChart />
              </div>
            </motion.div>
            
            {/* Recent Tickets */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="col-span-7 panel"
            >
              <div className="panel-header">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-data-blue" />
                  <span className="panel-title">Recent Classifications</span>
                </div>
                <Link href="/tickets" className="text-xxs text-white/40 hover:text-data-cyan transition-colors">
                  VIEW ALL →
                </Link>
              </div>
              <div className="panel-body">
                <RecentTickets />
              </div>
            </motion.div>
            
            {/* Category Distribution */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="col-span-5 panel"
            >
              <div className="panel-header">
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-data-amber" />
                  <span className="panel-title">Category Dist.</span>
                </div>
              </div>
              <div className="panel-body">
                <CategoryDistribution />
              </div>
            </motion.div>
          </div>
          
          {/* Quick Actions - Bottom Row */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="grid grid-cols-4 gap-3 mt-4"
          >
            <Link href="/classify" className="group">
              <div className="panel hover:border-data-cyan/50 transition-colors">
                <div className="panel-body py-4">
                  <div className="flex items-center gap-4">
                    <div className="p-3 rounded-terminal bg-data-cyan/10 border border-data-cyan/30 group-hover:bg-data-cyan/20 transition-colors">
                      <Zap className="w-5 h-5 text-data-cyan" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-white group-hover:text-data-cyan transition-colors">
                        Classify Ticket
                      </h3>
                      <p className="text-xxs text-white/40 mt-0.5">Single classification</p>
                    </div>
                  </div>
                </div>
              </div>
            </Link>
            
            <Link href="/batch" className="group">
              <div className="panel hover:border-data-blue/50 transition-colors">
                <div className="panel-body py-4">
                  <div className="flex items-center gap-4">
                    <div className="p-3 rounded-terminal bg-data-blue/10 border border-data-blue/30 group-hover:bg-data-blue/20 transition-colors">
                      <Layers className="w-5 h-5 text-data-blue" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-white group-hover:text-data-blue transition-colors">
                        Batch Process
                      </h3>
                      <p className="text-xxs text-white/40 mt-0.5">Multiple tickets</p>
                    </div>
                  </div>
                </div>
              </div>
            </Link>
            
            <Link href="/hitl" className="group">
              <div className="panel hover:border-data-amber/50 transition-colors">
                <div className="panel-body py-4">
                  <div className="flex items-center gap-4">
                    <div className="p-3 rounded-terminal bg-data-amber/10 border border-data-amber/30 group-hover:bg-data-amber/20 transition-colors">
                      <Users className="w-5 h-5 text-data-amber" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-white group-hover:text-data-amber transition-colors">
                        Review Queue
                      </h3>
                      <p className="text-xxs text-white/40 mt-0.5">HITL tasks</p>
                    </div>
                  </div>
                </div>
              </div>
            </Link>
            
            <Link href="/analytics" className="group">
              <div className="panel hover:border-data-green/50 transition-colors">
                <div className="panel-body py-4">
                  <div className="flex items-center gap-4">
                    <div className="p-3 rounded-terminal bg-data-green/10 border border-data-green/30 group-hover:bg-data-green/20 transition-colors">
                      <BarChart3 className="w-5 h-5 text-data-green" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-white group-hover:text-data-green transition-colors">
                        Analytics
                      </h3>
                      <p className="text-xxs text-white/40 mt-0.5">Reports & insights</p>
                    </div>
                  </div>
                </div>
              </div>
            </Link>
          </motion.div>
        </div>
      </main>
    </div>
  )
}
