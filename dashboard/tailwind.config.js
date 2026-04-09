/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        agency: {
          50:  '#f0f4ff',
          100: '#e0e8ff',
          500: '#4f46e5',
          600: '#4338ca',
          900: '#1e1b4b',
        },
      },
    },
  },
  plugins: [],
};
