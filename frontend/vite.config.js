import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    server: {
        port: 3000,
        proxy: {
            '/admin': 'http://localhost:8001',
            '/activate': 'http://localhost:8001',
            '/validate': 'http://localhost:8001',
            '/health': 'http://localhost:8001',
        }
    }
})
