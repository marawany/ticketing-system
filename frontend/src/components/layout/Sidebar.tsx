'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { motion } from 'framer-motion'
import {
  Activity,
  BarChart3,
  GitBranch,
  Home,
  Layers,
  LogOut,
  MessageSquare,
  Network,
  Settings,
  Sparkles,
  Users,
  Zap,
} from 'lucide-react'
import clsx from 'clsx'
import { hitlApi, analyticsApi } from '@/lib/api'

const navigation = [
  { name: 'Dashboard', href: '/', icon: Home, shortcut: '1' },
  { name: 'Classify', href: '/classify', icon: Zap, shortcut: '2' },
  { name: 'Tickets', href: '/tickets', icon: MessageSquare, shortcut: '3' },
  { name: 'Batch', href: '/batch', icon: Layers, shortcut: '4' },
  { name: 'HITL Queue', href: '/hitl', icon: Users, shortcut: '5' },
  { name: 'Graph', href: '/graph', icon: Network, shortcut: '6' },
  { name: 'Analytics', href: '/analytics', icon: BarChart3, shortcut: '7' },
]

const secondaryNav = [
  { name: 'Settings', href: '/settings', icon: Settings, shortcut: '0' },
]

export function Sidebar() {
  const pathname = usePathname()
  const [hitlCount, setHitlCount] = useState<number>(0)
  const [systemStatus, setSystemStatus] = useState<'online' | 'offline'>('online')
  const [currentTime, setCurrentTime] = useState<string>('')

  // Fetch HITL queue count
  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await hitlApi.getTasks({ status: 'pending' })
        setHitlCount(res.total)
        setSystemStatus('online')
      } catch (e) {
        setSystemStatus('offline')
      }
    }
    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

  // Update time
  useEffect(() => {
    const updateTime = () => {
      setCurrentTime(new Date().toLocaleTimeString('en-US', { 
        hour12: false, 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit'
      }))
    }
    updateTime()
    const interval = setInterval(updateTime, 1000)
    return () => clearInterval(interval)
  }, [])

  return (
    <aside className="w-56 h-screen flex flex-col bg-terminal-panel border-r border-terminal-border">
      {/* Logo / Brand */}
      <div className="p-4 border-b border-terminal-border">
        <Link href="/" className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-terminal bg-gradient-to-br from-data-cyan to-data-blue flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-data-cyan tracking-tight">
              NEXUSFLOW
            </h1>
            <p className="text-xxs text-white/30 uppercase tracking-widest">Turing AI</p>
          </div>
        </Link>
      </div>

      {/* System Status Bar */}
      <div className="px-4 py-2 bg-terminal-surface border-b border-terminal-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={`w-1.5 h-1.5 rounded-full ${
              systemStatus === 'online' ? 'bg-data-green animate-pulse' : 'bg-data-red'
            }`} />
            <span className="text-xxs uppercase tracking-wider text-white/40">
              {systemStatus}
            </span>
          </div>
          <span className="text-xxs font-mono text-white/40">{currentTime}</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-2 space-y-0.5 overflow-y-auto">
        <div className="px-2 py-2 text-xxs font-semibold text-white/30 uppercase tracking-widest">
          Navigation
        </div>
        {navigation.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.name}
              href={item.href}
              className={clsx(
                'flex items-center justify-between px-3 py-2 rounded-terminal transition-all duration-150 group',
                isActive
                  ? 'bg-data-cyan/10 text-data-cyan border-l-2 border-data-cyan -ml-0.5 pl-[10px]'
                  : 'text-white/50 hover:text-white hover:bg-white/5'
              )}
            >
              <div className="flex items-center gap-3">
                <item.icon className={clsx(
                  'w-4 h-4',
                  isActive ? 'text-data-cyan' : 'text-white/40 group-hover:text-white/60'
                )} />
                <span className="text-sm font-medium">{item.name}</span>
              </div>
              <div className="flex items-center gap-2">
                {item.name === 'HITL Queue' && hitlCount > 0 && (
                  <span className="px-1.5 py-0.5 text-xxs font-mono bg-data-amber/20 text-data-amber rounded-sm">
                    {hitlCount}
                  </span>
                )}
                <span className="text-xxs font-mono text-white/20 group-hover:text-white/40">
                  {item.shortcut}
                </span>
              </div>
            </Link>
          )
        })}

        <div className="px-2 py-2 mt-4 text-xxs font-semibold text-white/30 uppercase tracking-widest">
          System
        </div>
        {secondaryNav.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.name}
              href={item.href}
              className={clsx(
                'flex items-center justify-between px-3 py-2 rounded-terminal transition-all duration-150 group',
                isActive
                  ? 'bg-data-cyan/10 text-data-cyan border-l-2 border-data-cyan -ml-0.5 pl-[10px]'
                  : 'text-white/50 hover:text-white hover:bg-white/5'
              )}
            >
              <div className="flex items-center gap-3">
                <item.icon className="w-4 h-4 text-white/40 group-hover:text-white/60" />
                <span className="text-sm font-medium">{item.name}</span>
              </div>
              <span className="text-xxs font-mono text-white/20 group-hover:text-white/40">
                {item.shortcut}
              </span>
            </Link>
          )
        })}
        
        {/* External Links */}
        <a
          href="http://localhost:6006"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-between px-3 py-2 rounded-terminal transition-all duration-150 group text-white/50 hover:text-white hover:bg-white/5"
        >
          <div className="flex items-center gap-3">
            <Activity className="w-4 h-4 text-data-amber/60 group-hover:text-data-amber" />
            <span className="text-sm font-medium">Phoenix</span>
          </div>
          <span className="text-xxs text-white/20">↗</span>
        </a>
      </nav>

      {/* User Section */}
      <div className="p-3 border-t border-terminal-border bg-terminal-surface">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-terminal bg-gradient-to-br from-data-cyan/20 to-data-blue/20 border border-data-cyan/30 flex items-center justify-center">
            <span className="text-xs font-bold text-data-cyan">MY</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium truncate">Marawan Youssef</p>
            <p className="text-xxs text-white/40 truncate">marawan.y@turing.com</p>
          </div>
          <button className="p-1.5 text-white/30 hover:text-white/60 transition-colors rounded-terminal hover:bg-white/5">
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Version */}
      <div className="px-4 py-2 border-t border-terminal-border">
        <p className="text-xxs font-mono text-white/20 text-center">
          NEXUSFLOW v0.1.0
        </p>
      </div>
    </aside>
  )
}
