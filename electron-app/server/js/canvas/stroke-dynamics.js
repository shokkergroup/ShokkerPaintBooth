(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBStrokeDynamics = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    // SPB-93 tick 45 (2026-07-16), owner verdict: tools need a natural,
    // Photoshop-quality feel. Configured size/opacity are hard maxima; pen
    // pressure tapers toward them, while mouse input stays exactly configured.
    function normalizePressure(value, pointerType) {
        if (String(pointerType || 'mouse').toLowerCase() !== 'pen') return 1;
        const pressure = Number(value);
        if (!Number.isFinite(pressure)) return 0.5;
        return Math.max(0, Math.min(1, pressure));
    }

    function resolveDynamics(options) {
        const opts = options || {};
        const pressure = normalizePressure(opts.pressure, opts.pointerType);
        const baseRadius = Math.max(1, Number(opts.baseRadius) || 1);
        const baseOpacity = Math.max(0, Math.min(1, Number(opts.baseOpacity) || 0));
        const flow = Math.max(0, Math.min(1, Number(opts.flow) || 0));
        const isPen = String(opts.pointerType || 'mouse').toLowerCase() === 'pen';
        if (!isPen) {
            return { pressure: 1, radius: Math.max(1, Math.round(baseRadius)), opacity: baseOpacity * flow };
        }

        const sizeFloor = Math.max(0.01, Math.min(1, Number(opts.sizeFloor) || 0.2));
        const opacityFloor = Math.max(0, Math.min(1, Number(opts.opacityFloor) || 0.04));
        const sizeResponse = sizeFloor + (1 - sizeFloor) * Math.pow(pressure, 0.65);
        const opacityResponse = opacityFloor + (1 - opacityFloor) * Math.pow(pressure, 0.8);
        return {
            pressure,
            radius: Math.max(1, Math.round(baseRadius * sizeResponse)),
            opacity: Math.max(0, Math.min(1, baseOpacity * flow * opacityResponse)),
        };
    }

    function beginStroke(point) {
        if (!point || !Number.isFinite(Number(point.x)) || !Number.isFinite(Number(point.y))) return null;
        return {
            x: Number(point.x),
            y: Number(point.y),
            pressure: Number.isFinite(Number(point.pressure)) ? Number(point.pressure) : 1,
            carry: 0,
        };
    }

    // Distance resampling is independent of browser event frequency. A fast
    // 300px move and thirty 10px moves emit the same evenly spaced dab path.
    function sampleSegment(state, point, spacing) {
        if (!state) return { state: beginStroke(point), points: [] };
        if (!point || !Number.isFinite(Number(point.x)) || !Number.isFinite(Number(point.y))) {
            return { state, points: [] };
        }
        const nextX = Number(point.x);
        const nextY = Number(point.y);
        const nextPressure = Number.isFinite(Number(point.pressure)) ? Number(point.pressure) : state.pressure;
        const step = Math.max(0.25, Number(spacing) || 1);
        const dx = nextX - state.x;
        const dy = nextY - state.y;
        const distance = Math.hypot(dx, dy);
        if (distance < 1e-6) {
            return { state: { x: nextX, y: nextY, pressure: nextPressure, carry: state.carry }, points: [] };
        }

        const priorCarry = Math.max(0, Math.min(step - 1e-6, Number(state.carry) || 0));
        let along = step - priorCarry;
        const points = [];
        while (along <= distance + 1e-7 && points.length < 8192) {
            const t = Math.max(0, Math.min(1, along / distance));
            points.push({
                x: state.x + dx * t,
                y: state.y + dy * t,
                pressure: state.pressure + (nextPressure - state.pressure) * t,
            });
            along += step;
        }
        const emittedDistance = points.length ? (along - step) : 0;
        const carry = points.length ? distance - emittedDistance : priorCarry + distance;
        return {
            state: { x: nextX, y: nextY, pressure: nextPressure, carry: Math.max(0, Math.min(step - 1e-6, carry)) },
            points,
        };
    }

    return Object.freeze({ normalizePressure, resolveDynamics, beginStroke, sampleSegment });
});
