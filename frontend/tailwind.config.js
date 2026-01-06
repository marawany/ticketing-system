/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Bloomberg Terminal inspired palette
        terminal: {
          bg: '#0a0a0a',        // Deep black background
          panel: '#121212',     // Panel background
          surface: '#1a1a1a',   // Elevated surface
          border: '#2a2a2a',    // Border color
          muted: '#3a3a3a',     // Muted elements
        },
        // Data colors (Bloomberg style)
        data: {
          green: '#00d26a',     // Positive/up
          red: '#ff3b3b',       // Negative/down
          amber: '#ffaa00',     // Warning/neutral
          blue: '#0088ff',      // Info/link
          cyan: '#00bac7',      // Primary accent
        },
        // Turing NexusFlow brand colors
        nexus: {
          50: '#ecfeff',
          100: '#cffafe',
          200: '#a5f3fc',
          300: '#67e8f9',
          400: '#00bac7',
          500: '#00a3b0',
          600: '#0891b2',
          700: '#0e7490',
          800: '#155e75',
          900: '#164e63',
          950: '#083344',
        },
        // Semantic colors for confidence levels
        confidence: {
          high: '#00d26a',
          medium: '#ffaa00',
          low: '#ff3b3b',
        },
      },
      fontFamily: {
        sans: ['Inter', 'SF Pro Display', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'SF Mono', 'Fira Code', 'monospace'],
        display: ['SF Pro Display', 'Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'xxs': '0.65rem',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
        'nexus-gradient': 'linear-gradient(135deg, #00bac7 0%, #0088ff 50%, #6366f1 100%)',
        'terminal-gradient': 'linear-gradient(180deg, #0a0a0a 0%, #121212 100%)',
        'grid-pattern': 'linear-gradient(rgba(42, 42, 42, 0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(42, 42, 42, 0.3) 1px, transparent 1px)',
      },
      backgroundSize: {
        'grid': '20px 20px',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'shimmer': 'shimmer 2s linear infinite',
        'ticker': 'ticker 20s linear infinite',
        'blink': 'blink 1s step-end infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideDown: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        ticker: {
          '0%': { transform: 'translateX(0)' },
          '100%': { transform: 'translateX(-50%)' },
        },
        blink: {
          '50%': { opacity: '0' },
        },
      },
      boxShadow: {
        'nexus': '0 4px 14px 0 rgba(0, 186, 199, 0.25)',
        'nexus-lg': '0 10px 40px -10px rgba(0, 186, 199, 0.35)',
        'terminal': '0 0 0 1px rgba(42, 42, 42, 0.8), 0 4px 16px rgba(0, 0, 0, 0.4)',
        'terminal-inset': 'inset 0 1px 0 rgba(255, 255, 255, 0.03), inset 0 -1px 0 rgba(0, 0, 0, 0.3)',
        'glow-green': '0 0 20px rgba(0, 210, 106, 0.3)',
        'glow-cyan': '0 0 20px rgba(0, 186, 199, 0.3)',
      },
      borderRadius: {
        'terminal': '2px',
      },
    },
  },
  plugins: [],
}
