/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      // CoachOwl palette — mirrors landing/index.html so the app and the
      // marketing site read as one calm product.
      colors: {
        cream: '#FBF8F1',
        ink: {
          DEFAULT: '#12302B',
          deep: '#0B463D',
        },
        // Brand green / teal scale
        brand: {
          50: '#F4FAF8',
          100: '#E3F0EB',
          200: '#C9E3DB',
          400: '#1B7A6E',
          500: '#19A38E', // teal accent
          600: '#0E5A4F', // primary green
          700: '#0B463D',
          800: '#093A33',
        },
        // Amber accent (primary call-to-action)
        amber: {
          DEFAULT: '#F2A23C',
          500: '#F2A23C',
          600: '#EE9622',
          700: '#E07F1B',
          ink: '#3A2306',
          soft: '#FBEBD2',
        },
        muted: '#7E938E',
        body: '#43615B',
        subtle: '#53706A',
        danger: {
          DEFAULT: '#C0473A',
          soft: '#FBF1F0',
        },
      },
      fontFamily: {
        display: ['Nunito', 'system-ui', 'sans-serif'],
        sans: ['"Nunito Sans"', 'system-ui', '-apple-system', 'sans-serif'],
      },
      borderRadius: {
        xl: '14px',
        '2xl': '18px',
        '3xl': '24px',
      },
      boxShadow: {
        card: '0 16px 36px -24px rgba(11,70,61,0.3)',
        lift: '0 36px 70px -34px rgba(11,70,61,0.5), 0 6px 18px -10px rgba(11,70,61,0.18)',
        amber: '0 14px 26px -12px rgba(242,162,60,0.9), inset 0 1px 0 rgba(255,255,255,0.45)',
      },
      keyframes: {
        'co-float': {
          '0%,100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-9px)' },
        },
      },
      animation: {
        float: 'co-float 7s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
