/**
 * Tailwind CSS configuration for the Physiological Threat Intelligence Engine.
 *
 * This config sets up a dark, security‑oriented colour palette inspired by
 * network observability dashboards. It also enables the JIT engine for
 * lightning‑fast rebuilds during development.
 */
module.exports = {
  darkMode: 'class',
  content: [
    './pages/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
    './app/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        bg: '#0e0d1a',
        panel: '#18132f',
        accent: '#8b5cf6',
        success: '#10b981',
        warning: '#f59e0b',
        danger: '#ef4444',
      },
      boxShadow: {
        'glow': '0 0 10px rgba(139, 92, 246, 0.5)',
      },
    },
  },
  plugins: [],
};