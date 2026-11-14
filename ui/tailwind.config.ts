import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Tokens from `Descriptif DESIGN.docx` (light + dark)
        // Apple-like neutrals: off-white canvas, white sheets, near-black ink.
        canvas: '#F5F5F7',
        surface: {
          light: '#FFFFFF',
          dark: '#0B1220',
          deep: '#1B2A5A',
        },
        ink: {
          light: '#1D1D1F',
          dark: '#F8FAFC',
          muted: '#6E6E73',
        },
        accent: {
          DEFAULT: '#0071E3',
          hover: '#0077ED',
          subtle: '#E8F1FC',
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
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"SF Pro Display"',
          '"SF Pro Text"',
          '"Helvetica Neue"',
          'Helvetica',
          'Arial',
          'sans-serif',
        ],
      },
    },
  },
  plugins: [],
}

export default config
