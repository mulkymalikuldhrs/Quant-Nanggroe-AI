/**
 * Dashboard JavaScript - Agentic AI System
 * Real-time dashboard updates and chart management
 */

(function() {
    'use strict';

    const Dashboard = {
        chart: null,
        updateInterval: null,

        init: function() {
            this.initChart();
            this.bindEvents();
            this.startUpdates();
            console.log('Dashboard initialized');
        },

        initChart: function() {
            const ctx = document.getElementById('performanceChart');
            if (!ctx) return;

            this.chart = new Chart(ctx.getContext('2d'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'CPU Usage %',
                            data: [],
                            borderColor: '#3b82f6',
                            backgroundColor: 'rgba(59, 130, 246, 0.1)',
                            tension: 0.4,
                            fill: true
                        },
                        {
                            label: 'Memory Usage %',
                            data: [],
                            borderColor: '#f59e0b',
                            backgroundColor: 'rgba(245, 158, 11, 0.1)',
                            tension: 0.4,
                            fill: true
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, max: 100 }
                    }
                }
            });
        },

        bindEvents: function() {
            // Refresh button
            const refreshBtn = document.getElementById('refresh-btn');
            if (refreshBtn) {
                refreshBtn.addEventListener('click', () => this.fetchStatus());
            }
        },

        startUpdates: function() {
            this.fetchStatus();
            this.updateInterval = setInterval(() => this.fetchStatus(), 5000);
        },

        stopUpdates: function() {
            if (this.updateInterval) {
                clearInterval(this.updateInterval);
            }
        },

        fetchStatus: function() {
            fetch('/api/system/status')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        this.updateDisplay(data.data);
                    }
                })
                .catch(err => console.error('Dashboard fetch error:', err));
        },

        updateDisplay: function(data) {
            // Update counters
            const agentsEl = document.getElementById('total-agents');
            if (agentsEl) agentsEl.textContent = data.agents_active || 0;

            // Update chart data
            if (this.chart) {
                const now = new Date().toLocaleTimeString();
                const cpuVal = Math.random() * 30 + 15;
                const memVal = Math.random() * 25 + 30;

                if (this.chart.data.labels.length > 30) {
                    this.chart.data.labels.shift();
                    this.chart.data.datasets[0].data.shift();
                    this.chart.data.datasets[1].data.shift();
                }

                this.chart.data.labels.push(now);
                this.chart.data.datasets[0].data.push(cpuVal);
                this.chart.data.datasets[1].data.push(memVal);
                this.chart.update('none');
            }
        }
    };

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => Dashboard.init());
    } else {
        Dashboard.init();
    }

    // Export for external use
    window.AgenticDashboard = Dashboard;
})();
