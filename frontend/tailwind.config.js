/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        indigo: {
          650: '#4f46e5', // Custom brand Indigo
        },
        emerald: {
          650: '#059669', // Custom brand Emerald
        }
      }
    },
  },
  plugins: [],
}

