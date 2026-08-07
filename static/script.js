document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('drawingCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    let isDrawing = false;
    
    // Set initial canvas background to white
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    function startDrawing(e) {
        isDrawing = true;
        draw(e);
    }

    function stopDrawing() {
        isDrawing = false;
        ctx.beginPath();
    }

    function draw(e) {
        if (!isDrawing) return;
        
        ctx.lineWidth = 5;
        ctx.lineCap = 'round';
        ctx.strokeStyle = '#000000';

        const rect = canvas.getBoundingClientRect();
        const clientX = e.clientX || (e.touches && e.touches[0].clientX);
        const clientY = e.clientY || (e.touches && e.touches[0].clientY);
        
        if (clientX === undefined || clientY === undefined) return;

        const x = clientX - rect.left;
        const y = clientY - rect.top;

        ctx.lineTo(x, y);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(x, y);
    }

    // Mouse events
    canvas.addEventListener('mousedown', startDrawing);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseup', stopDrawing);
    canvas.addEventListener('mouseleave', stopDrawing);

    // Touch events for mobile devices
    canvas.addEventListener('touchstart', (e) => {
        e.preventDefault();
        startDrawing(e);
    }, { passive: false });
    canvas.addEventListener('touchmove', (e) => {
        e.preventDefault();
        draw(e);
    }, { passive: false });
    canvas.addEventListener('touchend', (e) => {
        e.preventDefault();
        stopDrawing();
    });

    // Clear button handler
    const clearBtn = document.getElementById('clearBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
        });
    }

    // Send button handler
    const sendBtn = document.getElementById('sendBtn');
    if (sendBtn) {
        sendBtn.addEventListener('click', () => {
            canvas.toBlob(function(blob) {
                let formData = new FormData();
                formData.append('image', blob, 'drawing.png');

                fetch('/upload', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    console.log('Success:', data);
                    alert('Drawing sent successfully!');
                    ctx.fillStyle = '#ffffff';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);
                })
                .catch((error) => {
                    console.error('Error:', error);
                    alert('Error connecting to server');
                });
            }, 'image/png');
        });
    }
});
