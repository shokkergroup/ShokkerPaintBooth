(function(W){

    'use strict';

    var DATA={cars:[]},ARTICLES={};

    var STOP=new Set('a an the my your this that these those is are was were do does did can could should would i we you it its to from for of on in with and or about have has use need know tell me what which where how why please paint painting template file files car cars iracing'.split(' '));

    function words(text){return W.SpbCarKnowledge.norm(text).replace(/air hose/g,'airhose').split(' ').filter(function(t){return t&&!STOP.has(t);}).map(function(t){return t.length>4?t.replace(/s$/,''):t;});}

    function index(list){ARTICLES={};DATA.cars=list.filter(function(a){return a.car_reference;}).map(function(a){ARTICLES[a.car_reference.id]=a;return a.car_reference;});}

    function pick(text){return W.SpbCarKnowledge.selectContext(text,null,{template_identity:W.SpbTemplateIdentity?W.SpbTemplateIdentity.read():null},DATA);}

    function namesCar(text){var catalog=DATA;if(!DATA.cars.length&&W.SpbCarReferenceNames&&W.SpbCarReferenceNames.schema==='spb-car-name-index/1'&&Array.isArray(W.SpbCarReferenceNames.cars))catalog=W.SpbCarReferenceNames;var found=W.SpbCarKnowledge&&W.SpbCarKnowledge.select(catalog,{query:text});return !!(found&&((found.matches||[]).length||found.retired_matches));}

    function welcome(){

        if(!W.SpbCarKnowledge||!W.SpbCarKnowledge.identitySummary||!DATA.cars.length)return {status:'unavailable',source_verified:false,can_target_panels:false,text:'Car references are not ready yet. I can help explain the loaded layer groups.'};

        return W.SpbCarKnowledge.identitySummary(pick(''));

    }

    function packet(a,text,title){return {id:a.id,title:title||a.title,level:'beginner',text:text,faq:null,summary:text,chat_summary:text,reference_context:true,how:[],shot:null,actions:[],related:(a.related||[]).slice(0,4)};}

    function cited(reply,a,facts){

        var seen={},details=a.source_details||{};

        reply.sources=(reply.sources||[]).slice(0,4);reply.sources.forEach(function(s){if(s.url)seen[s.url]=true;});

        (facts||[]).forEach(function(f){(f.source_ids||[]).forEach(function(id){var s=details[id];if(s&&s.url&&!seen[s.url]){seen[s.url]=true;var label=s.title||(f.release&&f.release.label)||(f.file?f.file+' — inspected template source':id.split(':').pop());label=label.replace(/^(20\d\d)-?s([1-4])(?:p(\d+))?$/i,function(_,y,season,p){return y+' Season '+season+(p?' Patch '+p:'');});reply.sources.push({url:s.url,label:label});}});});

        reply.sources=reply.sources.slice(0,4);return reply;

    }

    function linksHtml(sources){

        function esc(s){return String(s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}

        var links=(sources||[]).slice(0,4).filter(function(s){return /^https:\/\/[a-z0-9.-]+(?::443)?(?:\/|$)/i.test(s.url)&&!/[\u0000-\u0020\\]/.test(s.url);}).map(function(s){return '<a class="spb-ob-link" href="'+esc(s.url)+'" target="_blank" rel="noopener noreferrer">'+esc(s.label||'Official source')+'</a>';});

        return links.length?'<div class="spb-ob-sec"><b>Sources</b><div class="spb-ob-row">'+links.join('')+'</div></div>':'';

    }

    function cardHtml(r){

        var a=r&&r.answer;if(!a||!a.chat_summary||!(a.reference_context||a.live_context))return null;

        function esc(s){return String(s||'').replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}

        return '<details class="spb-ob-tcard spb-oa-card"><summary style="cursor:pointer;padding:10px">Reference details and sources — '+esc(a.title)+'</summary><div class="spb-ob-art"><div class="spb-ob-tsum" style="white-space:pre-line">'+esc(a.text)+'</div>'+linksHtml(a.sources)+'</div></details>';

    }

    function followup(text,previous){

        var p=previous&&(previous.answer||previous),q=String(text||'').trim(),m=/^(?:and|what about|how about|explain)\s+(?:the\s+)?(red(?: channel)?|green(?: channel)?|blue(?: channel)?|metallic|roughness|clear\s*coat|alpha)(?:\s+(?:channel|layer))?\s*[?.!]*$/i.exec(q)||/^what does (?:the )?(red|green|blue|metallic|roughness|clear\s*coat|alpha)(?: channel)? (?:do|mean)\s*[?.!]*$/i.exec(q);

        var availability=/^(?:and\s+)?(?:is (?:that|it|this)(?: (?:car|one|model))? (?:the )?legacy(?: one)?|is (?:that|it|this)(?: car)? still available|can i(?: still)? paint (?:that|it|this)(?: car)?)\s*[?.!]*$/i.test(q);

        var download=/^(?:and\s+)?(?:where (?:can|do) i (?:get|download|find) (?:it|that(?: template)?|this template)|(?:how do i|can i) (?:download|open) (?:it|that(?: template)?|this template))\s*[?.!]*$/i.test(q);

        if((!m&&!availability&&!download)||!p||!p.reference_context||!p.reference_car_id||!W.SpbConversationScope||p.document_stamp==null||!W.SpbConversationScope.current(p.document_stamp))return null;

        var a=ARTICLES[p.reference_car_id];if(!a||!a.car_reference)return null;

        if(download){var downloadReply=answer(a,'Where can I download and open the '+a.car_reference.name+' template?');if(downloadReply){downloadReply.reference_car_id=p.reference_car_id;downloadReply.document_stamp=p.document_stamp;}return downloadReply?{cls:'ANSWER',hits:[],answer:downloadReply}:null;}

        if(availability && /\bcan i(?: still)? paint\b/i.test(q) && (a.car_reference.facts||[]).some(function(f){return f.topic==='custom-paint-restriction';})) {
            var restricted=answer(a,'What custom-paint restrictions apply to '+a.car_reference.name+'?');
            if(restricted){restricted.reference_car_id=p.reference_car_id;restricted.document_stamp=p.document_stamp;return {cls:'ANSWER',hits:[],answer:restricted};}
        }
        if(availability){var c=a.car_reference,v=c.availability||{},t=c.name+': '+(c.status==='legacy'?'this exact reference is classified as Legacy. ':c.status==='retired'?'this exact reference is retired. ':'this exact reference is current-listed, rather than classified as Legacy. ');t+=v.simulator_painting_available===false?'Official retirement evidence says painting this exact model is unavailable. Preserve the old file; a replacement does not establish compatible templates or UVs.':'Catalog listing does not verify purchase access, ownership, current simulator painting availability or compatibility with your open file. Confirm the exact model in iRacing before exporting.';var r=cited(packet(a,t,'Exact car availability'),a,(c.facts||[]).filter(function(f){return /retir|availability|identity/.test(f.topic)||/retir/i.test(f.text);}));var basis=(c.status_basis||[]).join(' '),ids=(v.status_source_ids||[]).slice();if(/manual/i.test(basis))ids.push('roster:manuals');if(/tradingpaints/i.test(basis))ids.push('roster:tradingpaints');r=cited(r,a,[{source_ids:ids}]);r.reference_car_id=c.id;r.document_stamp=p.document_stamp;return {cls:'ANSWER',hits:[],answer:r};}

        var property=m[1].toLowerCase().replace(/ channel$/,'');property={red:'metallic',green:'roughness',blue:'clearcoat'}[property]||property;

        var reply=answer(a,'What does '+property+' mean in the '+a.car_reference.name+' template?');

        if(reply){reply.reference_car_id=p.reference_car_id;reply.document_stamp=p.document_stamp;}

        return reply?{cls:'ANSWER',hits:[],answer:reply}:null;

    }

    function answer(a,text){

        if(!a.car_reference||!W.SpbCarKnowledge)return null;

        if(/\b(?:uv\s+coordinates|where exactly|give\b[^.?!]*\bbox)\b/i.test(text))return packet(a,'UV coordinates and panel boxes are unverified for your open file. Show the requested part in SPB or use a confirmed live car map, then inspect the preview. Layer names and a similar-looking template cannot establish that location.','Panel positions need confirmation');

        var picked=pick(text);

        if(picked.comparison&&!picked.comparison.complete){

            var unresolved=picked.comparison.mentions.filter(function(m){return !m.resolved;}).map(function(m){return m.query;});

            return packet(a,'I need an exact car/version for each side of this comparison. Please clarify: '+unresolved.join('; ')+'. '+(picked.matches.length?'Possible references: '+picked.matches.map(function(c){return c.name;}).join('; ')+'. ':'')+'I will not substitute the open car or assume template compatibility.','Confirm comparison identities');

        }

        if(picked.comparison&&picked.comparison.complete&&picked.matches.length===1)return packet(a,'Both names resolve to the same reference: '+picked.matches[0].name+'. That does not establish that two saved paints or source revisions are compatible. Confirm each actual template before reusing masks.','Same car reference');

        if(picked.retired_matches){var retiredReply=packet(a,picked.retired_matches.map(function(r){return r.name+': '+r.note;}).join(' ')+' Confirm which old template you have before using a current-car reference.','Retired model needs its own reference');retiredReply.sources=picked.retired_matches.map(function(r){return {url:r.source,label:'Retired-model release note'};});return retiredReply;}

        if(picked.reason==='excluded-configured-car')return packet(a,'You said this is not the car selected by the iRacing destination folder ('+picked.identity_evidence.configured_paint_folders.join(' / ')+'). Confirm the loaded template and correct destination before using its reference.','Check the open car identity');

        if(picked.identity_conflict&&picked.template_match)return packet(a,'The verified source-template evidence and current destination or observations disagree. Confirm the loaded template and iRacing destination before using car-specific advice.','Check the open car identity');

        if(picked.reason==='source-name-recognition-conflict')return packet(a,'The source filename ('+picked.identity_evidence.source_paint_names.join(' / ')+') and recognized layout ('+picked.identity_evidence.recognized_layouts.join(' / ')+') suggest different car variants. Neither verifies this template. Reopen the saved project to verify its original source, or confirm the exact car before using its reference. Actual layer groups can still be explained without choosing a car.','Check the open car identity');

        if(picked.identity_conflict)return packet(a,(picked.identity_evidence.configured_paint_folders.length?'The selected iRacing folder is '+picked.identity_evidence.configured_paint_folders.join(' / ')+', while the recognized layout is ':'Live recognition disagrees between observations: ')+picked.identity_evidence.recognized_layouts.join(' / ')+'. Confirm the loaded template and destination before using car-specific advice. The destination folder alone does not verify this file.','Check the open car identity');

        if(!picked.definite||picked.matches.length!==1){

            var names=picked.matches.slice(0,5).map(function(c){return c.name;});

            if(picked.matches.length>=2&&picked.matches.length<=5&&(picked.comparison||/\b(vs|versus|compare|comparison|between|both|same|share|shared|different|difference|two)\b/i.test(text)||/\b(use|copy|borrow|transfer)\b.*\b(selections?|masks?)\b/i.test(text))){

                var comparisons=picked.matches.slice(0,3).map(function(c){

                    var detail=(c.facts||[]).filter(function(f){return /variant|export|compatib/.test(f.topic)||/_ss|same.*(?:zip|archive|template)|separate.*(?:psd|template)/i.test(f.text);}).slice(0,2).map(function(f){return f.text;}).join(' ');

                    return c.name+': '+(detail||'Inspected files: '+(c.template_metadata||[]).map(function(m){return m.file;}).join('; ')+'.');

                });

                var comparisonReply=packet(a,'These are separate car/version references.\n'+comparisons.join('\n')+' Cross-car mask compatibility is unverified; confirm the exact template before reusing selections.','Compare template variants');

                picked.matches.slice(0,3).forEach(function(c){comparisonReply=cited(comparisonReply,ARTICLES[c.id]||a,(c.facts||[]).filter(function(f){return /variant|export|compatib/.test(f.topic)||/_ss|same.*(?:zip|archive|template)|separate.*(?:psd|template)/i.test(f.text);}).slice(0,2));});

                return comparisonReply;

            }

            return packet(a,names.length?'Which exact car or version do you mean? '+names.join('; ')+'. I need that before giving template-specific advice.':'Tell me the exact car and version, or its iRacing paint-folder name, so I can use the correct template reference.','Choose the exact car');

        }

        var car=picked.matches[0],nameWords=new Set(words([car.name].concat(car.aliases||[]).join(' '))),query=words(text).filter(function(t){return !nameWords.has(t);});

        a=Object.assign({},ARTICLES[car.id]||a,{id:'cars.reference.'+car.id,title:car.name+' — template reference'});

        if(/\b(?:which|what)\s+(?:car|vehicle|model)\b/i.test(text))return packet(a,picked.template_match&&picked.template_match.exact_variant?'This project’s verified original source is '+car.name+'.':'The current reference is '+car.name+'. '+(picked.identity_source||'This is the model named in your question.')+'. Confirm that it matches the loaded template before editing; the reference does not verify its panel positions.');

        var firstPaint=W.SpbCarKnowledge.firstPaintWorkflow&&W.SpbCarKnowledge.firstPaintWorkflow(car,text);
        if(firstPaint&&firstPaint.requested){
            var workflowText=firstPaint.status==='painting-restricted'?firstPaint.guidance:'Starting '+car.name+' in SPB:\n'+firstPaint.steps.map(function(step,i){return (i+1)+'. '+step;}).join('\n');
            if(firstPaint.variant_paths_to_inspect&&firstPaint.variant_paths_to_inspect.length)workflowText+='\nMatching variant labels to inspect: '+firstPaint.variant_paths_to_inspect.join('; ')+'.';
            if(firstPaint.export_reference_groups&&firstPaint.export_reference_groups.length)workflowText+='\nInspected export-guide group: '+firstPaint.export_reference_groups.join('; ')+'. Keep new artwork outside it.';
            if(firstPaint.knowledge_scope)workflowText+='\n'+firstPaint.knowledge_scope;
            var workflowPacket=packet(a,workflowText,car.name+' — starting workflow');
            workflowPacket.related=(firstPaint.help_article_ids||[]).slice(0,4);
            if(firstPaint.status==='general-spb-starting-workflow'){
                var workflowBrief='Starting '+car.name+':\n1. Open the exact layered template and wait for its layers.\n2. Select artwork or add a layer outside guide groups; preserve wanted numbers and sponsors.\n3. Use Layer for artwork, Zone for coverage/finishes; check the active target.\n4. Follow export-guide instructions, check RENDER, then check the paint in iRacing.';
                if(firstPaint.variant_paths_to_inspect&&firstPaint.variant_paths_to_inspect.length)workflowBrief+='\nVariant labels to inspect: '+firstPaint.variant_paths_to_inspect.join('; ')+'.';
                if(firstPaint.export_reference_groups&&firstPaint.export_reference_groups.length)workflowBrief+='\nGuide group: '+firstPaint.export_reference_groups.join('; ')+'.';
                workflowBrief+='\nNo edits made. Labels do not verify pixels, decal restrictions, compatibility or UV placement. Full steps and sources are below.';
                workflowPacket.summary=workflowBrief;workflowPacket.chat_summary=workflowBrief;
            }
            return cited(workflowPacket,a,(car.facts||[]).filter(function(f){return (firstPaint.variant_source_fact_ids||firstPaint.source_fact_ids||[]).indexOf(f.id)!==-1;}));
        }

        var facts=car.facts||[],history=/\b(?:changed|changes? (?:in|to|since)|^did\b.*\bchange\b|updated?|revisions?|history|latest|recently|what(?: is|s|'s) new)\b/i.test(text);

        var variant=W.SpbCarKnowledge.variantReference&&W.SpbCarKnowledge.variantReference(car,text);
        if(variant&&variant.requested&&variant.layer_path_to_inspect){
            var variantFacts=facts.filter(function(f){return variant.source_fact_ids.indexOf(f.id)!==-1;});
            var variantPaths=variant.layer_paths_to_inspect||[variant.layer_path_to_inspect];
            var variantPacket=packet(a,'For '+car.name+', inspect “'+variantPaths.join('”; “')+'” in the actual template. '+variantFacts.map(function(f){return f.text;}).join(' ')+' '+variant.guidance);
            // Keep full evidence in the reference card; show the requested variant paths first.
            var variantBrief='For '+car.name+', inspect:\n'+variantPaths.map(function(p){return '• '+p;}).join('\n')+'\n\nNo layers changed. Match these labels to your actual template; labels alone do not verify pixels, decal restrictions or UV placement.';
            if(variantPaths.some(function(p){return p.indexOf('Turn Off Before Exporting TGA/')===0;}))variantBrief+='\nPaths under Turn Off Before Exporting TGA are reference guides; follow that group’s export instruction before exporting.';
            variantPacket.summary=variantBrief;variantPacket.chat_summary=variantBrief;
            return cited(variantPacket,a,variantFacts);
        }

        var restrictions=facts.filter(function(f){return f.topic==='custom-paint-restriction'||/locked paint|without sponsor|color selections|no custom/i.test(f.text);});

        // Dated non-actionable template history must not displace downloads or layer/export guidance.
        var restrictionQuestion=/\b(?:restrict(?:ion|ions|ed)?|lock(?:ed|s)?|forced|mandatory|manufacturer|allowed|permit(?:ted)?|can i(?: still)? paint)\b/i.test(text);
        var focusedLayerQuestion=W.SpbTemplateLayers&&car.template_metadata.some(function(m){return W.SpbTemplateLayers.focusedReferenceQuestion&&W.SpbTemplateLayers.focusedReferenceQuestion(text,m);});
        var relevantRestrictions=restrictions.filter(function(f){return f.actionable_paint_restriction!==false||restrictionQuestion&&!focusedLayerQuestion;});
        if(relevantRestrictions.length&&/template|custom|sponsor|number|paint|livery/i.test(text))return cited(packet(a,relevantRestrictions.map(function(f){return f.text;}).slice(0,3).join(' ')),a,relevantRestrictions.slice(0,3));

        var downloadRequest=/\b(?:template|psd|archive)\b/i.test(text)&&(/\b(?:download|where\b.{0,30}\b(?:get|find)|get\b.{0,20}\b(?:latest|newest|updated))\b/i.test(text)||/\b(?:latest|newest)\b.{0,25}\b(?:template|psd)\b/i.test(text))&&!/\b(?:repaint|recolour|recolor|apply|delete|replace|overwrite|export|transfer)\b/i.test(text);

        if(downloadRequest&&W.SpbCarKnowledge.templateDownloadGuide){

            var guide=W.SpbCarKnowledge.templateDownloadGuide(car),reply=packet(a,car.name+': '+(guide.available?'The official ZIP link is in Reference details and sources below'+(guide.checked_at?' (HTTP check '+guide.checked_at.slice(0,10)+')':'')+'. '+(guide.inspected_documents.length?'Inspected documents: '+guide.inspected_documents.map(function(m){return m.file+' ('+m.width+' × '+m.height+')';}).join('; ')+'. ':'')+guide.guidance:guide.guidance),'Get the exact template');

            reply.template_download=guide;
            if(guide.available){
                reply.sources=[{url:guide.url,label:car.name+' — official template ZIP'}];
                var documentStep=guide.inspected_documents.length===1?'open '+guide.inspected_documents[0].file+' in SPB':'choose the exact PSD for your car and variant, then open it in SPB';
                reply.chat_summary=car.name+': Open “Reference details and sources” below for the official template ZIP. Extract it, then '+documentStep+'. Save your current work first; older paint and masks may need checking against the new template.';
            }
            return cited(reply,a,car.template_metadata);

        }

        var datedArtworkQuestion=history&&/\b(?:body vinyl|artwork|vehicle art|paint patterns?|window banners?|contingency (?:decals?|logos?)|imsa decals?|paint\s*shop|preview|flicker(?:ing)?)\b/i.test(text);
        if(!datedArtworkQuestion&&W.SpbTemplateLayers&&(car.template_metadata.some(function(m){return W.SpbTemplateLayers.focusedReferenceQuestion&&W.SpbTemplateLayers.focusedReferenceQuestion(text,m);})||W.SpbTemplateLayers.materialQuestion(text)||/\b(?:layers?|groups?)\b/i.test(text)&&/\b(?:template|spec|metallic|roughness|clearcoat|alpha|export|wire|groups?)\b/i.test(text))&&car.template_metadata.length){

            if(car.template_metadata.length>1)return cited(packet(a,'The inspected reference contains several documents: '+car.template_metadata.map(function(m){return m.file;}).slice(0,5).join('; ')+'. Choose the exact document before applying its layer explanation. These references do not verify your loaded file.'),a,car.template_metadata);

            var referenceAnswer=W.SpbTemplateLayers.answerReference(text,car.template_metadata[0]);

            if(referenceAnswer)return cited(Object.assign({},referenceAnswer,{id:a.id,title:car.name+' — template layers',reference_car_id:car.id,document_stamp:W.SpbConversationScope&&W.SpbConversationScope.stamp?W.SpbConversationScope.stamp():null}),a,car.template_metadata);

        }

        var overview=!history&&W.SpbCarKnowledge.referenceIntent(text,namesCar(text)).overview;

        var previewHistory=/\b(?:paint\s*shop|preview|flicker(?:ing)?)\b/i.test(text);

        var artworkHistory=/\b(?:body vinyl|artwork|vehicle art|paint patterns?|window banners?|contingency (?:decals?|logos?)|imsa decals?)\b/i.test(text);

        var candidates=facts.filter(function(f){return !history||(f.topic==='paint-preview-history'?previewHistory:f.topic==='paint-artwork-history'?artworkHistory&&!previewHistory:['template-revision','template-compatibility','paint-pattern-revision','template_revision_or_variant'].indexOf(f.topic)>=0);});

        var historyFocus=W.SpbCarKnowledge.historyEvidence(car,text);
        if(history&&historyFocus.requested&&historyFocus.requested_features.length)candidates=candidates.filter(function(f){return historyFocus.matched_fact_ids.indexOf(f.id)>=0;});

        function dated(f){if(f.release)return f.release.year*100+f.release.season*10+(f.release.patch||0);var match=String((f.source_labels||[]).join(' ')).match(/(20\d\d)\s*(?:s|season\s*)([1-4])(?:\s*(?:p|patch\s*)(\d+))?/i);return match?Number(match[1])*100+Number(match[2])*10+Number(match[3]||0):0;}

        function score(f){var fw=new Set(words(f.text+' '+(f.helper_implication||'')));return query.reduce(function(n,t){return n+(fw.has(t)?1:0);},0);}

        var ranked=candidates.map(function(f){return {f:f,s:score(f)+(overview&&f.topic==='template-layer-structure'?2:0)};}).filter(function(x){return x.s>0||history||overview;}).sort(function(a,b){return (history?dated(b.f)-dated(a.f):0)||b.s-a.s;});

        var selected=[],size=0;

        ranked.slice(0,4).forEach(function(row){if(size+row.f.text.length>1600)return;selected.push(row.f);size+=row.f.text.length;});

        if(selected.length){

            var reply=selected.map(function(f){var labels=f.release?f.release.label:(f.source_labels||[]).join(', ').replace(/(20\d\d)s([1-4])(?:p(\d+))?/gi,function(_,y,s,p){return y+' Season '+s+(p?' Patch '+p:'');});return f.text+(history&&labels&&f.text.indexOf(labels)<0?' ('+labels+')':'')+(f.topic==='simulator-rendering-fix'?' This is a simulator rendering fix; it does not establish a PSD revision.':'');}).join(' ');

            if(selected.some(function(f){return f.evidence_level==='official-template-metadata';}))reply+=' These are observed template labels; they do not verify a panel location or that SPB can target it automatically.';

            var answerPacket=packet(a,reply,car.name+(selected.every(function(f){return f.topic==='paint-preview-history';})?' — Paint Shop history':selected.every(function(f){return f.topic==='paint-artwork-history';})?' — artwork history':' — template reference'));
            // Show an identical historical qualifier once; retain full evidence in the source card.
            if(history&&selected.length>1&&selected.every(function(f){return f.topic==='paint-artwork-history';})){
                var splitAt=selected.map(function(f){return f.text.indexOf(' This ');});
                if(splitAt.every(function(n){return n>0;})){
                    var qualifier=selected[0].text.slice(splitAt[0]);
                    if(selected.every(function(f,i){return f.text.slice(splitAt[i])===qualifier;})){
                        var brief=selected.map(function(f,i){var claim=f.text.slice(0,splitAt[i]),labels=f.release?f.release.label:(f.source_labels||[]).join(', ').replace(/(20\d\d)s([1-4])(?:p(\d+))?/gi,function(_,y,s,p){return y+' Season '+s+(p?' Patch '+p:'');});return claim+(labels&&f.text.indexOf(labels)<0?' ('+labels+')':'');}).join(' ')+ '\n\n'+qualifier.trim();
                        answerPacket.chat_summary=brief;answerPacket.summary=brief;
                    }
                }
            }
            return cited(answerPacket,a,selected);

        }

        if((overview||/\b(template|psd|file|download|dimensions|size)\b/i.test(text))&&car.template_metadata.length){

            return cited(packet(a,'The inspected official template contains '+car.template_metadata.slice(0,3).map(function(m){return m.file+' ('+m.width+' × '+m.height+')';}).join('; ')+'. '+(history?'No verified template revision history is recorded here yet. ':overview?'I do not have a verified unusual feature or template-specific exception recorded for this car yet. ':'')+'This file evidence does not verify UV panel positions on your open paint.'),a,car.template_metadata.slice(0,3));

        }

        if(car.availability&&car.availability.simulator_painting_available===false)return cited(packet(a,'I found the '+car.name+' historical reference, but I do not have a verified answer to that detail. This exact car is retired from painting in iRacing. Preserve the old file; independently confirm the supported car and its template for a current series. A replacement car does not establish matching paint files or UVs.','Retired car - historical reference'),a,facts.filter(function(f){return /retir/i.test(f.text);}).slice(0,2));

        return packet(a,'I found the '+car.name+' reference, but I do not have a verified answer to that particular detail yet. Check the labelled layers in its current official template and the live preview before changing that area.');

    }

    function contextQuestion(text){

        var explicitlyNamed=W.SpbCarKnowledge&&W.SpbCarKnowledge.select(DATA,{query:text});

        var inventory=W.SpbTemplateLayers&&W.SpbTemplateLayers.inventoryQuestion(text);

        var focused=W.SpbTemplateLayers&&W.SpbProCar&&W.SpbTemplateLayers.focusedQuestion(text,W.SpbProCar.roles());

        if(W.SpbTemplateLayers&&W.SpbProCar&&!namesCar(text)&&(inventory||focused||/\b(?:my|this|current|open|loaded)\b/i.test(text)&&explicitlyNamed)){var layerAnswer=W.SpbTemplateLayers.answer(text,W.SpbProCar.roles());if(layerAnswer)return {cls:'ANSWER',hits:[{id:layerAnswer.id,title:layerAnswer.title,score:0}],answer:layerAnswer};}

        // Only car-reference questions. General design/material questions stay in the existing helper.

        if(!W.SpbCarKnowledge||!W.SpbCarKnowledge.referenceIntent(text,namesCar(text)).current_context)return null;

        var chosen=pick(text),car=chosen.matches[0],a=car&&ARTICLES[car.id];

        if(chosen.template_match&&!chosen.template_match.matched&&/\b(?:which|what)\s+(?:car|vehicle|model)\b/i.test(text)){

            var unknownSource=packet({id:'cars.reading_sheet',title:'Original source is not in the car reference'},'The original source was verified during project Open, but its hash has no match in the inspected car-template reference. I cannot verify the exact car variant from that evidence. A suggested layout or destination is not proof. Confirm the car and version before using its reference; UV positions remain unverified.');

            return {cls:'ANSWER',hits:[{id:unknownSource.id,title:unknownSource.title,score:0}],answer:unknownSource};

        }

        if(!a)a={id:'cars.reading_sheet',title:'Identify the open template',car_reference:{}};

        var reply=answer(a,text),beforeScopeNote=reply&&reply.text;

        if(reply&&car&&chosen.definite&&chosen.matches.length===1&&!chosen.identity_conflict&&W.SpbConversationScope){reply.reference_car_id=car.id;reply.document_stamp=W.SpbConversationScope.stamp();}

        if(reply&&chosen.definite&&chosen.matches.length===1&&chosen.identity_evidence&&!chosen.identity_conflict){

            reply.text+=chosen.template_match&&chosen.template_match.matched&&chosen.template_match.exact_variant?' The original source file matches the inspected '+car.name+' template by SHA256. Saved artwork may differ; UV panel positions remain unverified.':' This reference follows the app’s current car context; the loaded file has not been verified against it.';

            if(chosen.template_match&&!chosen.template_match.matched)reply.text+=' The verified source snapshot has no match in the inspected template corpus.';

            reply.summary=reply.text;

        }

        else if(reply&&car&&!chosen.identity_conflict){

            reply.text+=' '+W.SpbCarKnowledge.identitySummary(chosen).text;

            reply.summary=reply.text;

        }

        // Concise chat and expanded cards must carry the same identity limits.

        if(reply&&reply.chat_summary&&reply.text!==beforeScopeNote)reply.chat_summary+=reply.text.slice(beforeScopeNote.length);

        return reply?{cls:'ANSWER',hits:[{id:reply.id,title:reply.title,score:0}],answer:reply}:null;

    }

    function isReferenceQuestion(text){

        if(!W.SpbCarKnowledge)return false;

        var intent=W.SpbCarKnowledge.referenceIntent(text,namesCar(text));

        if(intent.mixed_or_edit)return false;

        if(W.SpbTemplateLayers&&W.SpbTemplateLayers.inventoryQuestion(text))return true;

        if(!namesCar(text)&&W.SpbTemplateLayers&&W.SpbProCar&&W.SpbTemplateLayers.focusedQuestion(text,W.SpbProCar.roles()))return true;

        return intent.question;

    }

    function readOnlyQuestion(text){
        if(W.SpbCarKnowledge&&W.SpbCarKnowledge.referenceText)text=W.SpbCarKnowledge.referenceText(text);

        if(!isReferenceQuestion(text))return null;

        var live=contextQuestion(text);if(live)return live;

        var named=W.SpbCarKnowledge&&W.SpbCarKnowledge.select(DATA,{query:text}),car=named&&named.matches[0],a=car&&ARTICLES[car.id];

        if(!a&&named&&named.retired_matches)a={id:'cars.reading_sheet',title:'Retired model needs its own reference',car_reference:{}};

        if(!a)return null;

        var reply=answer(a,text);if(reply&&named.definite&&named.matches.length===1&&W.SpbConversationScope){reply.reference_car_id=car.id;reply.document_stamp=W.SpbConversationScope.stamp();}return reply&&(!reply.actions||!reply.actions.length)?{cls:'ANSWER',hits:[{id:reply.id,title:reply.title,score:0}],answer:reply}:null;

    }

    W.SpbCarReferenceAnswer={ready:function(){return DATA.cars.length > 0;},index:index,answer:answer,contextQuestion:contextQuestion,isReferenceQuestion:isReferenceQuestion,readOnlyQuestion:readOnlyQuestion,linksHtml:linksHtml,welcome:welcome,namesCar:namesCar,followup:followup,cardHtml:cardHtml};

})(window);

