/**
 * Handover Canvas System - Damage Diagram Drawing
 * Handles fabric.js canvas initialization for vehicle damage annotation
 */

let damageCanvas = null;

/**
 * Initialize damage canvas for drawing
 */
function initializeDamageCanvas() {
    const canvasEl = document.getElementById('damage-canvas');
    if (!canvasEl || damageCanvas) return;

    try {
        damageCanvas = new fabric.Canvas('damage-canvas', {
            isDrawingMode: true,
            backgroundColor: '#f8f9fa',
            width: canvasEl.offsetWidth,
            height: 400
        });

        // Set default brush settings
        damageCanvas.freeDrawingBrush.color = '#FF0000';
        damageCanvas.freeDrawingBrush.width = 3;

        // Load vehicle diagram background
        const diagramPath = '/static/images/vehicle_diagram.png';
        fabric.util.loadImage(diagramPath, function(img) {
            if (img) {
                if (img.width > 0 && img.height > 0) {
                    const fabricImage = new fabric.Image(img, {
                        left: 0,
                        top: 0,
                        scaleX: damageCanvas.width / img.width,
                        scaleY: damageCanvas.height / img.height,
                        selectable: false,
                        evented: false
                    });

                    damageCanvas.setBackgroundImage(fabricImage, damageCanvas.renderAll.bind(damageCanvas));
                } else {
                    showDiagramPlaceholder('خطأ: لم يتمكن من تحميل صورة المركبة');
                }
            } else {
                showDiagramPlaceholder('خطأ: الصورة غير متوفرة');
            }
        }, { crossOrigin: 'anonymous' });

        // Load existing damage diagram if in edit mode
        const existingData = document.getElementById('damage-diagram-data')?.value;
        if (existingData && existingData.trim()) {
            fabric.util.loadImage(existingData, function(img) {
                if (img) {
                    const fabricImage = new fabric.Image(img, {
                        left: damageCanvas.width / 2,
                        top: damageCanvas.height / 2,
                        originX: 'center',
                        originY: 'center'
                    });
                    damageCanvas.add(fabricImage);
                    damageCanvas.renderAll();
                }
            });
        }

        // Setup drawing controls
        setupDamageCanvasControls();

    } catch (error) {
        console.error('Error initializing damage canvas:', error);
        showDiagramPlaceholder('خطأ: فشل تحميل لوحة الرسم');
    }
}

/**
 * Setup damage canvas control buttons and color picker
 */
function setupDamageCanvasControls() {
    const drawModeBtn = document.getElementById('draw-mode-btn');
    const selectModeBtn = document.getElementById('select-mode-btn');
    const colorPicker = document.getElementById('draw-color-picker');
    const lineWidthSlider = document.getElementById('draw-line-width');
    const clearBtn = document.getElementById('clear-canvas-btn');

    if (drawModeBtn) {
        drawModeBtn.addEventListener('click', function() {
            damageCanvas.isDrawingMode = true;
            drawModeBtn.classList.add('btn-danger', 'active');
            selectModeBtn?.classList.remove('btn-outline-secondary', 'active');
            selectModeBtn?.classList.add('btn-outline-secondary');
        });
    }

    if (selectModeBtn) {
        selectModeBtn.addEventListener('click', function() {
            damageCanvas.isDrawingMode = false;
            selectModeBtn.classList.add('btn-info', 'active');
            drawModeBtn?.classList.remove('btn-danger', 'active');
            drawModeBtn?.classList.add('btn-outline-danger');
        });
    }

    if (colorPicker) {
        colorPicker.addEventListener('input', function() {
            damageCanvas.freeDrawingBrush.color = this.value;
        });
    }

    if (lineWidthSlider) {
        lineWidthSlider.addEventListener('input', function() {
            damageCanvas.freeDrawingBrush.width = parseInt(this.value);
            document.getElementById('brush-width-display').textContent = this.value + ' px';
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            if (confirm('هل تريد مسح جميع الرسومات؟')) {
                damageCanvas.clear();
                damageCanvas.backgroundColor = '#f8f9fa';
                damageCanvas.renderAll();
            }
        });
    }
}

/**
 * Save damage diagram to hidden input
 */
function saveDamageCanvas() {
    const input = document.getElementById('damage_diagram_data');
    if (damageCanvas && input) {
        input.value = damageCanvas.toDataURL('image/png');
        return true;
    }
    return false;
}

/**
 * Handle canvas resize (responsive)
 */
function resizeDamageCanvas() {
    if (!damageCanvas) return;

    const container = damageCanvas.getElement().parentElement;
    const newWidth = container.offsetWidth - 20; // Account for padding

    if (newWidth !== damageCanvas.width) {
        damageCanvas.setDimensions({
            width: newWidth,
            height: 400
        });
        damageCanvas.renderAll();
    }
}

/**
 * Show placeholder message if diagram fails to load
 */
function showDiagramPlaceholder(message) {
    const canvasEl = document.getElementById('damage-canvas');
    if (canvasEl) {
        const parent = canvasEl.parentElement;
        const placeholder = document.createElement('div');
        placeholder.className = 'alert alert-warning';
        placeholder.innerHTML = `
            <i class="fas fa-exclamation-triangle me-2"></i>
            ${message}
            <p class="mt-2 mb-0">يمكنك تحميل صورة المركبة أو الرسم مباشرة بدون الصورة الخلفية</p>
        `;
        parent.appendChild(placeholder);
    }
}

/**
 * Upload custom vehicle diagram image
 */
function uploadDiagramImage(file) {
    if (!damageCanvas || !file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
        fabric.util.loadImage(e.target.result, function(img) {
            if (img && img.width > 0 && img.height > 0) {
                const fabricImage = new fabric.Image(img, {
                    left: 0,
                    top: 0,
                    scaleX: damageCanvas.width / img.width,
                    scaleY: damageCanvas.height / img.height,
                    selectable: false,
                    evented: false
                });

                damageCanvas.setBackgroundImage(fabricImage, damageCanvas.renderAll.bind(damageCanvas));
            }
        });
    };
    reader.readAsDataURL(file);
}

/**
 * Export damage canvas as image
 */
function exportDamageCanvasImage() {
    if (!damageCanvas) return null;

    const dataUrl = damageCanvas.toDataURL({
        format: 'png',
        quality: 0.8
    });

    return dataUrl;
}

/**
 * Undo last action on canvas
 */
function undoDamageCanvas() {
    if (!damageCanvas || damageCanvas._objects.length === 0) {
        return;
    }

    const lastObject = damageCanvas._objects.pop();
    damageCanvas.renderAll();
}

/**
 * Get canvas state for comparison
 */
function getDamageCanvasState() {
    if (!damageCanvas) return null;

    return {
        objectCount: damageCanvas._objects.length,
        drawing: damageCanvas.isDrawingMode,
        data: damageCanvas.toJSON()
    };
}

/**
 * Reset canvas to initial state
 */
function resetDamageCanvas() {
    if (!damageCanvas) return;

    damageCanvas.clear();
    damageCanvas.isDrawingMode = true;
    damageCanvas.freeDrawingBrush.color = '#FF0000';
    damageCanvas.freeDrawingBrush.width = 3;
    damageCanvas.renderAll();
}

// ===== INITIALIZATION =====

document.addEventListener('DOMContentLoaded', function() {
    // Initialize damage canvas
    const damageCanvasEl = document.getElementById('damage-canvas');
    if (damageCanvasEl) {
        setTimeout(() => {
            initializeDamageCanvas();
            // Resize on window resize
            window.addEventListener('resize', resizeDamageCanvas);
        }, 100);
    }

    // Save canvas data before form submission
    const form = document.getElementById('main-handover-form');
    if (form) {
        form.addEventListener('submit', function() {
            saveDamageCanvas();
        });
    }

    // Setup custom diagram upload (if exists)
    const diagramUploadInput = document.getElementById('diagram-image-upload');
    if (diagramUploadInput) {
        diagramUploadInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                uploadDiagramImage(file);
            }
        });
    }

    // Setup diagram export button (if exists)
    const exportBtn = document.getElementById('export-diagram-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', function() {
            const imageData = exportDamageCanvasImage();
            if (imageData) {
                const link = document.createElement('a');
                link.href = imageData;
                link.download = 'damage-diagram.png';
                link.click();
            }
        });
    }

    // Setup undo button (if exists)
    const undoBtn = document.getElementById('undo-diagram-btn');
    if (undoBtn) {
        undoBtn.addEventListener('click', undoDamageCanvas);
    }
});
