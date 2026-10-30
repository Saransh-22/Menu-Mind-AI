/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        forest: {
          DEFAULT: '#183B32',
          dark: '#0f2620',
          secondary: '#24483E',
          light: '#2d574b',
          muted: '#183B3215',
        },
        cream: {
          DEFAULT: '#F7F5EF',
          card: '#FFFFFF',
          border: '#E8E5DD',
          darker: '#EFECE2',
        },
        terracotta: {
          DEFAULT: '#D97757',
          dark: '#b95d3e',
          light: '#fdf2ee',
          border: '#f6d5ca',
        },
        amber: {
          DEFAULT: '#D6A64F',
          dark: '#b38534',
          light: '#fdf8ee',
        },
        brandText: {
          primary: '#303A35',
          secondary: '#7A817B',
          muted: '#A5ABA6',
        },
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        display: ['Manrope', 'Plus Jakarta Sans', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 3px rgba(24, 59, 50, 0.05), 0 1px 2px rgba(24, 59, 50, 0.03)',
        cardHover: '0 4px 14px rgba(24, 59, 50, 0.08)',
        modal: '0 12px 36px rgba(24, 59, 50, 0.16)',
      },
      borderRadius: {
        card: '14px',
      },
    },
  },
  plugins: [],
}
