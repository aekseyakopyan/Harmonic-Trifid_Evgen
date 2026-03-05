/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: '#0f1117',
        card: '#1a1d27',
        border: '#2a2d3a',
        accent: '#6366f1',
        'accent-hover': '#4f46e5',
        muted: '#6b7280',
        hot: '#ef4444',
        warm: '#f59e0b',
        cold: '#3b82f6',
      },
    },
  },
  plugins: [],
}
