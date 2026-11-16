import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
        surface: {
          base: '#060913',
          subtle: '#0a0f1d',
          elevated: '#0f172a',
          highlight: '#152038',
        },
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'glow-sm': '0 0 20px -5px rgba(59, 130, 246, 0.28)',
        'glow-md': '0 0 32px -5px rgba(59, 130, 246, 0.35)',
        'glow-emerald': '0 0 30px -5px rgba(16, 185, 129, 0.28)',
        'glow-amber': '0 0 32px -5px rgba(245, 158, 11, 0.32)',
        'exec': '0 1px 0 0 rgba(255, 255, 255, 0.07) inset, 0 20px 45px -20px rgba(0, 0, 0, 0.7)',
      },
    },
  },
  plugins: [],
};

export default config;
