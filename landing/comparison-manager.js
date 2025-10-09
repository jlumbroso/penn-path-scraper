/**
 * ComparisonManager - Reusable library for side-by-side chart comparisons
 *
 * Implements ADR-0008: Side-by-Side Visualization Comparison with Dynamic Panels
 *
 * Architecture: Wrapper-based pattern - treats visualizations as black boxes
 * that can be instantiated multiple times without modification.
 *
 * Usage:
 *   const manager = new ComparisonManager({
 *       containerId: 'chart-panels',
 *       chartType: 'school-enrollment',
 *       renderFunction: (canvasId, filters) => { ... }
 *   });
 *   manager.addPanel(); // Adds a new comparison panel
 */
class ComparisonManager {
    /**
     * @param {Object} config
     * @param {string} config.containerId - ID of container div
     * @param {string} config.chartType - Unique identifier for this chart type
     * @param {Function} config.renderFunction - (canvasId, filters, panelId) => Chart instance
     * @param {Object} config.defaultFilters - Default filter values
     * @param {Array<Object>} config.filterDefinitions - Filter config [{name, label, options}]
     * @param {number} config.maxPanels - Maximum panels allowed (default: 6)
     * @param {number} config.warnAtPanels - Show warning at this count (default: 4)
     */
    constructor(config) {
        this.containerId = config.containerId;
        this.chartType = config.chartType;
        this.renderFunction = config.renderFunction;
        this.defaultFilters = config.defaultFilters || {};
        this.filterDefinitions = config.filterDefinitions || [];
        this.maxPanels = config.maxPanels || 6;
        this.warnAtPanels = config.warnAtPanels || 4;

        this.panels = [];
        this.syncYAxis = true; // ON by default per ADR-0008
        this.nextPanelId = 1;

        // Store container reference
        this.container = document.getElementById(this.containerId);
        if (!this.container) {
            throw new Error(`Container #${this.containerId} not found`);
        }

        // Initialize UI
        this.initializeUI();
    }

    /**
     * Initialize the comparison UI structure
     */
    initializeUI() {
        this.container.innerHTML = `
            <div class="comparison-controls">
                <button class="comparison-add-btn" id="${this.chartType}-add-panel">
                    <span class="add-icon">+</span> Add Comparison Panel
                </button>
                <label class="sync-toggle">
                    <input type="checkbox" id="${this.chartType}-sync-axis" checked>
                    <span>Sync Y-Axis Scales</span>
                </label>
                <div class="panel-count-warning" id="${this.chartType}-warning" style="display: none;">
                    ⚠️ Many panels may impact performance
                </div>
            </div>
            <div class="comparison-panels-grid" id="${this.chartType}-panels-grid"></div>
        `;

        // Attach event listeners
        document.getElementById(`${this.chartType}-add-panel`).addEventListener('click', () => {
            this.addPanel();
        });

        document.getElementById(`${this.chartType}-sync-axis`).addEventListener('change', (e) => {
            this.syncYAxis = e.target.checked;
            if (this.syncYAxis) {
                this.syncAllAxes();
            }
        });

        // Add initial panel
        this.addPanel(this.defaultFilters);
    }

    /**
     * Add a new comparison panel
     * @param {Object} filters - Filter values (defaults to copy of last panel)
     * @param {string} title - Optional panel title
     */
    addPanel(filters = null, title = '') {
        // Check panel limit
        if (this.panels.length >= this.maxPanels) {
            alert(`Maximum ${this.maxPanels} panels allowed. Remove a panel to add another.`);
            return;
        }

        // Copy filters from last panel if not provided (ADR-0008: default behavior)
        if (!filters && this.panels.length > 0) {
            const lastPanel = this.panels[this.panels.length - 1];
            filters = { ...lastPanel.filters };
        } else if (!filters) {
            filters = { ...this.defaultFilters };
        }

        // Create panel object
        const panelId = `${this.chartType}-panel-${this.nextPanelId++}`;
        const panel = {
            id: panelId,
            filters: filters,
            title: title,
            chartInstance: null,
            element: null
        };

        this.panels.push(panel);
        this.renderPanel(panel);
        this.updateWarning();

        return panel;
    }

    /**
     * Render a panel's DOM and chart
     * @param {Object} panel
     */
    renderPanel(panel) {
        const grid = document.getElementById(`${this.chartType}-panels-grid`);

        // Create panel element
        const panelEl = document.createElement('div');
        panelEl.className = 'comparison-panel';
        panelEl.id = panel.id;

        // Build filter controls HTML
        const filterControlsHTML = this.filterDefinitions.map(filterDef => {
            const filterId = `${panel.id}-filter-${filterDef.name}`;
            const currentValue = panel.filters[filterDef.name] || '';

            return `
                <div class="panel-filter-group">
                    <label for="${filterId}">${filterDef.label}:</label>
                    <select id="${filterId}" class="panel-filter" data-filter="${filterDef.name}">
                        ${filterDef.options.map(opt => `
                            <option value="${opt.value}" ${opt.value === currentValue ? 'selected' : ''}>
                                ${opt.label}
                            </option>
                        `).join('')}
                    </select>
                </div>
            `;
        }).join('');

        // Build panel HTML
        panelEl.innerHTML = `
            ${this.panels.length > 1 ? `
                <button class="panel-remove" title="Remove panel">✕</button>
            ` : ''}

            <div class="panel-header">
                <input type="text"
                       class="panel-title-input"
                       placeholder="Panel title (optional)"
                       value="${panel.title}"
                       maxlength="50">
            </div>

            <div class="panel-filters">
                ${filterControlsHTML}
            </div>

            <div class="panel-chart-container">
                <canvas id="${panel.id}-canvas"></canvas>
            </div>

            <div class="panel-loading" style="display: none;">
                Loading chart...
            </div>
        `;

        grid.appendChild(panelEl);
        panel.element = panelEl;

        // Attach event listeners for this panel
        this.attachPanelEvents(panel);

        // Render the chart
        this.renderPanelChart(panel);
    }

    /**
     * Attach event listeners for a panel
     * @param {Object} panel
     */
    attachPanelEvents(panel) {
        // Remove button
        const removeBtn = panel.element.querySelector('.panel-remove');
        if (removeBtn) {
            removeBtn.addEventListener('click', () => {
                this.removePanel(panel.id);
            });
        }

        // Title input
        const titleInput = panel.element.querySelector('.panel-title-input');
        titleInput.addEventListener('input', (e) => {
            panel.title = e.target.value;
        });

        // Filter selects
        const filterSelects = panel.element.querySelectorAll('.panel-filter');
        filterSelects.forEach(select => {
            select.addEventListener('change', (e) => {
                const filterName = e.target.dataset.filter;
                panel.filters[filterName] = e.target.value;
                this.renderPanelChart(panel);
            });
        });
    }

    /**
     * Render or update a panel's chart
     * @param {Object} panel
     */
    renderPanelChart(panel) {
        const canvasId = `${panel.id}-canvas`;

        // Show loading state
        const loading = panel.element.querySelector('.panel-loading');
        if (loading) loading.style.display = 'block';

        // Destroy existing chart instance
        if (panel.chartInstance && typeof panel.chartInstance.destroy === 'function') {
            panel.chartInstance.destroy();
        }

        // Call the render function (black box - visualization doesn't know it's in a comparison)
        try {
            panel.chartInstance = this.renderFunction(canvasId, panel.filters, panel.id);

            // Sync Y-axis if enabled
            if (this.syncYAxis) {
                // Defer sync until all charts are rendered
                setTimeout(() => this.syncAllAxes(), 100);
            }
        } catch (error) {
            console.error(`Error rendering panel ${panel.id}:`, error);
            if (loading) {
                loading.innerHTML = '<p style="color: var(--penn-red);">Error loading chart</p>';
            }
        } finally {
            if (loading) loading.style.display = 'none';
        }
    }

    /**
     * Remove a panel
     * @param {string} panelId
     */
    removePanel(panelId) {
        // Don't allow removing the last panel
        if (this.panels.length === 1) {
            alert('Cannot remove the last panel');
            return;
        }

        const index = this.panels.findIndex(p => p.id === panelId);
        if (index === -1) return;

        const panel = this.panels[index];

        // Destroy chart instance
        if (panel.chartInstance && typeof panel.chartInstance.destroy === 'function') {
            panel.chartInstance.destroy();
        }

        // Remove DOM element
        if (panel.element && panel.element.parentNode) {
            panel.element.parentNode.removeChild(panel.element);
        }

        // Remove from panels array
        this.panels.splice(index, 1);

        this.updateWarning();
    }

    /**
     * Synchronize Y-axes across all panels
     */
    syncAllAxes() {
        if (!this.syncYAxis || this.panels.length === 0) return;

        // Find global max across all charts
        let globalMax = 0;

        this.panels.forEach(panel => {
            if (!panel.chartInstance || !panel.chartInstance.data) return;

            panel.chartInstance.data.datasets.forEach(dataset => {
                if (!dataset.data) return;
                const dataMax = Math.max(...dataset.data.filter(v => typeof v === 'number'));
                globalMax = Math.max(globalMax, dataMax);
            });
        });

        // Update all charts with same scale
        this.panels.forEach(panel => {
            if (!panel.chartInstance || !panel.chartInstance.options) return;

            if (panel.chartInstance.options.scales && panel.chartInstance.options.scales.y) {
                panel.chartInstance.options.scales.y.max = globalMax * 1.1; // 10% padding
                panel.chartInstance.update('none'); // Update without animation
            }
        });
    }

    /**
     * Update panel count warning
     */
    updateWarning() {
        const warning = document.getElementById(`${this.chartType}-warning`);
        if (warning) {
            warning.style.display = this.panels.length >= this.warnAtPanels ? 'block' : 'none';
        }

        // Update add button state
        const addBtn = document.getElementById(`${this.chartType}-add-panel`);
        if (addBtn) {
            addBtn.disabled = this.panels.length >= this.maxPanels;
        }
    }

    /**
     * Clear all panels and reset to single panel
     */
    clear() {
        while (this.panels.length > 0) {
            this.removePanel(this.panels[0].id);
        }
        this.addPanel(this.defaultFilters);
    }

    /**
     * Load a preset comparison ("Quest")
     * @param {Array<Object>} questPanels - [{filters, title}, ...]
     */
    loadQuest(questPanels) {
        this.clear();
        questPanels.forEach(panelConfig => {
            this.addPanel(panelConfig.filters, panelConfig.title);
        });
    }

    /**
     * Serialize comparison state to URL hash
     * @returns {string} URL hash fragment
     */
    serializeToHash() {
        const state = this.panels.map(p => ({
            filters: p.filters,
            title: p.title
        }));
        return btoa(JSON.stringify(state));
    }

    /**
     * Load comparison state from URL hash
     * @param {string} hash - Base64 encoded state
     */
    loadFromHash(hash) {
        try {
            const state = JSON.parse(atob(hash));
            this.clear();
            state.forEach(panelConfig => {
                this.addPanel(panelConfig.filters, panelConfig.title);
            });
        } catch (error) {
            console.error('Error loading comparison from hash:', error);
        }
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ComparisonManager;
}
