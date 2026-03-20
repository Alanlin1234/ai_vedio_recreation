/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: {
          50: '#FDFCFA',
          100: '#FAF7F2',
          200: '#F3EDE4',
          300: '#E8E2D9',
        },
        moss: {
          50: '#F0F4F2',
          100: '#D4E0DB',
          200: '#A8C1B4',
          300: '#7A9B8E',
          400: '#5D7B6F',
          500: '#4A6358',
          600: '#3D5247',
          700: '#324539',
          800: '#2A3A2F',
          900: '#243127',
        },
        caramel: {
          50: '#FDF8F4',
          100: '#F9EDE0',
          200: '#F0D9C0',
          300: '#D4AA85',
          400: '#C4956A',
          500: '#A87B55',
          600: '#8C6644',
          700: '#735339',
          800: '#5E4430',
          900: '#4D3928',
        },
        charcoal: {
          50: '#F5F5F5',
          100: '#E8E8E8',
          200: '#D1D1D1',
          300: '#B0B0B0',
          400: '#888888',
          500: '#6B6B6B',
          600: '#555555',
          700: '#2D2D2D',
          800: '#1F1F1F',
          900: '#141414',
        }
      },
      fontFamily: {
        'serif': ['Noto Serif SC', 'Cormorant Garamond', 'Georgia', 'Times New Roman', 'serif'],
        'sans': ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
      },
      borderRadius: {
        'sm': '6px',
        'DEFAULT': '12px',
        'md': '12px',
        'lg': '20px',
        'xl': '24px',
      },
      boxShadow: {
        'soft': '0 4px 20px rgba(45, 45, 45, 0.08)',
        'hover': '0 8px 30px rgba(45, 45, 45, 0.12)',
        'card': '0 2px 12px rgba(45, 45, 45, 0.06)',
      },
      spacing: {
        '18': '4.5rem',
        '22': '5.5rem',
      },
      transitionTimingFunction: {
        'spring': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
        'expo-out': 'cubic-bezier(0.16, 1, 0.3, 1)',
        'smooth': 'cubic-bezier(0.65, 0, 0.35, 1)',
      },
      animation: {
        'fade-in-up': 'fadeInUp 0.5s ease-out forwards',
        'pulse-soft': 'pulseSoft 1.5s ease-in-out infinite',
      },
      keyframes: {
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '0.6' },
          '50%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
