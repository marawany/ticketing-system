'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  Activity,
  Bell,
  Check,
  Database,
  GitBranch,
  Key,
  Loader2,
  Save,
  Server,
  Settings,
  Shield,
  User,
  Zap
} from 'lucide-react'
import { Sidebar } from '@/components/layout/Sidebar'
import { healthApi } from '@/lib/api'

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('general')
  const [health, setHealth] = useState<any>(null)
  const [readiness, setReadiness] = useState<any>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  
  // Settings state
  const [settings, setSettings] = useState({
    confidenceThreshold: 0.7,
    hitlThreshold: 0.5,
    batchSize: 50,
    enableNotifications: true,
    enableAutoClassify: true,
    defaultModel: 'gpt-4o',
  })

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const [h, r] = await Promise.all([
          healthApi.check(),
          healthApi.ready(),
        ])
        setHealth(h)
        setReadiness(r)
      } catch (e) {
        console.error('Health check failed')
      }
    }
    checkHealth()
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  const handleSave = async () => {
    setIsSaving(true)
    // Simulate save
    await new Promise(resolve => setTimeout(resolve, 1000))
    setIsSaving(false)
    setSaveSuccess(true)
    setTimeout(() => setSaveSuccess(false), 3000)
  }

  const tabs = [
    { id: 'general', name: 'General', icon: Settings },
    { id: 'classification', name: 'Classification', icon: Zap },
    { id: 'system', name: 'System Status', icon: Server },
    { id: 'profile', name: 'Profile', icon: User },
  ]

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      
      <main className="flex-1 overflow-y-auto bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
        {/* Header */}
        <header className="sticky top-0 z-10 glass border-b border-white/10 px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-gradient-to-br from-gray-500 to-gray-600 shadow-lg">
                <Settings className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">Settings</h1>
                <p className="text-white/50 text-sm">Configure Turing NexusFlow</p>
              </div>
            </div>
            
            <button 
              onClick={handleSave}
              disabled={isSaving}
              className="btn-primary flex items-center gap-2"
            >
              {isSaving ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Saving...
                </>
              ) : saveSuccess ? (
                <>
                  <Check className="w-4 h-4" />
                  Saved!
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  Save Changes
                </>
              )}
            </button>
          </div>
        </header>

        <div className="p-8">
          <div className="max-w-4xl mx-auto">
            {/* Tabs */}
            <div className="flex gap-2 mb-8">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                    activeTab === tab.id
                      ? 'bg-nexus-500/20 text-nexus-400 border border-nexus-500/50'
                      : 'text-white/60 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.name}
                </button>
              ))}
            </div>

            {/* Tab Content */}
            {activeTab === 'general' && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-6"
              >
                <div className="card">
                  <h3 className="text-lg font-semibold mb-6">Application Settings</h3>
                  
                  <div className="space-y-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">Auto Classification</p>
                        <p className="text-sm text-white/50">Automatically classify new tickets</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={settings.enableAutoClassify}
                          onChange={(e) => setSettings({ ...settings, enableAutoClassify: e.target.checked })}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:bg-nexus-500 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
                      </label>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">Notifications</p>
                        <p className="text-sm text-white/50">Get notified about HITL tasks</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={settings.enableNotifications}
                          onChange={(e) => setSettings({ ...settings, enableNotifications: e.target.checked })}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:bg-nexus-500 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
                      </label>
                    </div>
                    
                    <div>
                      <label className="block font-medium mb-2">Default Model</label>
                      <select
                        value={settings.defaultModel}
                        onChange={(e) => setSettings({ ...settings, defaultModel: e.target.value })}
                        className="input w-full max-w-xs"
                      >
                        <option value="gpt-4o">GPT-4o</option>
                        <option value="gpt-4o-mini">GPT-4o Mini</option>
                        <option value="claude-3-opus">Claude 3 Opus</option>
                        <option value="claude-3-sonnet">Claude 3 Sonnet</option>
                      </select>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            {activeTab === 'classification' && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-6"
              >
                <div className="card">
                  <h3 className="text-lg font-semibold mb-6">Classification Settings</h3>
                  
                  <div className="space-y-6">
                    <div>
                      <label className="block font-medium mb-2">
                        Confidence Threshold ({(settings.confidenceThreshold * 100).toFixed(0)}%)
                      </label>
                      <input
                        type="range"
                        min="0.5"
                        max="0.95"
                        step="0.05"
                        value={settings.confidenceThreshold}
                        onChange={(e) => setSettings({ ...settings, confidenceThreshold: parseFloat(e.target.value) })}
                        className="w-full"
                      />
                      <p className="text-sm text-white/50 mt-1">
                        Minimum confidence for auto-resolution
                      </p>
                    </div>
                    
                    <div>
                      <label className="block font-medium mb-2">
                        HITL Threshold ({(settings.hitlThreshold * 100).toFixed(0)}%)
                      </label>
                      <input
                        type="range"
                        min="0.3"
                        max="0.7"
                        step="0.05"
                        value={settings.hitlThreshold}
                        onChange={(e) => setSettings({ ...settings, hitlThreshold: parseFloat(e.target.value) })}
                        className="w-full"
                      />
                      <p className="text-sm text-white/50 mt-1">
                        Route to HITL if confidence below this
                      </p>
                    </div>
                    
                    <div>
                      <label className="block font-medium mb-2">Batch Size</label>
                      <input
                        type="number"
                        value={settings.batchSize}
                        onChange={(e) => setSettings({ ...settings, batchSize: parseInt(e.target.value) })}
                        min={10}
                        max={200}
                        className="input w-32"
                      />
                      <p className="text-sm text-white/50 mt-1">
                        Maximum tickets per batch
                      </p>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            {activeTab === 'system' && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-6"
              >
                <div className="card">
                  <h3 className="text-lg font-semibold mb-6">System Status</h3>
                  
                  {health && (
                    <div className="grid grid-cols-2 gap-4 mb-6">
                      <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20">
                        <div className="flex items-center gap-2 mb-2">
                          <Activity className="w-4 h-4 text-green-400" />
                          <span className="text-green-400 font-medium">System Status</span>
                        </div>
                        <p className="text-2xl font-bold capitalize">{health.status}</p>
                      </div>
                      <div className="p-4 rounded-lg bg-nexus-500/10 border border-nexus-500/20">
                        <div className="flex items-center gap-2 mb-2">
                          <GitBranch className="w-4 h-4 text-nexus-400" />
                          <span className="text-nexus-400 font-medium">Version</span>
                        </div>
                        <p className="text-2xl font-bold">{health.version}</p>
                      </div>
                    </div>
                  )}
                  
                  <h4 className="font-medium mb-4">Service Health</h4>
                  <div className="space-y-3">
                    {readiness && Object.entries(readiness.checks).map(([service, status]) => (
                      <div key={service} className="flex items-center justify-between p-3 rounded-lg bg-white/5">
                        <div className="flex items-center gap-3">
                          <Database className="w-4 h-4 text-white/50" />
                          <span className="capitalize">{service.replace('_', ' ')}</span>
                        </div>
                        <span className={`px-2 py-1 rounded text-xs ${
                          status ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                        }`}>
                          {status ? 'Connected' : 'Disconnected'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
                
                <div className="card">
                  <h3 className="text-lg font-semibold mb-6">External Services</h3>
                  <div className="space-y-3">
                    <a
                      href="http://localhost:6006"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <Activity className="w-4 h-4 text-orange-400" />
                        <span>Arize Phoenix</span>
                      </div>
                      <span className="text-xs text-white/40">localhost:6006 ↗</span>
                    </a>
                    <a
                      href="http://localhost:7474"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <GitBranch className="w-4 h-4 text-purple-400" />
                        <span>Neo4j Browser</span>
                      </div>
                      <span className="text-xs text-white/40">localhost:7474 ↗</span>
                    </a>
                    <a
                      href="http://localhost:8000/docs"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <Server className="w-4 h-4 text-nexus-400" />
                        <span>API Documentation</span>
                      </div>
                      <span className="text-xs text-white/40">localhost:8000/docs ↗</span>
                    </a>
                  </div>
                </div>
              </motion.div>
            )}

            {activeTab === 'profile' && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-6"
              >
                <div className="card">
                  <h3 className="text-lg font-semibold mb-6">Profile Settings</h3>
                  
                  <div className="flex items-center gap-6 mb-8">
                    <div className="w-20 h-20 rounded-full bg-gradient-to-br from-nexus-500 to-purple-500 flex items-center justify-center text-2xl font-bold">
                      MY
                    </div>
                    <div>
                      <h4 className="text-xl font-semibold">Marawan Youssef</h4>
                      <p className="text-white/50">marawan.y@turing.com</p>
                      <span className="inline-block mt-2 px-2 py-1 rounded text-xs bg-nexus-500/20 text-nexus-400">
                        Administrator
                      </span>
                    </div>
                  </div>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block font-medium mb-2">Full Name</label>
                      <input
                        type="text"
                        defaultValue="Marawan Youssef"
                        className="input w-full max-w-md"
                      />
                    </div>
                    <div>
                      <label className="block font-medium mb-2">Email</label>
                      <input
                        type="email"
                        defaultValue="marawan.y@turing.com"
                        className="input w-full max-w-md"
                        disabled
                      />
                    </div>
                  </div>
                </div>
                
                <div className="card">
                  <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                    <Shield className="w-5 h-5 text-orange-400" />
                    Security
                  </h3>
                  
                  <button className="btn-secondary flex items-center gap-2">
                    <Key className="w-4 h-4" />
                    Change Password
                  </button>
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

