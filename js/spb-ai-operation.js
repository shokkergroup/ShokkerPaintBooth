/* AI/offline14h W10: request ownership survives Cancel and source replacement.
   Document identity comes from the controller; the helper never edits paint. */
(function (root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.SpbAiOperation = factory();
}(typeof window !== 'undefined' ? window : this, function () {
    'use strict';
    function create(readDocument, readRevision) {
        var serial = 0, owner = null;
        function revision() { return readRevision ? readRevision() : null; }
        function snapshotDocument() {
            var source = readDocument(), out = {};
            Object.keys(source || {}).forEach(function (key) { out[key] = source[key]; });
            return out;
        }
        function validDocument(doc) {
            var generation = doc && (doc.sourceGeneration != null ? doc.sourceGeneration : doc.generation);
            return typeof generation === 'number' && isFinite(generation);
        }
        function sameDocument(ticket) {
            if (!ticket || !validDocument(ticket.document)) return false;
            var now = readDocument(), before = ticket.document, keys = Object.keys(before);
            return keys.length === Object.keys(now).length && keys.every(function (key) { return before[key] === now[key]; });
        }
        function owns(ticket) { return !!ticket && owner === ticket; }
        function current(ticket) { return owns(ticket) && !ticket.canceled && sameDocument(ticket) && ticket.revision === revision(); }
        function start(controller) {
            if (owner) owner.canceled = true;
            owner = { id: ++serial, document: snapshotDocument(), revision: revision(), controller: controller || null, canceled: false, phase: 'collecting', collection: 1 };
            return owner;
        }
        function cancel(ticket) {
            ticket = ticket || owner;
            if (!ticket) return false;
            ticket.canceled = true;
            try { if (ticket.controller) ticket.controller.abort(); } catch (e) {}
            return owns(ticket);
        }
        function bind(value, ticket) {
            if (value && typeof value === 'object') Object.defineProperty(value, '_spbOperation', { value: ticket, configurable: true });
            return value;
        }
        function ticketOf(value) { return value && value._spbOperation || null; }
        function collect(ticket) { if (!current(ticket)) return null; ticket.collection++; ticket.phase = 'collecting'; return ticket.collection; }
        function ready(ticket, collection) { if (current(ticket) && (collection == null || collection === ticket.collection)) { ticket.phase = 'ready'; return true; } return false; }
        function collecting(ticket, collection) { return current(ticket) && ticket.phase === 'collecting' && (collection == null || collection === ticket.collection); }
        // Only synchronous controller publication may advance the expected revision.
        // Awaited work must check current() again before entering this function.
        function publish(ticket, fn) {
            if (!current(ticket)) return { refused: true };
            var value = fn();
            if (!sameDocument(ticket) || !owns(ticket) || ticket.canceled) return { refused: true };
            ticket.revision = revision();
            return { value: value, refused: false };
        }
        // Cancel may restore its own preview, but never a replacement document or
        // a newer request/manual revision. Restoration is synchronous as above.
        function restore(ticket, fn) {
            if (!owns(ticket) || !sameDocument(ticket) || ticket.revision !== revision()) return { refused: true };
            var value = fn();
            if (owns(ticket) && sameDocument(ticket)) ticket.revision = revision();
            return { value: value, refused: false };
        }
        return { start: start, owns: owns, current: current, sameDocument: sameDocument, cancel: cancel, bind: bind, ticketOf: ticketOf,
            ready: ready, collecting: collecting, collect: collect, publish: publish, restore: restore, owner: function () { return owner; } };
    }
    return { create: create };
}));
