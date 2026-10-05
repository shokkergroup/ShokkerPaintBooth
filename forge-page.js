(function () {
  'use strict';

  const INTERNAL_HEADERS = { 'X-Shokker-Internal': '1' };
  const requiredRoles = ['left', 'right', 'top', 'front', 'rear'];
  const state = { adapter: null, job: null, files: new Map(), editor: null };
  const byId = (id) => document.getElementById(id);
  const anchorGeometry = window.ForgeAnchorGeometry;

  async function api(path, options) {
    const opts = Object.assign({}, options || {});
    opts.headers = Object.assign({}, INTERNAL_HEADERS, opts.headers || {});
    const response = await fetch(path, opts);
    const body = await response.json().catch(() => ({}));
    if (!response.ok && response.status !== 409) throw new Error(body.error || `Forge request failed (${response.status})`);
    return { response, body };
  }

  function captureQualityText(quality) {
    if (!quality) return 'QUALITY METRICS UNAVAILABLE';
    const warnings = Array.isArray(quality.warnings) ? quality.warnings.length : 0;
    return `${Number(quality.width || 0)}x${Number(quality.height || 0)} / ${Number(quality.megapixels || 0).toFixed(2)} MP / ${quality.admissible ? 'ADMISSIBLE' : 'REJECTED'} / ${warnings} REVIEW WARNING${warnings === 1 ? '' : 'S'}`;
  }

  async function hydrateEvidenceImage(image, referenceId) {
    const response = await fetch(`/api/forge/jobs/${state.job.job_id}/references/${referenceId}/content`, { headers: INTERNAL_HEADERS });
    if (!response.ok) throw new Error(`Forge could not load comparison source ${referenceId} (${response.status})`);
    const objectUrl = URL.createObjectURL(await response.blob());
    image.onload = () => URL.revokeObjectURL(objectUrl);
    image.src = objectUrl;
  }

  function buildEvidenceComparison(request) {
    const comparison = document.createElement('div');
    comparison.className = 'evidence-comparison';
    comparison.dataset.currentReferenceId = request.selected_reference_id;
    comparison.dataset.candidateReferenceId = request.replacement_candidate_reference_id;
    [
      ['CURRENT AUTHORITY', request.selected_reference_id, request.capture_quality],
      ['NEW CANDIDATE', request.replacement_candidate_reference_id, request.replacement_candidate_capture_quality]
    ].forEach(([label, referenceId, quality]) => {
      const figure = document.createElement('figure');
      const image = document.createElement('img');
      image.alt = `${label.toLowerCase()} direct physical-surface evidence`;
      const caption = document.createElement('figcaption');
      const title = document.createElement('b');
      const metrics = document.createElement('small');
      title.textContent = label;
      metrics.textContent = captureQualityText(quality);
      caption.append(title, metrics);
      figure.append(image, caption);
      comparison.appendChild(figure);
      hydrateEvidenceImage(image, referenceId).catch((error) => {
        metrics.textContent = `IMAGE LOAD FAILED / ${error.message}`;
      });
    });
    return comparison;
  }

  function updateCoverage() {
    const count = requiredRoles.filter((role) => state.files.has(role)).length;
    byId('coverageNumber').textContent = `${count}/5`;
    byId('coverageDetail').textContent = 'required views selected';
    byId('coverageBar').style.width = `${count * 20}%`;
    byId('coverageLabel').textContent = count === 5 ? 'READY TO QUALIFY' : 'NEEDS INPUT';
    byId('coverageLabel').style.color = count === 5 ? 'var(--green)' : 'var(--yellow)';
    byId('qualifyButton').disabled = !(state.adapter && count === 5);
  }

  function bindInputs() {
    document.querySelectorAll('.view-slot').forEach((slot) => {
      const input = slot.querySelector('input');
      const role = slot.dataset.role;
      input.addEventListener('change', () => {
        if (input.files && input.files[0]) {
          state.files.set(role, input.files[0]);
          slot.classList.add('selected');
          slot.querySelector('em').textContent = input.files[0].name;
        } else {
          state.files.delete(role);
          slot.classList.remove('selected');
          slot.querySelector('em').textContent = 'Choose image';
        }
        updateCoverage();
      });
    });
    byId('optionalFiles').addEventListener('change', (event) => {
      const count = event.target.files ? event.target.files.length : 0;
      byId('optionalLabel').textContent = count ? `${count} file${count === 1 ? '' : 's'} selected` : 'Choose files';
    });
  }

  async function loadAdapters() {
    try {
      const { body } = await api('/api/forge/adapters');
      state.adapter = (body.adapters || []).find((item) => item.id === 'iracing.dirt_late_model') || null;
      if (!state.adapter) throw new Error('Dirt Late Model adapter is not installed');
      byId('adapterVersion').textContent = `Adapter v${state.adapter.version} · ${state.adapter.adapter_sha256.slice(0, 12)}`;
      byId('adapterStatus').textContent = state.adapter.capabilities.full_nose_inverse ? 'FULL' : 'GUIDED / ABSTAINS';
      byId('connectionPill').textContent = 'LOCAL SERVICE ONLINE';
      byId('connectionPill').className = 'pill online';
      updateCoverage();
    } catch (error) {
      byId('adapterStatus').textContent = 'UNAVAILABLE';
      byId('connectionPill').textContent = 'SERVICE OFFLINE';
      byId('connectionPill').className = 'pill error';
      showJobError(error);
    }
  }

  function renderQualification(report) {
    const present = new Set(report.present_roles || []);
    const directCount = requiredRoles.filter((role) => present.has(role)).length;
    byId('coverageNumber').textContent = `${directCount}/5`;
    byId('coverageDetail').textContent = 'required views stored';
    byId('coverageBar').style.width = `${directCount * 20}%`;
    byId('coverageLabel').textContent = report.qualified ? 'QUALIFIED' : 'NEEDS INPUT';
    byId('coverageLabel').style.color = report.qualified ? 'var(--green)' : 'var(--yellow)';
    byId('qualificationGrid').innerHTML = requiredRoles.map((role) =>
      `<div class="${present.has(role) ? 'pass' : 'fail'}">${role.toUpperCase()} · ${present.has(role) ? 'DIRECT' : 'MISSING'}</div>`
    ).join('');
  }

  function renderPipeline(job) {
    const labels = {
      intake: 'INTAKE', geometry: 'GEOMETRY', projection: 'PROJECTION',
      semantics: 'LAYERS', compile: 'COMPILE', qa: 'QA'
    };
    const stages = job.stages || {};
    byId('pipelineGrid').innerHTML = Object.keys(labels).map((key) => {
      const status = (stages[key] && stages[key].status) || 'pending';
      return `<div class="${status}"><span>${labels[key]}</span><b>${String(status).replace('_', ' ').toUpperCase()}</b></div>`;
    }).join('');

    document.querySelectorAll('.stage-rail [data-stage]').forEach((node) => {
      const key = node.dataset.stage;
      const stageKey = key === 'import' ? null : key;
      const status = key === 'import'
        ? (job.state === 'imported' ? 'complete' : (job.state === 'ready' ? 'current' : 'pending'))
        : ((stages[stageKey] && stages[stageKey].status) || 'pending');
      node.className = status === 'complete' ? 'complete' : (status === 'needs_input' ? 'blocked' : (status === 'pending' ? '' : 'active'));
    });

    renderSurfaceExecutions(job);
    renderAnchorProposals(job);
    renderSurfaceReadiness(job);
    renderEvidenceRequests(job);
    const corrections = (job.last_run && job.last_run.required_corrections) || [];
    byId('correctionPanel').hidden = corrections.length === 0;
    const list = byId('correctionList');
    list.replaceChildren();
    corrections.forEach((item) => {
      const row = document.createElement('li');
      const fields = Array.isArray(item.fields) && item.fields.length ? `: ${item.fields.join(', ')}` : '';
      row.textContent = `${String(item.scope || 'job').toUpperCase()} — ${String(item.reason || 'unresolved').replaceAll('_', ' ')}${fields}`;
      list.appendChild(row);
    });
  }

  function renderSurfaceReadiness(job) {
    const readiness = job.surface_readiness || {};
    const roles = Array.isArray(readiness.roles) ? readiness.roles : [];
    const panel = byId('surfaceReadinessPanel');
    const grid = byId('surfaceReadinessGrid');
    panel.hidden = roles.length === 0;
    grid.replaceChildren();
    roles.forEach((row) => {
      const card = document.createElement('article');
      card.className = `surface-readiness-card ${row.state || 'not_requested'}`;
      const header = document.createElement('header');
      const title = document.createElement('b');
      const stateLabel = document.createElement('span');
      title.textContent = String(row.role || 'surface').replaceAll('_', ' ').toUpperCase();
      stateLabel.textContent = String(row.state || 'not_requested').replaceAll('_', ' ').toUpperCase();
      header.append(title, stateLabel);
      const scope = document.createElement('code');
      scope.textContent = `${row.surface || 'surface'} / ${String(row.physical_scope || '').replaceAll('_', ' ')}`;
      const steps = document.createElement('ol');
      const attestation = row.attestation_confirmed ? 'CONFIRMED' : (row.capture_status === 'low_confidence' ? 'ACTION REQUIRED' : 'LOCKED');
      const review = row.review_status === 'confirmed' ? `CONFIRMED REV ${Number(row.review_revision || 1)}` : String(row.review_status || 'locked').replaceAll('_', ' ').toUpperCase();
      [
        ['1 DIRECT CAPTURE', String(row.capture_status || 'not requested').replaceAll('_', ' ').toUpperCase()],
        ['2 ATTESTATION', attestation],
        ['3 SURFACE REVIEW', review],
        ['4 SPECIALIZED PROJECTION', row.specialized_projection_executable ? 'EXECUTABLE' : 'ABSTAINED']
      ].forEach(([label, value]) => {
        const item = document.createElement('li');
        const stepLabel = document.createElement('span');
        const stepValue = document.createElement('b');
        stepLabel.textContent = label;
        stepValue.textContent = value;
        item.append(stepLabel, stepValue);
        steps.appendChild(item);
      });
      const action = document.createElement('p');
      action.textContent = row.next_action || 'No action requested.';
      const ownership = document.createElement('small');
      ownership.textContent = `NEXT OWNER: ${String(row.responsible_party || 'none').replaceAll('_', ' ').toUpperCase()} / GENERIC SUBSTITUTION: PROHIBITED`;
      card.append(header, scope, steps, action, ownership);
      grid.appendChild(card);
    });
    const summary = readiness.summary || {};
    const adapterAuthority = summary.adapter_refresh_required ? 'ADAPTER REFRESH REQUIRED' : 'ADAPTER AUTHORITY MATCHED';
    byId('surfaceReadinessSummary').textContent = `${Number(summary.requested_count || 0)} REQUESTED / ${Number(summary.owner_action_count || 0)} OWNER ACTIONS / ${Number(summary.evidence_ready_count || 0)} REVIEWED BUT PROJECTOR-BLOCKED / SPECIALIZED EXECUTABLE 0 / ${adapterAuthority} / PSD IMPORT LOCKED`;
  }

  async function exportSurfaceReadiness() {
    if (!state.job) return;
    const response = await fetch(`/api/forge/jobs/${state.job.job_id}/surface-readiness/export`, { headers: INTERNAL_HEADERS });
    if (!response.ok) throw new Error(`Forge could not export the correction checklist (${response.status})`);
    const objectUrl = URL.createObjectURL(await response.blob());
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = `forge-${state.job.job_id}-surface-corrections.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(objectUrl);
  }

  function renderEvidenceRequests(job) {
    const persisted = Array.isArray(job.evidence_requests) ? job.evidence_requests : [];
    const report = job.last_run && job.last_run.evidence_requests;
    const requests = persisted.length ? persisted : ((report && report.requests) || []);
    const panel = byId('evidenceRequestPanel');
    const grid = byId('evidenceRequestGrid');
    panel.hidden = requests.length === 0;
    grid.replaceChildren();
    requests.forEach((request) => {
      const card = document.createElement('article');
      card.className = `evidence-request-card ${request.status || 'requested'}`;
      const header = document.createElement('header');
      const title = document.createElement('b');
      const status = document.createElement('span');
      title.textContent = String(request.role || 'optional evidence').replaceAll('_', ' ').toUpperCase();
      status.textContent = String(request.status || 'requested').replaceAll('_', ' ').toUpperCase();
      header.append(title, status);
      const scope = document.createElement('code');
      scope.textContent = `${request.surface || 'surface'} / ${String(request.physical_scope || 'direct physical face').replaceAll('_', ' ')}`;
      const guidance = document.createElement('p');
      guidance.textContent = request.capture_guidance || 'Supply a unique direct image of this physical surface.';
      const guard = document.createElement('small');
      const substitutes = (request.prohibited_substitute_roles || []).join(', ');
      guard.textContent = `Minimum role confidence ${Number(request.minimum_confidence || 0).toFixed(2)}. Rejected substitutes: ${substitutes || 'none declared'}.`;
      card.append(header, scope, guidance, guard);
      if (request.qualified) {
        const accepted = document.createElement('strong');
        accepted.textContent = `DIRECT EVIDENCE QUALIFIED / ${String(request.qualified_reference_id || '').toUpperCase()}`;
        card.appendChild(accepted);
        if (request.review_status === 'confirmed') {
          const reviewed = document.createElement('strong');
          reviewed.textContent = `SURFACE QUAD CONFIRMED / REVISION ${Number((request.surface_review || {}).revision || request.review_revision_count || 1)} / ${String((request.surface_review || {}).anchor_field || '').replaceAll('_', ' ').toUpperCase()}`;
          card.appendChild(reviewed);
        } else if (request.review_ready && request.review_contract) {
          const review = document.createElement('button');
          review.type = 'button';
          review.className = 'evidence-confirm';
          review.dataset.evidenceReviewRole = request.role;
          review.textContent = 'REVIEW FOUR PHYSICAL-SURFACE CORNERS';
          card.appendChild(review);
        }
        if (request.replacement_candidate_reference_id) {
          card.appendChild(buildEvidenceComparison(request));
          const replace = document.createElement('button');
          replace.type = 'button';
          replace.className = 'evidence-confirm';
          replace.dataset.evidenceConfirmRole = request.role;
          replace.dataset.evidenceReferenceId = request.replacement_candidate_reference_id;
          replace.textContent = 'CONFIRM NEW PHOTO AND SUPERSEDE CURRENT REVIEW';
          card.appendChild(replace);
        }
        if (Number(request.capture_rejected_count || 0) > 0) {
          const rejected = document.createElement('strong');
          rejected.className = 'capture-rejection';
          const failures = ((request.latest_capture_rejection || {}).hard_failures || []).join(', ').replaceAll('_', ' ');
          rejected.textContent = `LATEST REPLACEMENT REJECTED / ${failures || 'CAPTURE INTEGRITY FAILED'}`;
          card.appendChild(rejected);
        }
        const lineage = document.createElement('small');
        lineage.textContent = `Selected source revision ${Number(request.selection_revision || 1)} / ${Number(request.superseded_review_count || 0)} preserved superseded review${Number(request.superseded_review_count || 0) === 1 ? '' : 's'}.`;
        card.appendChild(lineage);
        const replacementUpload = document.createElement('label');
        replacementUpload.className = 'evidence-upload';
        replacementUpload.textContent = 'ADD A UNIQUE REPLACEMENT DIRECT VIEW';
        const replacementInput = document.createElement('input');
        replacementInput.type = 'file';
        replacementInput.accept = 'image/*,.tga';
        replacementInput.dataset.evidenceRole = request.role;
        replacementUpload.appendChild(replacementInput);
        card.appendChild(replacementUpload);
      } else if (request.status === 'low_confidence' && request.qualified_reference_id) {
        const confirm = document.createElement('button');
        confirm.type = 'button';
        confirm.className = 'evidence-confirm';
        confirm.dataset.evidenceConfirmRole = request.role;
        confirm.dataset.evidenceReferenceId = request.qualified_reference_id;
        confirm.textContent = 'I CONFIRM THIS PHOTO MATCHES THE CAPTURE CONTRACT';
        card.appendChild(confirm);
      } else {
        const label = document.createElement('label');
        label.className = 'evidence-upload';
        label.textContent = request.status === 'duplicate' ? 'REPLACE DUPLICATE WITH UNIQUE IMAGE' : 'UPLOAD THIS DIRECT VIEW';
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*,.tga';
        input.dataset.evidenceRole = request.role;
        label.appendChild(input);
        card.appendChild(label);
      }
      grid.appendChild(card);
    });
    const summary = (report && report.summary) || {};
    panel.dataset.summary = `${requests.length} requested / ${Number(summary.qualified_count || requests.filter((row) => row.qualified).length)} qualified / ${Number(summary.replacement_candidate_count || 0)} pending replacements / ${Number(summary.capture_rejected_count || 0)} rejected captures / ${Number(summary.superseded_review_count || 0)} preserved reviews / unsafe substitutions accepted 0`;
  }

  async function uploadRequestedEvidence(role, file) {
    if (!state.job || !file) return;
    byId('jobMessage').textContent = `Hashing unique ${String(role).replaceAll('_', ' ')} evidence and re-qualifying the resumable job...`;
    const form = new FormData();
    form.append('roles', role);
    form.append('files', file);
    const uploaded = await api(`/api/forge/jobs/${state.job.job_id}/references`, { method: 'POST', body: form });
    state.job = uploaded.body.job;
    const qualified = await api(`/api/forge/jobs/${state.job.job_id}/qualify`, { method: 'POST' });
    state.job = qualified.body.job;
    renderPersistedJob(state.job);
  }

  async function confirmRequestedEvidence(role, referenceId) {
    if (!state.job || !role || !referenceId) return;
    const confirmed = await api(`/api/forge/jobs/${state.job.job_id}/evidence/${role}/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reference_id: referenceId })
    });
    state.job = confirmed.body.job;
    renderPersistedJob(state.job);
  }

  function renderSurfaceExecutions(job) {
    const records = (job.last_run && job.last_run.surface_executions) || [];
    const summary = (job.last_run && job.last_run.surface_execution_summary) || {};
    const panel = byId('surfaceExecutionPanel');
    const grid = byId('surfaceExecutionGrid');
    panel.hidden = records.length === 0;
    grid.replaceChildren();
    records.forEach((record) => {
      const card = document.createElement('article');
      const executed = record.status === 'complete';
      const partial = executed && record.surface_completion === 'partial';
      card.className = `surface-execution-card ${partial ? 'partial' : (executed ? 'complete' : 'abstain')}`;
      const title = document.createElement('header');
      const name = document.createElement('b');
      const status = document.createElement('span');
      name.textContent = String(record.surface || 'surface').replaceAll('_', ' ').toUpperCase();
      status.textContent = partial ? 'PARTIAL UV' : (executed ? 'DIRECT UV' : 'ABSTAINED');
      title.append(name, status);
      const detail = document.createElement('p');
      if (executed) {
        const containment = (100 * Number(record.containment || 0)).toFixed(1);
        const coverage = (100 * Number(record.owned_mask_coverage || 0)).toFixed(1);
        const completion = partial ? ` / remaining: ${String(record.remaining_scope || 'unproved surface').replaceAll('_', ' ')}` : '';
        detail.textContent = `${Number(record.owned_uv_pixels || 0).toLocaleString()} owned pixels / ${containment}% contained / ${coverage}% mask observed${completion}`;
        const provenance = document.createElement('code');
        provenance.textContent = `${record.role} / ${record.projector} / ${String(record.layer_sha256 || '').slice(0, 12)}`;
        card.append(title, detail, provenance);
      } else {
        detail.textContent = String(record.reason || 'Direct evidence did not satisfy the surface contract');
        card.append(title, detail);
      }
      grid.appendChild(card);
    });
    if (records.length) {
      panel.dataset.summary = `${Number(summary.executed_surface_count || 0)} executed / ${Number(summary.fully_complete_surface_count || 0)} full / ${Number(summary.partial_surface_count || 0)} partial / ${Number(summary.unique_uv_pixels || 0)} unique pixels / ${Number(summary.cross_surface_overlap_pixels || 0)} overlaps`;
    }
  }

  function compactAnchorValue(value) {
    if (Array.isArray(value)) {
      if (value.length && Array.isArray(value[0])) return `${value.length}-point quad`;
      return value.map((item) => Number(item).toFixed(3)).join(', ');
    }
    return Number(value).toFixed(3);
  }

  function svgElement(name, attributes) {
    const node = document.createElementNS('http://www.w3.org/2000/svg', name);
    Object.entries(attributes || {}).forEach(([key, value]) => node.setAttribute(key, String(value)));
    return node;
  }

  function editorValueText(field, value) {
    if (Array.isArray(value) && Array.isArray(value[0])) {
      return value.map((point) => `(${point[0].toFixed(3)}, ${point[1].toFixed(3)})`).join(' ');
    }
    return `${field.replaceAll('_', ' ')} = ${Number(value).toFixed(4)}`;
  }

  function renderAnchorEditor() {
    const editor = state.editor;
    if (!editor) return;
    const overlay = byId('anchorEditorOverlay');
    overlay.replaceChildren();
    const box = anchorGeometry.normalizedBox(editor.proposal.primary_object_bbox);
    overlay.appendChild(svgElement('rect', {
      class: 'car-box', x: box[0] * 1000, y: box[1] * 1000,
      width: (box[2] - box[0]) * 1000, height: (box[3] - box[1]) * 1000
    }));

    editor.editableFields.forEach((field) => {
      const value = editor.values[field];
      if (Array.isArray(value) && Array.isArray(value[0])) {
        overlay.appendChild(svgElement('polygon', {
          class: 'anchor-poly', points: value.map((point) => `${point[0] * 1000},${point[1] * 1000}`).join(' ')
        }));
        value.forEach((point, index) => overlay.appendChild(svgElement('circle', {
          class: 'anchor-handle', cx: point[0] * 1000, cy: point[1] * 1000, r: 10,
          'data-anchor-field': field, 'data-anchor-index': index
        })));
      } else {
        const y = Number(value);
        overlay.appendChild(svgElement('line', {
          class: 'anchor-line', x1: box[0] * 1000, x2: box[2] * 1000, y1: y * 1000, y2: y * 1000
        }));
        overlay.appendChild(svgElement('circle', {
          class: 'anchor-handle', cx: ((box[0] + box[2]) / 2) * 1000, cy: y * 1000, r: 11,
          'data-anchor-field': field
        }));
      }
    });

    const fields = byId('anchorEditorFields');
    fields.replaceChildren();
    editor.editableFields.forEach((field) => {
      const metadata = editor.proposal.fields[field] || {};
      const row = document.createElement('div');
      row.className = 'anchor-editor-field';
      row.innerHTML = `<b>${field.replaceAll('_', ' ')}</b><span>${editorValueText(field, editor.values[field])}</span><span>CONFIDENCE ${Number(metadata.confidence || 0).toFixed(3)} / ${String(metadata.provenance || 'unknown')}</span>`;
      fields.appendChild(row);
    });

    editor.validation = anchorGeometry.validate(editor.role, editor.values, editor.proposal.primary_object_bbox);
    const validation = byId('anchorEditorValidation');
    validation.className = `anchor-editor-validation${editor.validation.valid ? '' : ' invalid'}`;
    validation.textContent = editor.validation.valid
      ? 'GEOMETRY VALID - confirmation will invalidate stale downstream stages.'
      : editor.validation.errors.join(' / ');
    byId('anchorEditorSave').disabled = !editor.validation.valid;
  }

  function editorPointerPosition(event) {
    const rect = byId('anchorEditorOverlay').getBoundingClientRect();
    return [
      anchorGeometry.clamp01((event.clientX - rect.left) / rect.width),
      anchorGeometry.clamp01((event.clientY - rect.top) / rect.height)
    ];
  }

  function beginAnchorDrag(event) {
    const handle = event.target.closest('[data-anchor-field]');
    if (!handle || !state.editor) return;
    event.preventDefault();
    state.editor.drag = {
      field: handle.dataset.anchorField,
      index: handle.dataset.anchorIndex == null ? null : Number(handle.dataset.anchorIndex)
    };
  }

  function moveAnchorDrag(event) {
    if (!state.editor || !state.editor.drag) return;
    event.preventDefault();
    const [x, y] = editorPointerPosition(event);
    const { field, index } = state.editor.drag;
    state.editor.values = index == null
      ? anchorGeometry.moveScalar(state.editor.values, field, y)
      : anchorGeometry.moveQuadPoint(state.editor.values, field, index, x, y);
    renderAnchorEditor();
  }

  function endAnchorDrag() {
    if (state.editor) state.editor.drag = null;
  }

  function closeAnchorEditor() {
    const editor = state.editor;
    state.editor = null;
    if (editor && editor.objectUrl) URL.revokeObjectURL(editor.objectUrl);
    const dialog = byId('anchorEditorDialog');
    if (dialog.open) dialog.close();
  }

  async function openAnchorEditor(role) {
    if (!anchorGeometry) throw new Error('Anchor editor geometry module is unavailable');
    const proposals = state.job && state.job.last_run && state.job.last_run.anchor_proposals;
    const proposal = proposals && proposals.roles && proposals.roles[role];
    if (!proposal) return;
    const editableFields = anchorGeometry.editableFields(role, proposal);
    if (!editableFields.length) return;
    const reference = (state.job.inputs || []).find((entry) => entry.role === role && !entry.duplicate_of);
    if (!reference) throw new Error(`No direct ${role} reference is stored for review`);
    const response = await fetch(`/api/forge/jobs/${state.job.job_id}/references/${reference.id}/content`, { headers: INTERNAL_HEADERS });
    if (!response.ok) throw new Error(`Forge could not load the ${role} source (${response.status})`);
    const objectUrl = URL.createObjectURL(await response.blob());
    state.editor = {
      role,
      proposal,
      editableFields,
      values: anchorGeometry.proposalValues(proposal),
      objectUrl,
      drag: null,
      validation: null
    };
    byId('anchorEditorTitle').textContent = `${role.toUpperCase()} SOURCE ANCHORS`;
    byId('anchorEditorHelp').textContent = `Drag only the yellow ${editableFields.map((name) => name.replaceAll('_', ' ')).join(', ')} handle${editableFields.length === 1 ? '' : 's'}. The cyan box is the measured physical car, not the full presentation sheet.`;
    const abstention = byId('anchorEditorAbstention');
    abstention.hidden = role !== 'rear';
    abstention.textContent = role === 'rear'
      ? 'Rear-inside spoiler remains ABSTAINED: it is not visible in this source and will not be copied from the outside face.'
      : '';
    const image = byId('anchorEditorImage');
    image.onload = () => {
      byId('anchorEditorStage').style.aspectRatio = `${image.naturalWidth} / ${image.naturalHeight}`;
      renderAnchorEditor();
    };
    image.src = objectUrl;
    byId('anchorEditorSave').textContent = `CONFIRM ${role.toUpperCase()} SOURCE ANCHORS`;
    byId('anchorEditorDialog').showModal();
  }

  async function openEvidenceReview(role) {
    if (!anchorGeometry || !state.job) throw new Error('Surface review geometry module is unavailable');
    const request = (state.job.evidence_requests || []).find((row) => row.role === role);
    if (!request || !request.review_ready || !request.review_contract) {
      throw new Error('Exact-role capture attestation is required before surface review');
    }
    const reference = (state.job.inputs || []).find((entry) =>
      entry.id === request.qualified_reference_id && entry.role === role && !entry.duplicate_of
    );
    if (!reference) throw new Error(`No qualified direct ${role} reference is stored for review`);
    const field = request.review_contract.anchor_field;
    const proposal = {
      status: 'review',
      confidence: request.confidence,
      primary_object_bbox: [0, 0, 1, 1],
      fields: {
        [field]: {
          value: request.review_contract.seed_quad,
          status: 'review',
          confidence: request.confidence,
          provenance: 'unconfirmed_review_seed/v1'
        }
      }
    };
    const editableFields = anchorGeometry.editableFields(role, proposal);
    if (editableFields.length !== 1) throw new Error('Adapter surface review contract is not editable');
    const response = await fetch(`/api/forge/jobs/${state.job.job_id}/references/${reference.id}/content`, { headers: INTERNAL_HEADERS });
    if (!response.ok) throw new Error(`Forge could not load the ${role} source (${response.status})`);
    const objectUrl = URL.createObjectURL(await response.blob());
    state.editor = {
      mode: 'surface_evidence',
      role,
      referenceId: reference.id,
      proposal,
      editableFields,
      values: anchorGeometry.proposalValues(proposal),
      objectUrl,
      drag: null,
      validation: null
    };
    byId('anchorEditorTitle').textContent = `${role.replaceAll('_', ' ').toUpperCase()} PHYSICAL SURFACE`;
    byId('anchorEditorHelp').textContent = `The yellow full-image box is only a NON-AUTHORITATIVE seed. Drag TL, TR, BR, and BL onto the four corners of the visible ${String(request.physical_scope || request.surface).replaceAll('_', ' ')}; confirmation binds this exact source hash and does not create a projector.`;
    byId('anchorEditorAbstention').hidden = false;
    byId('anchorEditorAbstention').textContent = 'ABSTENTION STAYS ACTIVE: this review records direct evidence but cannot unlock PSD or Import until a calibrated adapter projector consumes it.';
    const image = byId('anchorEditorImage');
    image.onload = () => {
      byId('anchorEditorStage').style.aspectRatio = `${image.naturalWidth} / ${image.naturalHeight}`;
      renderAnchorEditor();
    };
    image.src = objectUrl;
    byId('anchorEditorSave').textContent = `CONFIRM ${role.replaceAll('_', ' ').toUpperCase()} SURFACE QUAD`;
    byId('anchorEditorDialog').showModal();
  }

  async function saveAnchorEditor() {
    const editor = state.editor;
    if (!editor) return;
    editor.validation = anchorGeometry.validate(editor.role, editor.values, editor.proposal.primary_object_bbox);
    if (!editor.validation.valid) {
      renderAnchorEditor();
      return;
    }
    if (editor.mode === 'surface_evidence') {
      const field = editor.editableFields[0];
      const role = editor.role;
      const result = await api(`/api/forge/jobs/${state.job.job_id}/evidence/${role}/quad`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reference_id: editor.referenceId, quad: editor.values[field] })
      });
      closeAnchorEditor();
      renderPersistedJob(result.body.job);
      byId('jobMessage').textContent = `${role.replaceAll('_', ' ').toUpperCase()} surface review was hash-bound. Projection, PSD, and Import remain locked until an adapter projector explicitly consumes this evidence.`;
      return;
    }
    const existing = (state.job.user_corrections && state.job.user_corrections.anchors) || {};
    const confirmed = anchorGeometry.confirmationValues(editor.role, editor.values);
    const anchors = { [editor.role]: Object.assign({}, existing[editor.role] || {}, confirmed) };
    if (editor.role === 'top' && editor.values.rear_deck_quad) {
      anchors.rear = Object.assign({}, existing.rear || {}, { rear_deck_quad: editor.values.rear_deck_quad });
    }
    const role = editor.role;
    const result = await api(`/api/forge/jobs/${state.job.job_id}/corrections`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ anchors })
    });
    closeAnchorEditor();
    renderPersistedJob(result.body.job);
    byId('jobMessage').textContent = `${role.toUpperCase()} source anchors visually confirmed. Stale downstream authority was invalidated; re-run when all required evidence is reviewed.`;
  }

  function renderAnchorProposals(job) {
    const proposals = job.last_run && job.last_run.anchor_proposals;
    const roles = proposals && proposals.roles ? proposals.roles : {};
    const panel = byId('anchorProposalPanel');
    const grid = byId('anchorProposalGrid');
    panel.hidden = Object.keys(roles).length === 0;
    grid.replaceChildren();
    requiredRoles.forEach((role) => {
      const proposal = roles[role];
      if (!proposal) return;
      const card = document.createElement('article');
      card.className = `anchor-card ${proposal.status}`;
      const fieldRows = Object.entries(proposal.fields || {}).map(([name, field]) =>
        `<li class="${field.status}"><b>${name.replaceAll('_', ' ')}</b><span>${field.value == null ? 'NO DIRECT EVIDENCE' : compactAnchorValue(field.value)} / ${Number(field.confidence || 0).toFixed(3)}</span></li>`
      ).join('');
      const editableFields = anchorGeometry ? anchorGeometry.editableFields(role, proposal) : [];
      const action = editableFields.length
        ? `<button type="button" class="anchor-confirm" data-anchor-role="${role}">REVIEW ${role.toUpperCase()} ON SOURCE</button>`
        : '<small>MORE DIRECT EVIDENCE REQUIRED</small>';
      card.innerHTML = `<header><b>${role.toUpperCase()}</b><span>${proposal.status.toUpperCase()} ${Number(proposal.confidence || 0).toFixed(3)}</span></header><ul>${fieldRows}</ul>${action}`;
      grid.appendChild(card);
    });
  }

  function renderJobState(job) {
    const jobState = String(job.state || 'collecting');
    const corrections = (job.last_run && job.last_run.required_corrections) || [];
    byId('jobState').textContent = jobState.replace('_', ' ').toUpperCase();
    if (jobState === 'qualified') {
      byId('jobMessage').textContent = `Five direct views qualified. ${job.qualification.unique_reference_count} unique references; geometry validation is ready to run.`;
    } else if (jobState === 'needs_input' && corrections.length) {
      const complete = Object.entries(job.stages || {}).filter(([, value]) => value.status === 'complete').map(([key]) => key);
      const execution = (job.last_run && job.last_run.surface_execution_summary) || {};
      const generated = Number(execution.unique_uv_pixels || 0);
      const executed = Number(execution.executed_surface_count || 0);
      const partial = Number(execution.partial_surface_count || 0);
      const evidence = executed ? ` ${executed} authority-hashed surface${executed === 1 ? '' : 's'} produced ${generated.toLocaleString()} unique UV pixels (${partial} partial);` : '';
      const requests = (job.evidence_requests || []).filter((request) => !request.qualified).length;
      const optional = requests ? ` ${requests} surface-specific direct evidence request${requests === 1 ? '' : 's'} available below.` : '';
      byId('jobMessage').textContent = `Forge completed ${complete.join(' + ') || 'intake'} and abstained at projection.${evidence} ${corrections.length} measured correction requirement${corrections.length === 1 ? '' : 's'} remain.${optional}`;
    } else if (jobState === 'ready') {
      byId('jobMessage').textContent = 'All persisted QA gates passed. The editable PSD is ready to import.';
    } else if (job.error) {
      byId('jobMessage').textContent = job.error.message || 'The Forge job failed.';
    } else {
      byId('jobMessage').textContent = 'This resumable job has not completed reference qualification yet.';
    }
    byId('runButton').disabled = jobState !== 'qualified';
    byId('runButton').textContent = jobState === 'qualified' ? 'RUN MEASURED RECONSTRUCTION' : 'RUN RECONSTRUCTION';
    const readyPSD = jobState === 'ready' && job.outputs && job.outputs.psd_path;
    byId('importButton').disabled = !readyPSD;
    renderPipeline(job);
  }

  function renderPersistedJob(job) {
    state.job = job;
    byId('jobPanel').hidden = false;
    byId('jobId').textContent = job.job_id;
    if (job.qualification) {
      renderQualification(job.qualification);
    }
    renderJobState(job);
  }

  async function resumeJobFromURL() {
    const jobId = new URLSearchParams(window.location.search).get('job');
    if (!jobId) return;
    if (!/^[a-f0-9]{32}$/.test(jobId)) throw new Error('The Forge job link is invalid.');
    const { body } = await api(`/api/forge/jobs/${jobId}`);
    renderPersistedJob(body.job);
  }

  function showJobError(error) {
    byId('jobPanel').hidden = false;
    byId('jobState').textContent = 'FAILED';
    byId('jobMessage').textContent = error && error.message ? error.message : String(error);
  }

  async function createAndQualify() {
    byId('qualifyButton').disabled = true;
    byId('jobPanel').hidden = false;
    byId('jobState').textContent = 'CREATING';
    byId('jobMessage').textContent = 'Creating resumable local job and hashing source evidence…';
    try {
      const created = await api('/api/forge/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ adapter_id: state.adapter.id, mode: 'guided' })
      });
      state.job = created.body.job;
      byId('jobId').textContent = state.job.job_id;
      window.history.replaceState({}, '', `${window.location.pathname}?job=${state.job.job_id}`);

      const form = new FormData();
      requiredRoles.forEach((role) => { form.append('roles', role); form.append('files', state.files.get(role)); });
      const optional = byId('optionalFiles').files || [];
      Array.from(optional).forEach((file) => { form.append('roles', 'assets'); form.append('files', file); });
      byId('jobState').textContent = 'HASHING';
      const uploaded = await api(`/api/forge/jobs/${state.job.job_id}/references`, { method: 'POST', body: form });
      state.job = uploaded.body.job;

      byId('jobState').textContent = 'QUALIFYING';
      const qualified = await api(`/api/forge/jobs/${state.job.job_id}/qualify`, { method: 'POST' });
      state.job = qualified.body.job;
      renderPersistedJob(state.job);
    } catch (error) {
      showJobError(error);
    } finally {
      updateCoverage();
    }
  }

  async function importReadyPSD() {
    const psdPath = state.job && state.job.outputs && state.job.outputs.psd_path;
    if (!psdPath || state.job.state !== 'ready') return;
    if (window.electronAPI && typeof window.electronAPI.importForgePSD === 'function') {
      await window.electronAPI.importForgePSD(psdPath);
      byId('jobMessage').textContent = 'PSD imported into the Paint Booth layer tree.';
      return;
    }
    if (window.opener && typeof window.opener.importPSDFromPath === 'function') {
      await window.opener.importPSDFromPath(psdPath);
      byId('jobMessage').textContent = 'PSD imported into the Paint Booth layer tree.';
      return;
    }
    throw new Error('Paint Booth import bridge is unavailable; reopen Forge from the Paint Booth toolbar.');
  }

  async function runReconstruction() {
    if (!state.job || state.job.state !== 'qualified') return;
    byId('runButton').disabled = true;
    byId('jobState').textContent = 'RECONSTRUCTING';
    byId('jobMessage').textContent = 'Verifying source hashes and extracting measured geometry evidence…';
    try {
      const result = await api(`/api/forge/jobs/${state.job.job_id}/run`, { method: 'POST' });
      if (result.body.job) {
        renderPersistedJob(result.body.job);
      } else {
        throw new Error(result.body.error || 'Forge did not return a persisted job');
      }
    } catch (error) {
      showJobError(error);
    }
  }

  bindInputs();
  byId('qualifyButton').addEventListener('click', createAndQualify);
  byId('runButton').addEventListener('click', runReconstruction);
  byId('anchorProposalGrid').addEventListener('click', (event) => {
    const button = event.target.closest('[data-anchor-role]');
    if (button) openAnchorEditor(button.dataset.anchorRole).catch(showJobError);
  });
  byId('evidenceRequestGrid').addEventListener('change', (event) => {
    const input = event.target.closest('[data-evidence-role]');
    if (input && input.files && input.files[0]) {
      uploadRequestedEvidence(input.dataset.evidenceRole, input.files[0]).catch(showJobError);
    }
  });
  byId('evidenceRequestGrid').addEventListener('click', (event) => {
    const confirm = event.target.closest('[data-evidence-confirm-role]');
    if (confirm) {
      confirmRequestedEvidence(confirm.dataset.evidenceConfirmRole, confirm.dataset.evidenceReferenceId).catch(showJobError);
      return;
    }
    const review = event.target.closest('[data-evidence-review-role]');
    if (review) openEvidenceReview(review.dataset.evidenceReviewRole).catch(showJobError);
  });
  byId('anchorEditorOverlay').addEventListener('pointerdown', beginAnchorDrag);
  window.addEventListener('pointermove', moveAnchorDrag);
  window.addEventListener('pointerup', endAnchorDrag);
  byId('anchorEditorClose').addEventListener('click', closeAnchorEditor);
  byId('anchorEditorCancel').addEventListener('click', closeAnchorEditor);
  byId('anchorEditorSave').addEventListener('click', () => saveAnchorEditor().catch(showJobError));
  byId('anchorEditorDialog').addEventListener('cancel', (event) => { event.preventDefault(); closeAnchorEditor(); });
  byId('exportReadinessButton').addEventListener('click', () => exportSurfaceReadiness().catch(showJobError));
  byId('importButton').addEventListener('click', () => importReadyPSD().catch(showJobError));
  loadAdapters().then(resumeJobFromURL).catch(showJobError);
}());
