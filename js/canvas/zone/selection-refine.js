(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBSelectionRefine = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    function dimensions(widthValue, heightValue, mask) {
        const width = Math.max(0, Math.floor(Number(widthValue) || 0));
        const height = Math.max(0, Math.floor(Number(heightValue) || 0));
        const size = width * height;
        if (!mask || mask.length < size) throw new RangeError('Selection mask does not match its canvas');
        return { width, height, size };
    }

    function radiusValue(value) {
        return Math.max(1, Math.min(64, Math.floor(Number(value) || 1)));
    }

    function countSelected(mask) {
        let count = 0;
        for (let index = 0; mask && index < mask.length; index++) {
            if (mask[index] > 0) count++;
        }
        return count;
    }

    function compareMasks(before, after) {
        if (!before || !after || before.length !== after.length) {
            return { changedPixels: Infinity, selectedPixels: countSelected(after), softPixels: 0 };
        }
        let changedPixels = 0;
        let selectedPixels = 0;
        let softPixels = 0;
        for (let index = 0; index < after.length; index++) {
            const value = after[index];
            if (before[index] !== value) changedPixels++;
            if (value > 0) selectedPixels++;
            if (value > 0 && value < 255) softPixels++;
        }
        return { changedPixels, selectedPixels, softPixels };
    }

    function filterLine(source, target, start, stride, length, radius, keepMaximum, queueIndices, queueValues) {
        let head = 0;
        let tail = 0;
        for (let position = -radius; position < length + radius; position++) {
            const value = position >= 0 && position < length ? source[start + position * stride] : 0;
            while (tail > head && (keepMaximum
                ? queueValues[tail - 1] <= value
                : queueValues[tail - 1] >= value)) {
                tail--;
            }
            queueIndices[tail] = position;
            queueValues[tail] = value;
            tail++;

            const firstAllowed = position - radius * 2;
            while (tail > head && queueIndices[head] < firstAllowed) head++;
            const outputPosition = position - radius;
            if (outputPosition >= 0 && outputPosition < length) {
                target[start + outputPosition * stride] = queueValues[head];
            }
        }
    }

    function filterAxis(source, target, width, height, radius, keepMaximum, vertical) {
        const length = vertical ? height : width;
        const lines = vertical ? width : height;
        const stride = vertical ? width : 1;
        const queueIndices = new Int32Array(length + radius * 2 + 1);
        const queueValues = new Uint8Array(length + radius * 2 + 1);
        for (let line = 0; line < lines; line++) {
            const start = vertical ? line : line * width;
            filterLine(source, target, start, stride, length, radius, keepMaximum, queueIndices, queueValues);
        }
    }

    // SPB-93 tick 29, owner verdict: selection tools still felt "jinky/off."
    // The served 2048-square baseline scanned the whole canvas once per radius,
    // took 580 ms on a full-mask Grow 2, claimed success, and added a fake undo.
    // A separable monotonic-window max/min filter is O(canvas pixels), preserves
    // soft mask values, and reports the candidate before any history mutation.
    function morph(mask, widthValue, heightValue, radiusInput, modeInput) {
        const { width, height, size } = dimensions(widthValue, heightValue, mask);
        const radius = radiusValue(radiusInput);
        const mode = modeInput === 'shrink' ? 'shrink' : 'grow';
        let minimum = 255;
        let maximum = 0;
        for (let index = 0; index < size; index++) {
            const value = mask[index];
            if (value < minimum) minimum = value;
            if (value > maximum) maximum = value;
        }
        if (size === 0 || maximum === 0 || (mode === 'grow' && minimum === 255)) {
            return {
                mask: new Uint8Array(mask.slice(0, size)), mode, radius,
                changedPixels: 0,
                selectedPixels: maximum === 0 ? 0 : size,
                softPixels: 0,
            };
        }

        const intermediate = new Uint8Array(size);
        const output = new Uint8Array(size);
        const keepMaximum = mode === 'grow';
        filterAxis(mask, intermediate, width, height, radius, keepMaximum, false);
        filterAxis(intermediate, output, width, height, radius, keepMaximum, true);
        return { mask: output, mode, radius, ...compareMasks(mask, output) };
    }

    function fillHoles(mask, widthValue, heightValue) {
        const { width, height, size } = dimensions(widthValue, heightValue, mask);
        const output = new Uint8Array(mask.slice(0, size));
        const visited = new Uint8Array(size);
        const queue = new Int32Array(size);
        let head = 0;
        let tail = 0;

        function enqueue(index) {
            if (index < 0 || index >= size || visited[index] || mask[index] !== 0) return;
            visited[index] = 1;
            queue[tail++] = index;
        }

        if (width && height) {
            for (let x = 0; x < width; x++) {
                enqueue(x);
                enqueue((height - 1) * width + x);
            }
            for (let y = 0; y < height; y++) {
                enqueue(y * width);
                enqueue(y * width + width - 1);
            }
        }

        while (head < tail) {
            const index = queue[head++];
            const x = index % width;
            if (x > 0) enqueue(index - 1);
            if (x + 1 < width) enqueue(index + 1);
            if (index >= width) enqueue(index - width);
            if (index + width < size) enqueue(index + width);
        }

        let filledPixels = 0;
        let selectedPixels = 0;
        for (let index = 0; index < size; index++) {
            if (output[index] === 0 && !visited[index]) {
                output[index] = 255;
                filledPixels++;
            }
            if (output[index] > 0) selectedPixels++;
        }
        return {
            mask: output,
            changedPixels: filledPixels,
            filledPixels,
            selectedPixels,
            softPixels: 0,
        };
    }

    function boxBlur(source, width, height, radius, horizontal, target) {
        const windowSize = radius * 2 + 1;
        if (horizontal) {
            for (let y = 0; y < height; y++) {
                const row = y * width;
                let sum = 0;
                for (let sample = 0; sample <= radius && sample < width; sample++) sum += source[row + sample];
                for (let x = 0; x < width; x++) {
                    target[row + x] = Math.round(sum / windowSize);
                    const removeX = x - radius;
                    const addX = x + radius + 1;
                    if (removeX >= 0) sum -= source[row + removeX];
                    if (addX < width) sum += source[row + addX];
                }
            }
            return;
        }
        for (let x = 0; x < width; x++) {
            let sum = 0;
            for (let sample = 0; sample <= radius && sample < height; sample++) sum += source[sample * width + x];
            for (let y = 0; y < height; y++) {
                const index = y * width + x;
                target[index] = Math.round(sum / windowSize);
                const removeY = y - radius;
                const addY = y + radius + 1;
                if (removeY >= 0) sum -= source[removeY * width + x];
                if (addY < height) sum += source[addY * width + x];
            }
        }
    }

    function gaussianBoxRadii(radius) {
        const passes = 3;
        const ideal = Math.sqrt((12 * radius * radius / passes) + 1);
        let lower = Math.floor(ideal);
        if (lower % 2 === 0) lower--;
        lower = Math.max(1, lower);
        const upper = lower + 2;
        const lowerCount = Math.max(0, Math.min(passes, Math.round(
            (12 * radius * radius - passes * lower * lower - 4 * passes * lower - 3 * passes) /
            (-4 * lower - 4)
        )));
        const radii = [];
        for (let pass = 0; pass < passes; pass++) {
            radii.push(((pass < lowerCount ? lower : upper) - 1) / 2);
        }
        return radii;
    }

    function feather(mask, widthValue, heightValue, radiusInput) {
        const { width, height, size } = dimensions(widthValue, heightValue, mask);
        const radius = Math.max(1, Math.min(12, Math.floor(Number(radiusInput) || 2)));
        let maximum = 0;
        for (let index = 0; index < size; index++) maximum = Math.max(maximum, mask[index]);
        if (!size || maximum === 0) {
            return { mask: new Uint8Array(mask.slice(0, size)), radius, changedPixels: 0, selectedPixels: 0, softPixels: 0 };
        }
        let current = new Uint8Array(mask.slice(0, size));
        const horizontal = new Uint8Array(size);
        let output = new Uint8Array(size);
        for (const passRadius of gaussianBoxRadii(radius)) {
            boxBlur(current, width, height, passRadius, true, horizontal);
            boxBlur(horizontal, width, height, passRadius, false, output);
            current = output;
            output = new Uint8Array(size);
        }
        return { mask: current, radius, ...compareMasks(mask, current) };
    }

    function smooth(mask, widthValue, heightValue) {
        const { width, height } = dimensions(widthValue, heightValue, mask);
        const shrunk = morph(mask, width, height, 1, 'shrink');
        const grown = morph(shrunk.mask, width, height, 1, 'grow');
        return { mask: grown.mask, ...compareMasks(mask, grown.mask) };
    }

    return { countSelected, compareMasks, morph, fillHoles, feather, smooth };
});
