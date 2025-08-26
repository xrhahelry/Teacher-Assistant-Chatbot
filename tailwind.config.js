/** @type {import('tailwindcss').Config} */

module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./app/static/**/*.{css,js}",
  ],
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
