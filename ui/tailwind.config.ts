import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Tokens from `Descriptif DESIGN.docx` (light + dark)
        // Apple-like neutrals: off-white canvas, white sheets, near-black ink.
        canvas: '#F4F5F7',
        // Flux: colour only ever means cooling (cold) or heating (warm).
        cold: '#2F7DF6',
        warm: '#FF7A3D',
        surface: {
          light: '#FFFFFF',
          dark: '#0B1220',
          deep: '#1B2A5A',
        },
        ink: {
          light: '#14161A',
          dark: '#F8FAFC',
          muted: '#6A6F78',
        },
        accent: {
          DEFAULT: '#2F7DF6',
          hover: '#1F6BE0',
          subtle: '#E6EFFE',
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
        sans: ['"Instrument Sans Variable"', '"Helvetica Neue"', 'Helvetica', 'Arial', 'sans-serif'],
        display: ['"Archivo Variable"', '"Helvetica Neue"', 'Helvetica', 'Arial', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

export default config
