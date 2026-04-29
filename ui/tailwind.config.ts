import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Tokens from `Descriptif DESIGN.docx` (light + dark)
        surface: {
          light: '#FFFFFF',
          dark: '#0B1220',
          deep: '#1B2A5A',
        },
        ink: {
          light: '#0F172A',
          dark: '#F8FAFC',
          muted: '#64748B',
        },
        accent: {
          DEFAULT: '#2F5EFF',
          hover: '#1F4AE0',
          subtle: '#E0E8FF',
        },
        warn: '#F59E0B',
        success: '#10B981',
        danger: '#EF4444',
      },
      maxWidth: {
        page: '1600px',
      },
      transitionTimingFunction: {
        smooth: 'cubic-bezier(0.22, 1, 0.36, 1)',
      },
      transitionDuration: {
        '400': '400ms',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

export default config
