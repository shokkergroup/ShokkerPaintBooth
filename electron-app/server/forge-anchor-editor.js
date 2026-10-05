(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.ForgeAnchorGeometry = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const EDITABLE_FIELDS = Object.freeze({
    left: ['body_top_y'],
    right: ['body_top_y'],
    top: ['hood_quad', 'roof_quad', 'rear_deck_quad'],
    front: ['hood_seam_y'],
    rear: ['spoiler_outside_quad'],
    front_corner_left: ['front_corner_left_quad'],
    front_corner_right: ['front_corner_right_quad'],
    rear_inside: ['spoiler_inside_quad']
  });

  function finiteNumber(value) {
    return typeof value === 'number' && Number.isFinite(value);
  }

  function clamp01(value) {
    return Math.max(0, Math.min(1, Number(value)));
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function proposalValues(proposal) {
    const values = {};
    Object.entries((proposal && proposal.fields) || {}).forEach(([name, field]) => {
      if (field && field.value != null) values[name] = clone(field.value);
    });
    return values;
  }

  function editableFields(role, proposal) {
    const allowed = new Set(EDITABLE_FIELDS[role] || []);
    return Object.entries((proposal && proposal.fields) || {})
      .filter(([name, field]) => allowed.has(name) && field && field.value != null && field.status === 'review')
      .map(([name]) => name);
  }

  function normalizedBox(raw) {
    const fallback = [0, 0, 1, 1];
    if (!Array.isArray(raw) || raw.length !== 4 || !raw.every(finiteNumber)) return fallback;
    const x0 = clamp01(Math.min(raw[0], raw[2]));
    const y0 = clamp01(Math.min(raw[1], raw[3]));
    const x1 = clamp01(Math.max(raw[0], raw[2]));
    const y1 = clamp01(Math.max(raw[1], raw[3]));
    return x1 - x0 >= 0.02 && y1 - y0 >= 0.02 ? [x0, y0, x1, y1] : fallback;
  }

  function polygonArea(points) {
    let twice = 0;
    for (let index = 0; index < points.length; index += 1) {
      const next = points[(index + 1) % points.length];
      twice += points[index][0] * next[1] - next[0] * points[index][1];
    }
    return twice / 2;
  }

  function validateQuad(value, box, label) {
    const errors = [];
    if (!Array.isArray(value) || value.length !== 4) return [`${label} must have four ordered points`];
    if (!value.every((point) => Array.isArray(point) && point.length === 2 && point.every(finiteNumber))) {
      return [`${label} contains an invalid point`];
    }
    const [x0, y0, x1, y1] = box;
    value.forEach((point) => {
      if (point[0] < 0 || point[0] > 1 || point[1] < 0 || point[1] > 1) errors.push(`${label} must stay inside the source image`);
      if (point[0] < x0 - 0.035 || point[0] > x1 + 0.035 || point[1] < y0 - 0.035 || point[1] > y1 + 0.035) {
        errors.push(`${label} must stay on the measured car`);
      }
    });
    const area = polygonArea(value);
    if (area < 0.005) errors.push(`${label} is too small, reversed, or folded`);
    const signs = [];
    for (let index = 0; index < 4; index += 1) {
      const a = value[index];
      const b = value[(index + 1) % 4];
      const c = value[(index + 2) % 4];
      const cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]);
      if (Math.abs(cross) > 0.00001) signs.push(Math.sign(cross));
    }
    if (signs.length < 4 || signs.some((sign) => sign !== signs[0])) errors.push(`${label} points must stay ordered and convex`);
    return [...new Set(errors)];
  }

  function quadCenterX(quad) {
    return quad.reduce((sum, point) => sum + point[0], 0) / quad.length;
  }

  function validate(role, values, primaryObjectBox) {
    const errors = [];
    const box = normalizedBox(primaryObjectBox);
    const [x0, y0, x1, y1] = box;
    const height = y1 - y0;
    if (role === 'left' || role === 'right') {
      const top = values.body_top_y;
      if (!finiteNumber(top) || top < y0 || top > y1) errors.push('body top must stay inside the measured side body');
      if (finiteNumber(values.rocker_y) && finiteNumber(top) && top >= values.rocker_y - 0.02) errors.push('body top must remain above the rocker');
    } else if (role === 'front') {
      const seam = values.hood_seam_y;
      if (!finiteNumber(seam) || seam < y0 + height * 0.08 || seam > y1) errors.push('hood seam must stay inside the measured front body');
      if (finiteNumber(values.ground_y) && finiteNumber(seam) && seam >= values.ground_y - 0.025) errors.push('hood seam must remain above ground contact');
    } else if (role === 'top') {
      const names = ['hood_quad', 'roof_quad', 'rear_deck_quad'];
      names.forEach((name) => errors.push(...validateQuad(values[name], box, name.replaceAll('_', ' '))));
      if (names.every((name) => Array.isArray(values[name]) && values[name].length === 4)) {
        const centers = names.map((name) => quadCenterX(values[name]));
        const increasing = centers[0] + 0.02 < centers[1] && centers[1] + 0.02 < centers[2];
        const decreasing = centers[2] + 0.02 < centers[1] && centers[1] + 0.02 < centers[0];
        if (!increasing && !decreasing) errors.push('hood, roof, and rear deck must keep a consistent physical order');
      }
    } else if (role === 'rear') {
      errors.push(...validateQuad(values.spoiler_outside_quad, box, 'spoiler outside quad'));
    } else if (role === 'front_corner_left') {
      errors.push(...validateQuad(values.front_corner_left_quad, box, 'front corner left quad'));
    } else if (role === 'front_corner_right') {
      errors.push(...validateQuad(values.front_corner_right_quad, box, 'front corner right quad'));
    } else if (role === 'rear_inside') {
      errors.push(...validateQuad(values.spoiler_inside_quad, box, 'spoiler inside quad'));
    } else {
      errors.push('unsupported anchor role');
    }
    return { valid: errors.length === 0, errors: [...new Set(errors)], box: [x0, y0, x1, y1] };
  }

  function moveScalar(values, field, y) {
    const next = clone(values);
    next[field] = clamp01(y);
    return next;
  }

  function moveQuadPoint(values, field, index, x, y) {
    const next = clone(values);
    if (!Array.isArray(next[field]) || index < 0 || index >= next[field].length) return next;
    next[field][index] = [clamp01(x), clamp01(y)];
    return next;
  }

  function confirmationValues(role, values) {
    if (role !== 'rear') return clone(values);
    return values.spoiler_outside_quad == null
      ? {}
      : { spoiler_outside_quad: clone(values.spoiler_outside_quad) };
  }

  return Object.freeze({
    EDITABLE_FIELDS,
    clamp01,
    editableFields,
    normalizedBox,
    polygonArea,
    proposalValues,
    validate,
    moveScalar,
    moveQuadPoint,
    confirmationValues
  });
}));
