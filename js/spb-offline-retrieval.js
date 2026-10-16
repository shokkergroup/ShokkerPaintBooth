// Owner-directed Offline Helper integration, 2026-10-13.
// Read existing FAQ units individually: unrelated FAQs in a large article must
// not lend each other coverage. This module cannot create or execute actions.
(function (W) {
    'use strict';
    var cache = null, source = null;
    // One read-only Inspector exposes these source-backed views of the same
    // loaded image. Follow-ups may move between its tabs and raw statistics,
    // but cannot borrow a different painting or project workflow.
    var inspectorTopics=['spec.inspector','spec.preview_truth_readiness',
        'spec.preview_truth_raw_alpha','spec.preview_truth_statistics',
        'spec.preview_truth_display','spec.preview_truth_format',
        'spec.preview_truth_freshness','spec.preview_truth_comparison'];
    var aliases = {
        starred:'favorite', stars:'favorite', favourites:'favorite', favorites:'favorite',
        thumbnails:'thumbnail', card:'thumbnail', cards:'thumbnail', popup:'picker',
        restarted:'restart', rendering:'render', loaded:'load', loading:'load',
        unchecked:'uncheck', checking:'check', selected:'select', selection:'selection',
        retained:'keep', stayed:'keep', kept:'keep', retains:'keep', retaining:'keep',
        changed:'change', changes:'change', changing:'change', removed:'remove', removing:'remove',
        cleared:'clear', clearing:'clear', saved:'save', saving:'save', exporting:'export',
        broke:'broken', disappeared:'missing', gone:'missing', empty:'missing', vanished:'missing',
        colour:'color', colourway:'colorway', colours:'color', colors:'color', coloured:'color', colored:'color',
        params:'parameter', parameters:'parameter', choices:'selection', choose:'pick', choosing:'pick', picks:'pick',
        swapped:'change', swapping:'change', replaced:'change', replacing:'change', swap:'change',
        strength:'strength', strengths:'strength', rotation:'rotation', rotate:'rotation',
        id:'identity', ids:'identity', filename:'filename', filenames:'filename',
        custom:'custom', customized:'custom', timeout:'timeout', timed:'timeout'
    };
    Object.assign(aliases,{magnify:'zoom',magnification:'zoom',largest:'big',maximum:'big',
        minimum:'smallest',wheel:'scroll',filled:'fill',filling:'fill',clicked:'click'});
    var noise = /^(?:old|again|still|today|yesterday|really|actually|even|looks?|looking|tri|trying|say|said|show|seen|see|got|went|now|just|lot|install|normal|though|instead|into)$/;
    // Scope is about the named UI subject, not a fixed customer sentence.
    // Similar words in another subsystem (pattern placement vs spec type,
    // layer sorting vs My Rating) cannot supply the answer's subject.
    function scope(text) {
        var t=String(text || '').toLowerCase().replace(/([a-z])([0-9])|([0-9])([a-z])/g,'$1$3 $2$4'), ids=[];
        function add(){ids=ids.concat(Array.prototype.slice.call(arguments));}
        // Keep the named colour-source control distinct from removing a
        // material. Corpus IDF movement must not turn replacement into reset.
        if(/\bfrom base\b/.test(t) && /\b(?:overlay|colou?r picker|colou?r source)\b/.test(t))
            return ['finishes.practical_picker_apply_transactions'];
        if(/\b(?:spec (?:map )?inspector|material sampler|channels inspector)\b/.test(t) && /^(?:what|how|why|where|when|is|are|does|do|can|will|should)\b|\?\s*$/.test(t))
            return inspectorTopics.slice();
        var practicalSubject=contextSubject(t);
        if(['tools.zoom_pan','tools.brush_eraser','tools.fill_bucket',
            'ui_shell.panels_and_ui_size','ui_shell.save_open_projects'].indexOf(practicalSubject)>=0)
            add(practicalSubject);
        if(/\b(?:favou?rites?|starred|my rating|surprise)\b/.test(t)) add('finishes.practical_picker_choices_persistence');
        if(/\bpicker\b/.test(t) && /\b(?:filters?|strong|sponsor safe|fast)\b/.test(t)) add('finishes.practical_picker_search_filters');
        if(/\b(?:search\w*|filtered|ranked|shown)\b/.test(t) && /\b(?:finish\w*|picker|carbon|weave|ranked|shown|favou?rite\w*)\b/.test(t)) add('finishes.practical_picker_search_filters');
        if(/\b(?:thumbnail|swatch|card)\b/.test(t) && /\b(?:image|fail\w*|flat|plain|category|load\w*|large)\b/.test(t) || /rendering full detail|brows(?:e|ed|ing).*render/.test(t)) add('finishes.practical_baked_picker_truth');
        if(/\b(?:color|colour)\s+lock(?:ed)?\b|\bspecial\b/.test(t) || /\bpicker\b/.test(t)&&/\b(?:apply|open|zone|target)\b/.test(t) || /\b(?:clear\w*|reset)\b/.test(t)&&/\bbase\b/.test(t)&&/\bstrength\b/.test(t)) add('finishes.practical_picker_apply_transactions');
        if(/\b(?:second|additional|overlay)\s+base\b/.test(t)) add('finishes.practical_overlay_selection_state');
        if(!/\bspec\b/.test(t)&&/\bpattern\b/.test(t)&&/\b(?:stack\w*|row\w*)\b/.test(t)) add('patterns.practical_stack_editor_state');
        if(/\bpattern\s*1\b/.test(t) && /\b(?:stack\w*|row\w*)\b/.test(t)) add('finishes.practical_picker_apply_transactions');
        if(/\b(?:spec\s+feel|feel)\b/.test(t) && /\b(?:sav\w*|store|storage|preset)\b/.test(t) && /\b(?:toast|said|says|message|missing|gone|disappear\w*|reopen\w*|restart\w*)\b/.test(t)) add('spec.presets_feels');
        if(/\bspec\b/.test(t) || /\bchannel\b/.test(t) && /\bdetail panel\b/.test(t) && /\bzone\b/.test(t)) {
            if(/\bpreview\b/.test(t)&&!/\b(?:apply|popout|detach\w*|target\w*)\b/.test(t)) add('spec.practical_overlay_test_preview');
            else if(/\b(?:type|params?|parameters?|opacity|range|id)\b/.test(t)) add('spec.practical_overlay_defaults_replacement');
            else if(/\b(?:channel\w*|offset|step\w*|apply|popout|detach\w*|target\w*)\b/.test(t)) add('spec.practical_overlay_editor_targets');
        }
        if(/\b(?:config\w*|session settings)\b/.test(t)) {
            if(/\b(?:import|export|filename|invalid|ignore|without|only)\b/.test(t)) add('zones.practical_configuration_exchange_errors');
            else add('zones.practical_configuration_state');
        }
        if(/\bpreset\b/.test(t)&&!(/\b(?:feel|matte|gloss|satin|chrome|metallic)\b/.test(t))) {
            if(/\b(?:import|export\w*|description|filename|\.shokker|no finish)\b/.test(t)) add('zones.practical_configuration_exchange_errors');
            else add('zones.practical_named_preset_storage');
        }
        if(/\.shokker\b/.test(t)) add('zones.practical_configuration_exchange_errors');
        return Array.from(new Set(ids));
    }
    function words(text, api) {
        var t = String(text || '').replace(/([a-z])([A-Z])/g,'$1 $2').toLowerCase().replace(/([a-z])([0-9])|([0-9])([a-z])/g,'$1$3 $2$4');
        // Preserve single-letter shortcuts that the general word tokenizer
        // drops. These identify a question's key, never an executable action.
        t=t.replace(/\bctrl\s*\+?\s*s\b/g,'shortcutctrls').replace(/\b(?:press\s+x|x\s+key)\b/g,'keyx');
        t=t.replace(/\bback[ -]+up\b/g,'backup');
        if(api.contextArticle==='tools.zoom_pan' && /\bfar\b/.test(t) && /\bzoom\b/.test(t)) t+=' maximum';
        if(api.contextArticle==='tools.fill_bucket' && /nothing.{0,15}(?:fill|happen)|not.{0,10}fill/.test(t)) t+=' clicked nothing happened';
        if(api.contextArticle==='ui_shell.save_open_projects' && /\bopen\b/.test(t) && /\b(?:again|tomorrow)\b/.test(t)) t+=' project next day';
        if(inspectorTopics.indexOf(api.contextArticle)>=0)
            t=t.replace(/\baverages?\b/g,'mean');
        // Describe the search relationship without treating a returned finish
        // name as a request to put that material on the car.
        if(/\bsearch(?:ed|ing)?\b/.test(t) && /\b(?:also|too|other|different|unexpected)\b|\bas well\b|did(?:n't| not) type/.test(t)) t+=' related words synonym';
        if(/\.shokker|file\s*name|filename/.test(t)) t=t.replace(/\bname\b/g,'filename');
        // A reported Saved message concerns persistence, not the loader's
        // selected row. Keep the semantic operation as well as the shared subject.
        if(/\bpreset\b/.test(t) && /\bsav(?:e|ed|ing)\b/.test(t) && /\b(?:toast|said|says|message|reopen\w*|restart\w*)\b/.test(t)) t+=' toast persistent storage';
        if(api.contextArticle==='zones.practical_named_preset_storage' && /\b(?:click|choose|answer)\s+(?:no|cancel)\b/.test(t) && /\boverwrite\b/.test(t)) t+=' decline confirmation';
        t = t.replace(/[a-z]+/g,function(w){return aliases[w] || w;});
        return Array.from(new Set(api.tokens(t).filter(function(w){return !noise.test(w);} )));
    }
    function index(ix,api) {
        if (source === ix && cache) return cache;
        source=ix; cache={units:[],post:{}};
        ix.docs.forEach(function(d){
            d.faq.forEach(function(f){
                var w=words(f.q,api); if(w.length<2 && !w.some(function(x){return /^(?:keyx|shortcutctrl)$/.test(x);})) return;
                var aw=words(f.a,api), u={d:d,f:f,w:w,aw:aw,m:0};
                w.forEach(function(t){u.m+=Math.min(7,ix.idf[t] || 2);});
                var n=cache.units.push(u)-1;
                Array.from(new Set(w.concat(aw))).forEach(function(t){(cache.post[t] || (cache.post[t]=[])).push(n);});
            });
        });
        return cache;
    }
    function match(text,ix,api,debug) {
        if(!ix || !ix.docs || !api) return null;
        var q=words(text,api); if(q.length<2 && !q.some(function(w){return /^(?:keyx|shortcutctrl)$/.test(w);})) return null;
        var c=index(ix,api), counts={}, mass=0, ids=scope(text), scoped=ids.length>0;
        // Owner recovery5: a verified factual topic supplies only the missing
        // UI subject. Rank existing FAQ units within that source; never pool
        // another article's words or turn the topic into edit permission.
        if(api.contextArticle && supportsContext(api.contextArticle)) {
            var contextIds=contextArticles(api.contextArticle);
            if(api.contextArticle.indexOf('cars.reference.dirtlatemodel-')===0) {
                var queryName=' '+String(text).toLowerCase().replace(/[^a-z0-9]+/g,' ').trim()+' ';
                var otherCar=ix.docs.some(function(d){
                    if(d.id.indexOf('cars.reference.')!==0 || d.id.indexOf('cars.reference.dirtlatemodel-')===0)return false;
                    return (d.a.aliases || []).some(function(a){
                        var name=String(a).toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
                        return name.length>=4 && queryName.indexOf(' '+name+' ')>=0;
                    });
                });
                if(otherCar)return null;
            }
            // Recovery6: a named navigation, painting or project control is a
            // new subject. Short follow-ups can use the previous source only
            // when they do not explicitly name another inspected workflow.
            var subject=contextSubject(text);
            if(subject && contextIds.indexOf(subject)<0) return null;
            // Explicitly naming another preset system changes the subject.
            // Generic scope heuristics cannot lend that named control the old
            // source merely because both discuss names or local storage.
            if(/\b(?:spec\s+feel|saved\s+feel|feel\s+preset|feels)\b/i.test(text) && api.contextArticle!=='spec.presets_feels') return null;
            if(/\b(?:named\s+)?zone\s+preset\b/i.test(text) && api.contextArticle!=='zones.practical_named_preset_storage') return null;
            if(inspectorTopics.indexOf(api.contextArticle)>=0 && !/\b(?:overlay|pattern|parameter|opacity|offset)\b/i.test(text))
                ids=ids.filter(function(id){return id.indexOf('spec.practical_overlay_')!==0;});
            if(api.contextArticle==='support.flat_or_shiny' && !/\b(?:type|parameter|opacity|popout|detach|offset|id)\b/i.test(text))
                ids=ids.filter(function(id){return id.indexOf('spec.practical_overlay_')!==0;});
            if(ids.length && !ids.some(function(id){return contextIds.indexOf(id)>=0;})) return null;
            ids=contextIds; scoped=true;
        }
        // Existing general questions already have authored routes. Do not
        // replace them merely because a FAQ elsewhere shares common nouns.
        if(!scoped) return null;
        if(!api.contextArticle && /^\s*(?:what|what's|whats|who)\s+(?:is|are|does)\b/i.test(text) && q.length<=4 && !/\b(?:largest|smallest|maximum|minimum)\b/i.test(text) && !q.some(function(w){return /^(?:keyx|shortcutctrl)$/.test(w);})) return null;
        q.forEach(function(t){var weight=Math.min(7,ix.idf[t] || 2);mass+=weight;(c.post[t] || []).forEach(function(n){counts[n]=(counts[n] || 0)+weight;});});
        var ranked=[];
        Object.keys(counts).forEach(function(n){
            var u=c.units[n], hit=0, ah=0;
            q.forEach(function(t){var wt=Math.min(7,ix.idf[t] || 2);if(u.w.indexOf(t)>=0)hit+=wt;else if(u.aw.indexOf(t)>=0)ah+=wt;});
            var qc=(hit+0.4*ah)/mass, fc=hit/u.m;
            // Some authored headings have no words for the customer's symptom
            // ("whole window" versus "toolbars"). Complete answer coverage in
            // a verified source can supply that relationship; weak coverage
            // and competing answers still cannot.
            if(api.contextArticle && q.length>=3 && (hit+ah)/mass>=0.85 && fc<0.1) fc=0.35;
            // In a verified project topic, opening tomorrow and backing up
            // are different operations from saving or diagnosing a TGA.
            if(api.contextArticle==='ui_shell.save_open_projects') {
                if(/\bopen\b/i.test(text) && /\b(?:again|tomorrow|next day)\b/i.test(text) && /How do I open my project the next day/.test(u.f.q)) qc+=0.35;
                if(/\b(?:files?|keep)\b/i.test(text) && /\bbackup\b/i.test(text) && /How do I back up an editable paint scheme/.test(u.f.q)) qc+=0.35;
            }
            var named=['my rating','surprise','color lock','colour lock','rendering'];
            function hasNamed(s,phrase){return api.contextArticle ? new RegExp('\\b'+phrase+'\\b','i').test(s) : String(s).toLowerCase().indexOf(phrase)>=0;}
            var namedHit=named.some(function(phrase){return hasNamed(text,phrase) && hasNamed(u.f.q.replace(/colour/g,'color'),phrase.replace(/colour/g,'color'));});
            // A material tuple is a different question from one channel's
            // average. Preserve that named subject inside the Inspector.
            if(inspectorTopics.indexOf(api.contextArticle)>=0 && /\btuple\b/i.test(text) && /\btuple\b/i.test(u.f.q)) namedHit=true;
            var shortcutHit=q.some(function(w){return /^(?:keyx|shortcutctrl)$/.test(w) && u.w.indexOf(w)>=0;});
            if(shortcutHit) namedHit=true;
            if(api.contextArticle==='ui_shell.panels_and_ui_size' && /\bctrl\b/i.test(u.f.q) && !/\b(?:ctrl|keyboard|shortcut)\b/i.test(text)) return;
            if(scoped && ids.indexOf(u.d.id)<0) return;
            if(qc<0.2 || (fc<0.1 && !namedHit)) return;
            var covered=q.filter(function(t){return u.w.indexOf(t)>=0 || u.aw.indexOf(t)>=0;});
            if(covered.length<2 && !namedHit) return;
            var score=2*qc*fc/(qc+fc)+0.12*ah/mass;
            if(shortcutHit) score+=0.45;
            // A report about Special strength changes needs that material and
            // numeric field together; a general colour-lock FAQ cannot replace it.
            if (/\bspecial\b/i.test(text) && /\bstrengths?\b/i.test(text) && /\bspecial\b/i.test(u.f.q) && /\bstrength\b/i.test(u.f.q)) score+=0.08;
            if(namedHit) score+=0.18;
            if(named.some(function(phrase){return hasNamed(text,phrase) && !hasNamed(u.f.q.replace(/colour/g,'color'),phrase.replace(/colour/g,'color'));})) return;
            // Declining and confirming a save have opposite outcomes. Keep
            // the polarity even though the legacy tokenizer drops "no".
            if(api.contextArticle==='zones.practical_named_preset_storage' && /\boverwrit\w*\b/i.test(text)){
                var decline=/\bdeclin\w*\b|\b(?:click|choose|answer)\s+(?:no|cancel)\b/i.test(text);
                var asksConfirm=/\bconfirm\w*\b/i.test(text) && !/\b(?:edit|change|state|version|while|during)\b/i.test(text);
                if(decline && !/declined confirmation returns before the storage write/i.test(u.f.a)) return;
                if(asksConfirm && /Save awaits confirmation before replacing/i.test(u.f.a)) score+=0.18;
            }
            var operations=['remov','chang','clear','uncheck','import','export','save','load','delet'];
            var qo=operations.filter(function(op){return q.indexOf(op)>=0;});
            if(qo.length===1 && u.w.indexOf(qo[0])>=0) score+=0.15;
            if(scoped && /\b(?:failed|missing|gone|empty|error|timed out|wrong)\b/i.test(text) && /^why\b/i.test(u.f.q)) score+=0.06;
            if(q.length===u.w.length && covered.length===q.length) score+=0.25;
            ranked.push({doc:u.d,faq:u.f,score:score,qcov:qc,fcov:fc,covered:covered});
        });
        ranked.sort(function(a,b){return b.score-a.score;});
        if(debug) return {scope:ids,words:q,ranked:ranked.slice(0,3).map(function(x){return {id:x.doc.id,faq:x.faq.q,score:x.score};})};
        var best=ranked[0]; if(!best || best.score<(scoped?0.28:0.68)) return null;
        // Equal variants of the same answer are fine; distinct close answers
        // stay with the existing router rather than guessing a material fact.
        var other=ranked.find(function(x){return x.faq.a!==best.faq.a;});
        if(other && best.score-other.score<0.02) return {clarify:true,choices:[best.faq.q,other.faq.q],scoped:true};
        best.scoped=scoped;
        return best;
    }
    function supportsContext(id) {
        return ['ai_copilot.mcp_claude_chatgpt','ai_copilot.offline_vs_ai','help_support_1.ai_setup','help_support_1.ai_cost','layers.merge','ui_shell.update_banner','shokk_drop.fracture_this_paint',
            'spec.presets_feels','zones.practical_named_preset_storage',
            'zones.practical_configuration_state','zones.practical_configuration_exchange_errors',
            'patterns.practical_stack_editor_state','finishes.practical_picker_apply_transactions',
            'finishes.practical_overlay_selection_state','tools.zoom_pan',
            'tools.brush_eraser','tools.fill_bucket','ui_shell.panels_and_ui_size',
            'ui_shell.save_open_projects','tools.eyedropper_pick','tools.select_shapes',
            'layers.open_psd','preview_render.export_psd_photoshop','support.flat_or_shiny',
            'finishes.foundation_shine_only','finishes.base_compare','finishes.gradients_flip_depth_underglow',
            'cars.reference.dirtlatemodel-350','cars.reference.dirtlatemodel-358','cars.reference.dirtlatemodel-438'].indexOf(id)>=0 || inspectorTopics.indexOf(id)>=0;
    }
    function contextArticles(id) {
        if(['ai_copilot.mcp_claude_chatgpt','ai_copilot.offline_vs_ai','help_support_1.ai_setup','help_support_1.ai_cost'].indexOf(id)>=0)return ['ai_copilot.mcp_claude_chatgpt','ai_copilot.offline_vs_ai','help_support_1.ai_setup','help_support_1.ai_cost'];return inspectorTopics.indexOf(id)>=0 ? inspectorTopics.slice() : [id];}
    function contextSubject(text) {
        if(/\b(?:claude|codex|chatgpt|ai helper|offline helper|openrouter|deepseek)\b/i.test(text))return 'ai_copilot.mcp_claude_chatgpt';
        if(/\b(?:update banner|remind me later)\b/i.test(text))return 'ui_shell.update_banner';
        if(/\bfracture this paint\b/i.test(text))return 'shokk_drop.fracture_this_paint';
        var t=String(text || '').toLowerCase();
        if(/\bfrom base\b/.test(t) && /\b(?:overlay|colou?r picker|colou?r source)\b/.test(t))return 'finishes.practical_picker_apply_transactions';
        if(/\bdirt\s+late\s+model\b/.test(t))return /\blimited\b/.test(t)?'cars.reference.dirtlatemodel-350':/\bsuper\b/.test(t)?'cars.reference.dirtlatemodel-438':/\bpro\b/.test(t)?'cars.reference.dirtlatemodel-358':'customer-dirt-kind';
        if(/\b(?:underglow|color depth|colour depth|color flip|colour flip|color lab|colour lab)\b/.test(t))return 'finishes.gradients_flip_depth_underglow';
        if(/\bfoundation\b/.test(t))return 'finishes.foundation_shine_only';
        if(/\bmetallic\b/.test(t)&&/\bpearl\b/.test(t)&&/\b(?:difference|compare)\b/.test(t))return 'finishes.base_compare';
        if(/\bspec\b/.test(t)&&/\b(?:wrong|broken|looks off)\b/.test(t))return 'support.flat_or_shiny';
        if(/\b(?:spec (?:map )?inspector|material sampler|channels inspector)\b/.test(t)) return 'spec.inspector';
        if(/\b(?:eyedropper|pick item|add colou?r)\b/.test(t)) return 'tools.eyedropper_pick';
        if(/\bsampl(?:e|ing)\s+(?:an?\s+)?colou?r\b/.test(t)) return 'tools.eyedropper_pick';
        if(/\b(?:magic wand|wand|marquee|grab object|smart region fill|select all colou?r)\b/.test(t)) return 'tools.select_shapes';
        if(/\b(?:rendered|flat)\s+tga\b/.test(t) && /\b(?:restore|recover|backup|editable|layers)\b/.test(t)) return 'ui_shell.save_open_projects';
        if(/\b(?:load|open|import)\b/.test(t) && /\b(?:psd|xcf|ora|layered template)\b/.test(t)) return 'layers.open_psd';
        if(/\b(?:photoshop|round[ -]trip|channel png export)\b/.test(t)) return 'preview_render.export_psd_photoshop';
        if(/^\s*(?:what|does|do|will|can|why|how)\b/.test(t)) {
            if(/\bctrl\s*\+?\s*s\b/.test(t)) return 'ui_shell.save_open_projects';
            if(/\b(?:press\s+x|x\s+key)\b/.test(t)) return 'tools.brush_eraser';
        }
        if(/\b(?:interface|toolbars?|ui)\b/.test(t)) return 'ui_shell.panels_and_ui_size';
        if(/\b(?:brush|eraser|stroke)\b/.test(t)) return 'tools.brush_eraser';
        if(/\b(?:bucket|contiguous)\b/.test(t)) return 'tools.fill_bucket';
        if(/\bgradient\b/.test(t) && !/\b(?:where|switch)\b/.test(t)) return 'tools.gradient';
        if(/\b(?:zoom\w*|pan|scroll\w*|edit big)\b/.test(t)) return 'tools.zoom_pan';
        if(/\b(?:project|spbproj|save window|source missing)\b/.test(t)) return 'ui_shell.save_open_projects';
        if(/\bhow\b.*\b(?:load|open|import)\b.*\bpsd\b/.test(t)) return 'layers.open_psd';
        if(/\bhow\b.*\bpattern\b.*\b(?:smaller|finer|rotate|add)\b/.test(t)) return 'patterns.scale_rotation_opacity';
        return null;
    }
    // Customer presentation only. Keep the source FAQ identity/link and require
    // its evidence phrases before using a plain-language version. A changed
    // source falls back to its own answer; this is not a new knowledge entry.
    function present(f) {
        // The original FAQ asks whether deletion is possible. A customer's
        // Undo question needs the irreversible consequence, not its "Yes".
        if(f.q==='Can I delete a saved project?' && /cannot be undone/i.test(f.a))
            return 'Deleting a saved project cannot be undone. The X on its row in SPB PROJECTS asks for confirmation before deleting it.';
        var rows=[
            ['Why can a starred finish disappear after reopening the app?', ['in-memory Set','localStorage'], 'The star can update on screen even if SPB could not save it. If favorites disappear after reopening, check that you are using the same app/profile and that local settings can be saved. A missing favorite does not by itself mean the finish was removed.'],
            ['Why does a one-word search show related words I did not type?', ['synonym','all-token'], 'Some single-word searches include related terms, so results can contain words you did not type. Searches with multiple words require all of the words to match. These are search matches, not tested recommendations for your car.'],
            ['Why might the spec test-preview status remain Rendering after a successful response fails to display?', ['Image.onload','Image.onerror'], 'Rendering alone does not prove the spec test preview finished. That label can remain if the returned image fails to load. A server response does not prove the image was displayed successfully; check for the actual preview image.'],
            ['Does the Saved preset toast prove that my named Zone setup reached persistent storage?', ['catches errors silently','without verifying the write'], 'The Saved message does not guarantee your named Zone preset was saved successfully. SPB can show it even if saving local settings failed. Check that you are using the same app/profile and investigate local storage before assuming the preset was intentionally deleted.'],
            ['Why can clearing the Base reset Spec Strength from near zero to100percent?', ['at or below0.05','resets it to1'], 'Clearing the Base can reset Spec Strength to 100% when it was at 5% or below. That safeguard runs before SPB handles the material choice, including Clear. Clearing the Base does not guarantee every numeric setting stays unchanged.'],
            ['Does seeing a source-layer name prove the zone has valid nonempty coverage?', ['ID existence','nonempty coverage'], 'The summary tells you which source layer IDs exist, plus their names, visibility and locks. It does not measure the pixels covered by a material. Check the actual target coverage before assuming the finish will appear.']
        ];
        var row=rows.find(function(x){return x[0]===f.q && x[1].every(function(k){return String(f.a).indexOf(k)>=0;});});
        return row ? row[2] : f.a;
    }
    W.SpbOfflineRetrieval={match:match,present:present,supportsContext:supportsContext};
})(typeof window !== 'undefined' ? window : this);
