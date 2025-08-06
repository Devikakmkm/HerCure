// Initialize charts when document is ready
$(document).ready(function() {
    // Only proceed if chartData is defined
    if (typeof window.chartData === 'undefined') {
        console.error('chartData is not defined');
        return;
    }

    // Initialize Cycle Length Chart if element exists
    const cycleCtx = document.getElementById('cycleLengthChart');
    if (cycleCtx && window.chartData.cycleData && window.chartData.cycleData.labels && window.chartData.cycleData.labels.length > 0) {
        new Chart(cycleCtx, {
            type: 'line',
            data: {
                labels: window.chartData.cycleData.labels,
                datasets: [{
                    label: 'Cycle Length (days)',
                    data: window.chartData.cycleData.data,
                    borderColor: '#ec4899',
                    backgroundColor: 'rgba(236, 72, 153, 0.1)',
                    tension: 0.4,
                    fill: true,
                    borderWidth: 2,
                    pointBackgroundColor: '#ec4899',
                    pointBorderColor: '#fff',
                    pointHoverRadius: 5,
                    pointHoverBackgroundColor: '#ec4899',
                    pointHoverBorderColor: '#fff',
                    pointHitRadius: 10,
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { 
                    legend: { 
                        display: true,
                        position: 'top',
                        labels: {
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleFont: {
                            size: 14,
                            weight: 'bold'
                        },
                        bodyFont: {
                            size: 13
                        },
                        padding: 12,
                        displayColors: false,
                        callbacks: {
                            label: function(context) {
                                return 'Length: ' + context.parsed.y + ' days';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        min: function() {
                            const min = Math.min(...window.chartData.cycleData.data);
                            return Math.max(15, min - 2);
                        },
                        max: function() {
                            const max = Math.max(...window.chartData.cycleData.data);
                            return Math.min(45, max + 2);
                        },
                        grid: { 
                            color: 'rgba(0,0,0,0.05)'
                        },
                        ticks: {
                            stepSize: 1
                        }
                    },
                    x: { 
                        grid: { display: false },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart'
                }
            }
        });
    }

    // Initialize Symptom Chart if element exists
    const symptomCtx = document.getElementById('symptomChart');
    if (symptomCtx && window.chartData.symptomData && window.chartData.symptomData.labels && window.chartData.symptomData.labels.length > 0) {
        const backgroundColors = [
            '#ec4899', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#8b5cf6',
            '#ef4444', '#06b6d4', '#84cc16', '#f59e0b', '#10b981', '#6366f1'
        ];

        new Chart(symptomCtx, {
            type: 'bar',
            data: {
                labels: window.chartData.symptomData.labels,
                datasets: [{
                    label: 'Occurrences',
                    data: window.chartData.symptomData.data,
                    backgroundColor: backgroundColors,
                    borderColor: backgroundColors.map(color => color.replace('0.7', '1')),
                    borderWidth: 1,
                    borderRadius: 4,
                    barThickness: 'flex',
                    maxBarThickness: 40,
                    minBarLength: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleFont: {
                            size: 14,
                            weight: 'bold'
                        },
                        bodyFont: {
                            size: 13
                        },
                        padding: 12,
                        displayColors: false,
                        callbacks: {
                            label: function(context) {
                                const label = context.dataset.label || '';
                                const value = context.parsed.y;
                                return `${label}: ${value} ${value === 1 ? 'time' : 'times'}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            precision: 0,
                            stepSize: 1
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }
                },
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart'
                }
            }
        });
    }
});

// Function to refresh analytics
function refreshAnalytics() {
    location.reload();
}

// Add event listener for window resize to handle chart responsiveness
let resizeTimer;
window.addEventListener('resize', function() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function() {
        const charts = Chart.getChart('cycleLengthChart');
        if (charts) {
            charts.resize();
        }
        const symptomChart = Chart.getChart('symptomChart');
        if (symptomChart) {
            symptomChart.resize();
        }
    }, 250);
});
