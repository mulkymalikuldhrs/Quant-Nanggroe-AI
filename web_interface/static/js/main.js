/**
 * Main JavaScript - Agentic AI System
 * Core utility functions and Socket.IO integration
 */

(function() {
    'use strict';

    const App = {
        socket: null,

        init: function() {
            this.initSocket();
            this.initNavigation();
            console.log('Agentic AI System initialized');
        },

        initSocket: function() {
            if (typeof io === 'undefined') {
                console.warn('Socket.IO not loaded');
                return;
            }

            this.socket = io();

            this.socket.on('connect', function() {
                console.log('Connected to Agentic AI System');
                App.showNotification('Connected to server', 'success');
            });

            this.socket.on('disconnect', function() {
                console.log('Disconnected from server');
                App.showNotification('Disconnected from server', 'warning');
            });

            this.socket.on('system_update', function(data) {
                App.handleSystemUpdate(data);
            });

            this.socket.on('connection_status', function(data) {
                console.log('Connection status:', data.status);
            });
        },

        initNavigation: function() {
            // Active navigation highlighting
            const currentPath = window.location.pathname;
            document.querySelectorAll('.nav-link, .sidebar .nav-link').forEach(function(link) {
                if (link.getAttribute('href') === currentPath) {
                    link.classList.add('active');
                }
            });

            // Mobile sidebar toggle
            const sidebarToggle = document.getElementById('sidebarToggle');
            if (sidebarToggle) {
                sidebarToggle.addEventListener('click', function() {
                    const sidebar = document.getElementById('sidebar');
                    if (sidebar) sidebar.classList.toggle('show');
                });
            }
        },

        handleSystemUpdate: function(data) {
            // Update agent count in sidebar if present
            const agentCountEl = document.getElementById('agent-count');
            if (agentCountEl && data.agents_active !== undefined) {
                agentCountEl.textContent = data.agents_active + ' Agents Active';
            }

            // Update workflow count
            const workflowCountEl = document.getElementById('workflow-count');
            if (workflowCountEl) {
                workflowCountEl.textContent = (data.active_workflows || 0) + ' Workflows Running';
            }
        },

        showNotification: function(message, type) {
            type = type || 'info';
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-' + type + ' alert-dismissible fade show position-fixed';
            alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
            alertDiv.innerHTML = message +
                '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';

            document.body.appendChild(alertDiv);
            setTimeout(function() {
                if (alertDiv.parentNode) alertDiv.remove();
            }, 5000);
        },

        // API helper
        api: function(endpoint, options) {
            options = options || {};
            const defaults = {
                headers: { 'Content-Type': 'application/json' }
            };

            if (options.body && typeof options.body === 'object') {
                options.body = JSON.stringify(options.body);
            }

            return fetch(endpoint, Object.assign(defaults, options))
                .then(function(r) { return r.json(); });
        }
    };

    // Auto-initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() { App.init(); });
    } else {
        App.init();
    }

    window.AgenticApp = App;
})();
