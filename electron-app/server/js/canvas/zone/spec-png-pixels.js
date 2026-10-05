(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBSpecPngPixels = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';
    // SPB-93 09-08: canvas PNG readback premultiplies alpha. A saved material
    // [0,100,110,0] became [0,0,0,0]. Decode compiled 8-bit RGB/RGBA PNG bytes.
    function paeth(a, b, c) {
        const p = a + b - c, x = Math.abs(p - a), y = Math.abs(p - b), z = Math.abs(p - c);
        return x <= y && x <= z ? a : y <= z ? b : c;
    }
    async function decode(buffer) {
        const bytes = new Uint8Array(buffer), view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
        if (bytes.length < 33 || ![137,80,78,71,13,10,26,10].every((v,i) => bytes[i] === v)) throw Error('Invalid spec PNG');
        let width = 0, height = 0, channels = 0;
        const chunks = [];
        for (let offset = 8; offset + 12 <= bytes.length;) {
            const length = view.getUint32(offset), end = offset + 12 + length;
            if (end > bytes.length) throw Error('Truncated spec PNG');
            const type = String.fromCharCode(...bytes.subarray(offset + 4, offset + 8));
            const data = offset + 8;
            if (type === 'IHDR') {
                width = view.getUint32(data); height = view.getUint32(data + 4);
                const color = bytes[data + 9];
                if (length !== 13 || bytes[data + 8] !== 8 || ![2,6].includes(color)
                        || bytes[data + 10] || bytes[data + 11] || bytes[data + 12]
                        || !width || !height || width * height > 67108864) throw Error('Unsupported compiled spec PNG format');
                channels = color === 6 ? 4 : 3;
            } else if (type === 'IDAT') chunks.push(bytes.subarray(data, data + length));
            else if (type === 'tRNS') throw Error('Unsupported spec PNG transparency format');
            if (type === 'IEND') break;
            offset = end;
        }
        if (!channels || !chunks.length) throw Error('Incomplete spec PNG');
        const stream = new Blob(chunks).stream().pipeThrough(new DecompressionStream('deflate'));
        const scan = new Uint8Array(await new Response(stream).arrayBuffer());
        const stride = width * channels;
        if (scan.length !== (stride + 1) * height) throw Error('Spec PNG scanline size mismatch');
        const raw = new Uint8Array(stride * height);
        for (let y = 0; y < height; y++) {
            const row = y * stride, input = y * (stride + 1), filter = scan[input];
            if (filter > 4) throw Error('Invalid spec PNG filter');
            for (let x = 0; x < stride; x++) {
                const a = x >= channels ? raw[row + x - channels] : 0;
                const b = y ? raw[row + x - stride] : 0;
                const c = y && x >= channels ? raw[row + x - stride - channels] : 0;
                const prediction = filter === 1 ? a : filter === 2 ? b : filter === 3 ? Math.floor((a + b) / 2) : filter === 4 ? paeth(a,b,c) : 0;
                raw[row + x] = (scan[input + 1 + x] + prediction) & 255;
            }
        }
        const data = new Uint8ClampedArray(width * height * 4);
        if (channels === 4) data.set(raw);
        else for (let i = 0, j = 0; i < raw.length; i += 3, j += 4) {
            data[j] = raw[i]; data[j+1] = raw[i+1]; data[j+2] = raw[i+2]; data[j+3] = 255;
        }
        return {width, height, data};
    }
    let cachedSource = '', cachedPromise = null;
    function load(source) {
        if (source === cachedSource && cachedPromise) return cachedPromise;
        cachedSource = source;
        const pending = fetch(source).then(response => {
            if (!response.ok) throw Error('Could not load compiled spec pixels');
            return response.arrayBuffer();
        }).then(decode);
        cachedPromise = pending;
        pending.catch(() => { if (cachedPromise === pending) cachedPromise = null; });
        return pending;
    }
    return {decode, load};
});
