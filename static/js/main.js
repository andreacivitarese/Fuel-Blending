/**
 * Fuel Blending Optimization Web Application
 * Main JavaScript file
 */

// Initialize the application when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Enable tooltips everywhere
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Enable popovers everywhere
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // File input handler for custom file inputs
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(function(input) {
        input.addEventListener('change', function() {
            const fileName = this.value.split('\\').pop();
            const fileInfoElement = this.nextElementSibling;
            
            if (fileInfoElement && fileName) {
                const icon = fileInfoElement.querySelector('i');
                if (icon) {
                    icon.className = 'fas fa-check-circle text-success';
                }
                fileInfoElement.innerHTML = '<i class="fas fa-check-circle text-success"></i> Selected: <strong>' + fileName + '</strong>';
            }
        });
    });

    // Handle form submissions with validation
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const closeButton = alert.querySelector('.btn-close');
            if (closeButton) {
                closeButton.click();
            } else {
                alert.classList.add('fade');
                setTimeout(function() {
                    alert.remove();
                }, 150);
            }
        }, 5000);
    });

    // Add confirmation dialog for sensitive actions
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    confirmButtons.forEach(function(button) {
        button.addEventListener('click', function(event) {
            const message = this.getAttribute('data-confirm') || 'Are you sure you want to proceed?';
            if (!confirm(message)) {
                event.preventDefault();
            }
        });
    });

    // Handle collapsible sections with state persistence
    const collapsibles = document.querySelectorAll('.collapse');
    collapsibles.forEach(function(collapse) {
        collapse.addEventListener('shown.bs.collapse', function() {
            localStorage.setItem('collapse_' + this.id, 'shown');
        });
        
        collapse.addEventListener('hidden.bs.collapse', function() {
            localStorage.setItem('collapse_' + this.id, 'hidden');
        });
        
        // Restore state
        const storedState = localStorage.getItem('collapse_' + collapse.id);
        if (storedState === 'shown') {
            new bootstrap.Collapse(collapse).show();
        }
    });

    // Attach CSV export button functionality
    document.querySelectorAll('.export-csv-btn').forEach(function(button) {
        button.addEventListener('click', function() {
            const tableId = this.getAttribute('data-table-id');
            const fileName = this.getAttribute('data-file-name') || 'export.csv';
            exportTableToCSV(tableId, fileName);
        });
    });

    // Responsive table scrolling indicators
    const responsiveTables = document.querySelectorAll('.table-responsive');
    responsiveTables.forEach(function(tableContainer) {
        const table = tableContainer.querySelector('table');
        if (table && tableContainer.scrollWidth > tableContainer.clientWidth) {
            if (!tableContainer.querySelector('.scroll-indicator')) {
                const indicator = document.createElement('div');
                indicator.className = 'scroll-indicator';
                indicator.innerHTML = '<i class="fas fa-arrows-alt-h"></i> Scroll horizontally';
                tableContainer.parentNode.insertBefore(indicator, tableContainer);
            }
        }
    });
});

/**
 * Export a table to CSV file
 * @param {string} tableId - The ID of the table to export
 * @param {string} filename - The filename to save as
 */
function exportTableToCSV(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    let csv = [];
    const rows = table.querySelectorAll('tr');
    
    for (let i = 0; i < rows.length; i++) {
        const row = [], cols = rows[i].querySelectorAll('td, th');
        
        for (let j = 0; j < cols.length; j++) {
            // Replace any commas in the cell with semicolons to avoid CSV issues
            let text = cols[j].innerText.replace(/,/g, ';');
            // Enclose in quotes if contains semicolons
            if (text.includes(';')) {
                text = '"' + text + '"';
            }
            row.push(text);
        }
        
        csv.push(row.join(','));
    }
    
    // Download CSV file
    downloadCSV(csv.join('\n'), filename);
}

/**
 * Trigger download of CSV data
 * @param {string} csv - The CSV content
 * @param {string} filename - The filename to save as
 */
function downloadCSV(csv, filename) {
    const csvFile = new Blob([csv], {type: 'text/csv'});
    const downloadLink = document.createElement('a');
    
    downloadLink.download = filename;
    downloadLink.href = window.URL.createObjectURL(csvFile);
    downloadLink.style.display = 'none';
    
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
}

/**
 * Format a number with specified decimals
 * @param {number} value - The number to format
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted number
 */
function formatNumber(value, decimals = 2) {
    return Number(value).toFixed(decimals);
}

/**
 * Dynamically generate a pie chart from table data
 * @param {string} tableId - The ID of the table containing the data
 * @param {string} chartId - The ID of the canvas element for the chart
 * @param {string} labelColumn - The name or index of the column for labels
 * @param {string} valueColumn - The name or index of the column for values
 */
function generatePieChartFromTable(tableId, chartId, labelColumn, valueColumn) {
    const table = document.getElementById(tableId);
    const canvas = document.getElementById(chartId);
    if (!table || !canvas) return;
    
    const rows = table.querySelectorAll('tbody tr');
    const labels = [];
    const data = [];
    const backgroundColors = [
        '#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b', 
        '#6f42c1', '#fd7e14', '#20c9a6', '#5a5c69', '#858796'
    ];
    
    rows.forEach(function(row) {
        const cells = row.querySelectorAll('td');
        if (isNaN(labelColumn)) {
            // Find header index by text
            const headerCells = table.querySelectorAll('thead th');
            labelColumn = Array.from(headerCells).findIndex(cell => cell.innerText === labelColumn);
            valueColumn = Array.from(headerCells).findIndex(cell => cell.innerText === valueColumn);
        }
        
        if (cells[labelColumn] && cells[valueColumn]) {
            labels.push(cells[labelColumn].innerText);
            data.push(parseFloat(cells[valueColumn].innerText));
        }
    });
    
    if (labels.length > 0 && data.length > 0) {
        new Chart(canvas, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: backgroundColors.slice(0, data.length),
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            font: { size: 12 }
                        }
                    }
                }
            }
        });
    }
} 