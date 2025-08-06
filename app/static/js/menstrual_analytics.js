// Create empty state charts when no data is available
function createEmptyCharts() {
    // Empty Cycle Length Chart
    const cycleCtx = document.getElementById('cycleLengthChart');
    if (cycleCtx) {
        new Chart(cycleCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: ['No data available'],
                datasets: [{
                    label: 'Cycle Length (days)',
                    data: [],
                    borderColor: '#d1d5db',
                    backgroundColor: 'rgba(209, 213, 219, 0.1)',
                    borderDash: [5, 5],
                    borderWidth: 2,
                    pointBackgroundColor: '#9ca3af',
                    pointBorderColor: '#fff',
                    pointHoverRadius: 5,
                    pointHoverBackgroundColor: '#9ca3af',
                    pointHoverBorderColor: '#fff',
                    pointHitRadius: 10,
                    pointBorderWidth: 2,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function() {
                                return 'No cycle data available';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        min: 20,
                        max: 45,
                        grid: { color: 'rgba(0,0,0,0.05)' },
                        ticks: { color: '#9ca3af' }
                    },
                    x: { 
                        grid: { display: false },
                        ticks: { color: '#9ca3af' }
                    }
                }
            }
        });
    }

    // Empty Symptom Chart
    const symptomCtx = document.getElementById('symptomChart');
    if (symptomCtx) {
        new Chart(symptomCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['No symptoms logged'],
                datasets: [{
                    data: [1],
                    backgroundColor: ['#e5e7eb'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function() {
                                return 'No symptom data available';
                            }
                        }
                    }
                },
                cutout: '70%'
            }
        });
    }

    // Empty Mood Chart
    const moodCtx = document.getElementById('moodChart');
    if (moodCtx) {
        new Chart(moodCtx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: ['No mood data'],
                datasets: [{
                    label: 'Mood',
                    data: [],
                    backgroundColor: 'rgba(156, 163, 175, 0.6)',
                    borderColor: 'rgba(107, 114, 128, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function() {
                                return 'No mood data available';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 5,
                        grid: { color: 'rgba(0,0,0,0.05)' },
                        ticks: { color: '#9ca3af' }
                    },
                    x: { 
                        grid: { display: false },
                        ticks: { color: '#9ca3af' }
                    }
                }
            }
        });
    }
}

// Initialize all charts for the menstrual analytics page
function initializeMenstrualAnalyticsCharts(chartData) {
    console.log('Initializing charts with data:', chartData);
    
    // If no chart data is provided, show empty states
    if (!chartData || Object.keys(chartData).length === 0) {
        console.log('No chart data provided, showing empty states');
        createEmptyCharts();
        return;
    }

    // Initialize Cycle Length Chart if element exists
    const cycleCtx = document.getElementById('cycleLengthChart');
    if (cycleCtx) {
        const hasCycleData = chartData.chart_data && 
                           chartData.chart_data.dates && 
                           chartData.chart_data.dates.length > 0 &&
                           chartData.chart_data.cycle_lengths &&
                           chartData.chart_data.cycle_lengths.length > 0;
        
        if (hasCycleData) {
            console.log('Initializing cycle length chart with data:', {
                labels: chartData.chart_data.dates,
                data: chartData.chart_data.cycle_lengths
            });
            
            // Create chart with actual data
            new Chart(cycleCtx.getContext('2d'), {
                type: 'line',
                data: {
                    labels: chartData.chart_data.dates,
                    datasets: [{
                        label: 'Cycle Length (days)',
                        data: chartData.chart_data.cycle_lengths,
                        borderColor: '#ec4899',
                        backgroundColor: 'rgba(236, 72, 153, 0.1)',
                        tension: 0.4,
                        fill: true,
                        pointBackgroundColor: '#ec4899',
                        pointBorderColor: '#fff',
                        pointHoverRadius: 5,
                        pointHoverBackgroundColor: '#ec4899',
                        pointHoverBorderColor: '#fff',
                        pointHitRadius: 10,
                        pointBorderWidth: 2,
                        pointRadius: 3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { 
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return `Cycle: ${context.parsed.y} days`;
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            min: 20,
                            max: 45,
                            grid: { color: 'rgba(0,0,0,0.1)' },
                            ticks: {
                                stepSize: 5,
                                callback: function(value) {
                                    return value + ' days';
                                }
                            }
                        },
                        x: { 
                            grid: { display: false },
                            ticks: {
                                maxRotation: 45,
                                minRotation: 45
                            }
                        }
                    }
                }
            });
        } else {
            // Create empty chart with no data message
            createEmptyCharts();
        }
    }

    // Initialize Symptom Distribution Chart if element exists
    const symptomDistCtx = document.getElementById('symptomDistributionChart');
    if (symptomDistCtx) {
        const hasSymptomData = chartData.symptom_counts && Object.keys(chartData.symptom_counts).length > 0;
        
        if (hasSymptomData) {
            const symptomLabels = Object.keys(chartData.symptom_counts);
            const symptomData = Object.values(chartData.symptom_counts);
            
            console.log('Initializing symptom distribution chart with data:', {
                labels: symptomLabels,
                data: symptomData
            });
            
            new Chart(symptomDistCtx.getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: symptomLabels,
                    datasets: [{
                        data: symptomData,
                        backgroundColor: [
                            '#ec4899', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#8b5cf6',
                            '#ef4444', '#06b6d4', '#84cc16', '#f59e0b', '#10b981', '#6366f1'
                        ],
                        borderWidth: 2,
                        borderColor: '#ffffff',
                        hoverOffset: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 20,
                                usePointStyle: true,
                                boxWidth: 8,
                                font: {
                                    size: 11
                                }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const value = context.raw;
                                    const percentage = Math.round((value / total) * 100);
                                    return `${context.label}: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    },
                    cutout: '70%',
                    layout: {
                        padding: {
                            top: 10,
                            bottom: 10
                        }
                    }
                }
            });
        } else {
            // Create empty chart with no data message
            createEmptyCharts();
        }
    }

    // Initialize Mood Tracker Chart if element exists
    const moodTrackerCtx = document.getElementById('moodTrackerChart');
    if (moodTrackerCtx) {
        const hasMoodData = chartData.mood_data && 
                          chartData.mood_data.labels && 
                          chartData.mood_data.labels.length > 0 &&
                          chartData.mood_data.data &&
                          chartData.mood_data.data.length > 0;
        
        if (hasMoodData) {
            console.log('Initializing mood tracker chart with data:', {
                labels: chartData.mood_data.labels,
                data: chartData.mood_data.data
            });
            
            new Chart(moodTrackerCtx.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: chartData.mood_data.labels,
                    datasets: [{
                        label: 'Mood Level',
                        data: chartData.mood_data.data,
                        data: chartData.mood_data.values || [],
                        backgroundColor: [
                            'rgba(239, 68, 68, 0.7)',  // Red for sad
                            'rgba(249, 115, 22, 0.7)', // Orange for down
                            'rgba(234, 179, 8, 0.7)',  // Yellow for neutral
                            'rgba(16, 185, 129, 0.7)', // Green for happy
                            'rgba(59, 130, 246, 0.7)'  // Blue for excited
                        ],
                        borderColor: [
                            'rgba(239, 68, 68, 1)',
                            'rgba(249, 115, 22, 1)',
                            'rgba(234, 179, 8, 1)',
                            'rgba(16, 185, 129, 1)',
                            'rgba(59, 130, 246, 1)'
                        ],
                        borderWidth: 1,
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const moods = ['Sad', 'Down', 'Neutral', 'Happy', 'Excited'];
                                    return `${moods[context.dataIndex]}: ${context.raw} entries`;
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(0,0,0,0.1)' },
                            ticks: {
                                precision: 0,
                                callback: function(value) {
                                    if (value % 1 === 0) {
                                        return value;
                                    }
                                }
                            }
                        },
                        x: { 
                            grid: { display: false }
                        }
                    }
                }
            });
        } else {
            // Create empty chart with no data message
            createEmptyCharts();
        }
    }
}

// Function to refresh analytics
function refreshAnalytics() {
    location.reload();
}

// Function to show debug information
function showDebugInfo(chartData) {
    if (!chartData) return;
    
    // Show debug info in the UI
    const debugInfo = document.getElementById('debug-info');
    if (debugInfo) {
        debugInfo.classList.remove('hidden');
        
        // Show cycle data
        const cycleDataEl = document.getElementById('cycle-data-debug');
        if (cycleDataEl) {
            cycleDataEl.textContent = JSON.stringify({
                dates: chartData.chart_data?.dates || [],
                cycle_lengths: chartData.chart_data?.cycle_lengths || [],
                period_lengths: chartData.chart_data?.period_lengths || []
            }, null, 2);
        }
        
        // Show symptom data
        const symptomDataEl = document.getElementById('symptom-data-debug');
        if (symptomDataEl) {
            symptomDataEl.textContent = JSON.stringify({
                symptoms: chartData.symptom_counts || {},
                moods: chartData.mood_data || {}
            }, null, 2);
        }
    }
}

// Function to check if we have any chart data
function hasChartData(chartData) {
    if (!chartData) return false;
    
    // Check cycle data
    if (chartData.chart_data?.dates?.length > 0) return true;
    
    // Check symptom data
    if (chartData.symptom_counts && Object.keys(chartData.symptom_counts).length > 0) return true;
    
    // Check mood data
    if (chartData.mood_data?.labels?.length > 0) return true;
    
    return false;
}

// Initialize charts when document is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded, initializing charts...');
    
    try {
        // Get chart data from the JSON script tag
        const chartDataElement = document.getElementById('chart-data');
        if (!chartDataElement) {
            throw new Error('Chart data element not found');
        }
        
        const chartData = JSON.parse(chartDataElement.textContent);
        console.log('Parsed chart data:', chartData);
        
        // Show debug information
        showDebugInfo(chartData);
        
        // Store chart data in window for debugging
        window.chartData = chartData;
        
        // Check if we have any data
        if (!hasChartData(chartData)) {
            console.warn('No chart data available');
            showInfo('No data available to display. Start tracking your cycles to see analytics.');
            createEmptyCharts();
            return;
        }
        
        // Initialize the charts
        if (typeof initializeMenstrualAnalyticsCharts === 'function') {
            initializeMenstrualAnalyticsCharts(chartData);
        } else {
            throw new Error('Chart initialization function not found');
        }
    } catch (error) {
        console.error('Error initializing charts:', error);
        
        // Show error message to user
        const errorContainer = document.createElement('div');
        errorContainer.className = 'bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4';
        errorContainer.innerHTML = `
            <p class="font-bold">Error</p>
            <p>Failed to initialize charts. Please try refreshing the page.</p>
            <p class="text-sm mt-2">${error.message}</p>
            <p class="text-xs mt-2">Check the browser console for more details.</p>
        `;
        document.querySelector('.container').prepend(errorContainer);
        
        // Create empty charts as fallback
        createEmptyCharts();
    }
});
