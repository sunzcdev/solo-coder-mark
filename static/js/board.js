(function () {
    const meta = window.__BOARD__ || {};
    const BOARD_ID = meta.id;
    const USER = meta.user || '';

    const canvas = document.getElementById('board-canvas');
    const ctx = canvas.getContext('2d');
    const canvasWrap = document.querySelector('.canvas-wrap');
    const connStatus = document.getElementById('conn-status');
    const toast = document.getElementById('toast');

    const state = {
        tool: 'pen',
        color: '#000000',
        width: 3,
        drawing: false,
        startPoint: null,
        currentPoints: [],
        shapes: [],
        undoStack: [],
        redoStack: [],
        socketReady: false,
    };

    function showToast(msg, type) {
        toast.textContent = msg;
        toast.className = 'toast show ' + (type || '');
        setTimeout(() => toast.className = 'toast', 2200);
    }

    function resizeCanvas() {
        const rect = canvasWrap.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        canvas.style.width = rect.width + 'px';
        canvas.style.height = rect.height + 'px';
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        redrawAll();
    }

    function drawShape(shape, skipCommit) {
        ctx.strokeStyle = shape.color || '#000000';
        ctx.fillStyle = shape.color || '#000000';
        ctx.lineWidth = shape.width || 3;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        const pts = shape.points || [];
        if (shape.type === 'pen') {
            ctx.beginPath();
            for (let i = 0; i < pts.length; i++) {
                const p = pts[i];
                if (i === 0) ctx.moveTo(p.x, p.y);
                else ctx.lineTo(p.x, p.y);
            }
            ctx.stroke();
        } else if (shape.type === 'rect' && pts.length >= 2) {
            const p0 = pts[0], p1 = pts[1];
            ctx.beginPath();
            ctx.strokeRect(p0.x, p0.y, p1.x - p0.x, p1.y - p0.y);
        } else if (shape.type === 'circle' && pts.length >= 2) {
            const p0 = pts[0], p1 = pts[1];
            const dx = p1.x - p0.x, dy = p1.y - p0.y;
            const r = Math.sqrt(dx * dx + dy * dy);
            ctx.beginPath();
            ctx.arc(p0.x, p0.y, r, 0, Math.PI * 2);
            ctx.stroke();
        }
    }

    function redrawAll() {
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.restore();
        state.shapes.forEach(s => drawShape(s));
    }

    function getPos(e) {
        const rect = canvas.getBoundingClientRect();
        return {x: e.clientX - rect.left, y: e.clientY - rect.top};
    }

    function pushLocal(shape) {
        state.shapes.push(shape);
        state.undoStack.push(shape);
        state.redoStack.length = 0;
    }

    function onDown(e) {
        e.preventDefault();
        state.drawing = true;
        const p = getPos(e);
        state.startPoint = p;
        state.currentPoints = [p];
    }

    function onMove(e) {
        if (!state.drawing) return;
        const p = getPos(e);
        if (state.tool === 'pen') {
            state.currentPoints.push(p);
            const last = state.currentPoints[state.currentPoints.length - 2];
            if (last) {
                ctx.strokeStyle = state.color;
                ctx.lineWidth = state.width;
                ctx.lineCap = 'round';
                ctx.lineJoin = 'round';
                ctx.beginPath();
                ctx.moveTo(last.x, last.y);
                ctx.lineTo(p.x, p.y);
                ctx.stroke();
            }
        } else {
            redrawAll();
            drawPreview(p);
        }
    }

    function drawPreview(cur) {
        const s = {
            type: state.tool,
            color: state.color,
            width: state.width,
            points: [state.startPoint, cur]
        };
        ctx.save();
        ctx.globalAlpha = 0.6;
        drawShape(s);
        ctx.restore();
    }

    function onUp(e) {
        if (!state.drawing) return;
        state.drawing = false;
        const pts = state.currentPoints.slice();
        if (pts.length < 2) {
            state.currentPoints = [];
            return;
        }
        const shape = {
            type: state.tool,
            color: state.color,
            width: state.width,
            points: pts,
            _local: true
        };
        pushLocal(shape);
        redrawAll();

        if (state.socketReady) {
            const clientId = Date.now() + '-' + Math.random().toString(36).slice(2, 8);
            shape._clientId = clientId;
            socket.emit('draw', {
                board_id: BOARD_ID,
                type: shape.type,
                color: shape.color,
                width: shape.width,
                points: shape.points,
                client_id: clientId
            });
        }
        state.currentPoints = [];
    }

    canvas.addEventListener('mousedown', onDown);
    canvas.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    canvas.addEventListener('mouseleave', onUp);

    canvas.addEventListener('touchstart', (e) => {
        if (e.touches.length === 1) onDown(e.touches[0]);
    });
    canvas.addEventListener('touchmove', (e) => {
        if (e.touches.length === 1) { e.preventDefault(); onMove(e.touches[0]); }
    }, {passive: false});
    canvas.addEventListener('touchend', onUp);

    document.querySelectorAll('.tool-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.tool = btn.dataset.tool;
        });
    });

    document.querySelectorAll('.color-dot').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.color-dot').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.color = btn.dataset.color;
            document.getElementById('custom-color').value = state.color;
        });
    });

    document.getElementById('custom-color').addEventListener('input', (e) => {
        state.color = e.target.value;
        document.querySelectorAll('.color-dot').forEach(b => b.classList.remove('active'));
    });

    const widthSlider = document.getElementById('width-slider');
    const widthVal = document.getElementById('width-val');
    widthSlider.addEventListener('input', (e) => {
        state.width = parseInt(e.target.value, 10);
        widthVal.textContent = state.width;
    });

    document.getElementById('undo-btn').addEventListener('click', () => {
        if (state.redoStack.length > 0) {
            const shape = state.redoStack.pop();
            state.shapes.push(shape);
            state.undoStack.push(shape);
            redrawAll();
            if (state.socketReady) {
                socket.emit('redo', {board_id: BOARD_ID, shape: {
                    type: shape.type, color: shape.color, width: shape.width, points: shape.points
                }});
            }
            return;
        }
        if (state.undoStack.length > 0) {
            const shape = state.undoStack.pop();
            state.shapes.pop();
            state.redoStack.push(shape);
            redrawAll();
            if (state.socketReady) {
                socket.emit('undo', {board_id: BOARD_ID});
            }
        }
    });

    document.getElementById('redo-btn').addEventListener('click', () => {
        if (state.redoStack.length === 0) return;
        const shape = state.redoStack.pop();
        state.shapes.push(shape);
        state.undoStack.push(shape);
        redrawAll();
        if (state.socketReady) {
            socket.emit('redo', {board_id: BOARD_ID, shape: {
                type: shape.type, color: shape.color, width: shape.width, points: shape.points
            }});
        }
    });

    document.getElementById('clear-btn').addEventListener('click', () => {
        if (!confirm('确定清空整个画布？此操作对所有人可见。')) return;
        state.shapes.length = 0;
        state.undoStack.length = 0;
        state.redoStack.length = 0;
        redrawAll();
        if (state.socketReady) {
            socket.emit('clear_board', {board_id: BOARD_ID});
        }
    });

    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
            e.preventDefault();
            if (e.shiftKey) {
                document.getElementById('redo-btn').click();
            } else {
                document.getElementById('undo-btn').click();
            }
        }
    });

    window.addEventListener('resize', resizeCanvas);

    const socket = io({transports: ['polling', 'websocket']});

    socket.on('connect', () => {
        state.socketReady = true;
        connStatus.textContent = '已连接';
        connStatus.className = 'conn-status connected';
        socket.emit('join_board', {board_id: BOARD_ID});
    });

    socket.on('disconnect', () => {
        state.socketReady = false;
        connStatus.textContent = '已断开';
        connStatus.className = 'conn-status disconnected';
    });

    socket.on('joined', (data) => {
        loadShapes();
    });

    socket.on('draw', (data) => {
        const s = {
            id: data.id,
            type: data.type,
            color: data.color,
            width: data.width,
            points: data.points
        };
        state.shapes.push(s);
        state.undoStack.push(s);
        redrawAll();
    });

    socket.on('undo_applied', (data) => {
        for (let i = state.shapes.length - 1; i >= 0; i--) {
            if (state.shapes[i].id === data.id) {
                state.shapes.splice(i, 1);
                break;
            }
        }
        state.undoStack.length = 0;
        state.redoStack.length = 0;
        state.shapes.forEach(s => state.undoStack.push(s));
        redrawAll();
    });

    socket.on('board_cleared', () => {
        state.shapes.length = 0;
        state.undoStack.length = 0;
        state.redoStack.length = 0;
        redrawAll();
        showToast('画布已清空', 'success');
    });

    socket.on('error', (data) => {
        showToast(data.msg || '发生错误', 'error');
    });

    async function loadShapes() {
        try {
            const res = await fetch('/api/boards/' + BOARD_ID + '/shapes');
            const data = await res.json();
            if (data.ok) {
                state.shapes = data.shapes || [];
                state.undoStack = state.shapes.slice();
                state.redoStack.length = 0;
                redrawAll();
            }
        } catch (err) {
            console.error('加载白板失败', err);
        }
    }

    resizeCanvas();
})();
